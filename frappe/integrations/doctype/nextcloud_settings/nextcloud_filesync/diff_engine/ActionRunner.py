from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Set, Union

import frappe  # type: ignore
from frappe.model.rename_doc import rename_doc  # type: ignore
from frappe.core.doctype.file.file import File  # type: ignore

from .BaseActionRunner import _BaseActionRunner
from .Common import Common
from .Action import Action
from .Entry import EntryRemote
from .utils_normalize_paths import util_denormalize_to_local_path
from .utils import set_flag


# def path_to_owner_dir_name(path: str):
#     """
#     `path` should be relative to root files dir (`.../Frappe Files/$path`)
#     """
#     path = path.strip('/')
#     basename = os.path.basename(path)
#     splits = os.path.dirname(path).split('/', maxsplit=1)
#     owner, dir = (splits + ['', ''])[:2]

#     if owner and owner != 'Administrator':
#         dir = f'{owner}/{dir}'

#     return owner, dir.strip('/'), basename


# def get_local_parent_folder_and_file_name(path: str):
#     owner, dir, basename = path_to_owner_dir_name(path)
#     folder = os.path.join('Home', dir).rstrip('/')
#     file_name = basename
#     return folder, file_name


def descendants_of(folder: str):
	or_filters = [
		{'folder': folder},
		{'folder': ('like', f'{folder}/%')},
	]
	fields = ['name', 'folder', 'file_name',
			  'is_folder']
	return frappe.get_list('File', or_filters=or_filters, fields=fields)


def repath_descendants_of(old_path: str, new_path: str, ignore_list: set = set()):
	# print(f'mv {old_path}/** {new_path}/**')
	files = descendants_of(old_path)
	for file in files:
		# print(file)
		# try:
		#     while True:
		#         cmd = input("break> ")
		#         if not cmd:
		#             break
		#         print(eval(cmd))
		# except EOFError:
		#     raise SystemExit()

		if file.name in ignore_list:
			# print(f'skipping {file.name} (aka {file.folder}/{file.file_name})')
			continue

		folder: str = file.folder
		if folder == old_path:
			folder = new_path
		elif folder.startswith(old_path + '/'):
			folder = folder.replace(old_path, new_path, 1)
		else:
			print(f'{file.name} has unexpected folder {file.folder}')
			continue

		frappe.db.set_value('File', file.name, 'folder', folder)
		yield file


class ActionRunner_NexcloudFrappe(_BaseActionRunner):
	def __init__(
			self,
			common: Common,
			dry_run: bool = False,
	):
		super().__init__()
		self.common = common
		self.cloud_client = common.cloud_client
		self.cloud_settings = common.cloud_settings

		self._repathed_files: Set[str] = set()

		self.deferred_tasks: List[Callable] = []

	def get_remote_content(self, remote_real_path: str):
		try:
			data = self.cloud_client.get_file_contents(remote_real_path)
		except Exception as e:
			print('Exception trying to download', remote_real_path)
			raise e
		if data == False:
			frappe.throw(f'cannot download: {remote_real_path}')
		return data

	def run_actions(self, actions: Iterable[Action]):
		for action in actions:
			self._run_action(action)
		self._run_deferred_tasks()

	def _run_action(self, action: Action):
		if not self.is_action_valid(action):
			raise ValueError('invalid action')

		t = action.type
		# print(f'\x1b[1;34m·\x1b[0m', action)

		if t == 'local.create':
			self.action_local_create(action)
		elif t == 'local.file.moveRename':
			self.action_local_file_mv(action)
		elif t == 'local.dir.moveRenamePlusChildren':
			self.action_local_dir_mv(action)
		elif t == 'local.delete':
			self.action_local_delete(action)
		elif t == 'local.file.updateContent':
			self.action_local_file_update_content(action)
		elif t == 'meta.updateEtag':
			self.action_meta_update_etag(action)
		elif t == 'local.join':
			self.action_local_join(action)
		elif t == 'remote.createOrForceUpdate':
			self.action_remote_create_or_update(action)
		elif t == 'conflict.differentIds':
			self.resolve_conflict(action)
		else:
			self.common.logger(f'\x1b[2;33mskip\x1b[0m', action)
			# TODO: do not throw to avoid breaking the whole sync
			# but… how to recover and report the error?
			# frappe.throw('Unknown action type: {}'.format(t))
			return False
		return True

	def _run_deferred_tasks(self):
		for task in self.deferred_tasks:
			task()
		self.deferred_tasks = []

	def action_local_file_mv(self, action: Action):
		l, r = action.local, action.remote
		assert l is not None
		assert r is not None
		assert l._frappe_name

		folder, file_name = util_denormalize_to_local_path(r.path)
		frappe.db.set_value('File', l._frappe_name, {
			'file_name': file_name,
			'folder': folder,
			'modified': r.last_updated,
		}, update_modified=False)

		if r.is_dir():
			self.rename_folder_maybe_deferred(
				l._frappe_name, folder, file_name)

	def action_local_dir_mv(self, action: Action):
		l, r = action.local, action.remote
		assert l is not None
		assert r is not None
		assert l._frappe_name

		old_path = '/'.join(filter(None,
							util_denormalize_to_local_path(l.path)))
		new_path = '/'.join(filter(None,
							util_denormalize_to_local_path(r.path)))

		it = repath_descendants_of(
			old_path=old_path,
			new_path=new_path,
			ignore_list=self._repathed_files)

		repathed_files = set()
		for file in it:
			# print(f'{file.name} → {file.folder}/{file.file_name}')
			repathed_files.add(file.name)
			if int(file.is_folder):
				self.rename_folder_maybe_deferred(
					file.name, file.folder, file.file_name)

		self._repathed_files.update(repathed_files)

		self.action_local_file_mv(action)

	def action_local_delete(self, action: Action):
		assert action.local
		assert action.local._frappe_name
		frappe.delete_doc('File', action.local._frappe_name)

	def action_local_file_update_content(self, action: Action):
		l, r = action.local, action.remote
		assert l is not None
		assert r is not None
		assert l.path != '/'
		assert l._frappe_name

		docname = l._frappe_name
		d = self._remote_to_data(r, fetch_content=True)
		file_doc = frappe.get_doc('File', docname)
		d.apply_to_existing_document(file_doc)

	def action_meta_update_etag(self, action: Action):
		assert action.local is not None
		assert action.remote is not None
		assert action.local._frappe_name is not None

		docname = action.local._frappe_name
		frappe.db.set_value('File', docname, {
			'modified': action.remote.last_updated,
			'content_hash': action.remote.etag,
		})

	def action_remote_create_or_update(self, action: Action):
		raise NotImplementedError()

	def action_local_create(self, action: Action):
		assert not action.local
		assert action.remote

		d = self._remote_to_data(action.remote, fetch_content=True)

		existing_docname = frappe.db.exists(
			'File', {'file_name': d.file_name, 'folder': d.folder})

		if existing_docname:
			# if the File already exists, we just update it
			# and don't create a new one
			file_doc = frappe.get_doc('File', existing_docname)
			d.apply_to_existing_document(file_doc)
		else:
			file_doc = d.create_document()

	def action_local_join(self, action: Action):
		# attach by path if exist with same path but no id
		# action.local is the potential local file

		assert action.local is not None
		assert action.remote is not None
		assert action.local._frappe_name is not None

		existing_docname = action.local._frappe_name
		if existing_docname:
			d = self._remote_to_data(action.remote, fetch_content=True)
			file_doc = frappe.get_doc('File', existing_docname)
			d.apply_to_existing_document(file_doc)
		else:
			self.common.logger('! unexpected: join by creating')
			return self.action_local_create(action)

	def action_remote_mv(self, action: Action):
		assert action.local
		assert action.remote
		a = self.common.denormalize_remote(action.remote.path)
		b = self.common.denormalize_remote(action.local.path)
		res = self.common.cloud_client.move(a, b)
		if not res:
			raise Exception('Failed to move {} to {}'.format(a, b))

	def resolve_conflict(self, action: Action):
		if action.type == 'conflict.differentIds':
			self.common.logger('Different IDs')
		else:
			self.common.logger('CONFLICT ------------------------')
			raise NotImplementedError()

	def _remote_to_data(self, remote: EntryRemote, fetch_content=True):
		is_dir = remote.is_dir()
		folder, file_name = util_denormalize_to_local_path(remote.path)

		content = None
		if fetch_content and not is_dir:
			remote_path = self.common.denormalize_remote(remote.path)
			content = self.get_remote_content(remote_path)
			# if content == b'' or content == '':
			#     # Cannot have empty files
			#     content = b'\x00'

		data = {
			# frappe metadata
			# "modified": last_updated,
			"owner": "Administrator",
			"is_private": False,
			# attached_to_doctype = TODO
			# attached_to_name = TODO
			# file identification
			"file_name": file_name,
			"folder": folder,
			# data
			# "content": content,
			"is_folder": is_dir,
			"content_hash": remote.etag,
			# nextcloud
			"nextcloud_id": remote.nextcloud_id,
		}
		if remote.parent_id:
			data["nextcloud_parent_id"] = remote.parent_id

		post_insert_data = {
			# force "file name" because it is changed by frappe
			"file_name": file_name,
			"modified": remote.last_updated,
			"content_hash": remote.etag,
		}

		return TheData(folder, file_name, content, data, post_insert_data)

	def rename_folder_maybe_deferred(self, cur_docname: str, folder: str, file_name: str):
		new_docname = (folder + '/' + file_name).strip('/')
		exists = frappe.db.exists('File', new_docname)
		if not exists:
			# safe to rename now
			rename_folder(cur_docname, new_docname)
		else:
			# defer the rename until all actions are done

			# NOTE: why are we doing this?
			# When we change the folder/file_name of a folder, we also have
			# to change it's frappe name, but it might not be possible if a
			# folder of the same name already exists in the database.
			# How can a folder of the same name exist in the database in
			# the first place? Well, it can happen in the case of a
			# cross-rename, i.e. "simultaneous" renames a -> b / b -> a
			# (because of the way we fetch changes from the cloud, we have
			# no way to know what were the intermediate renames).
			# We have to translate this cross-rename to a valid sequence of
			# operations: a -> tmp, b -> a, tmp -> b
			# For this deferred rename to work, we have to hope that both
			# renames of the cross rename (a -> b, b -> a) appear in the
			# list of actions we run.

			tmp_docname = 'tmp_' + frappe.utils.random_string(12)
			rename_folder(cur_docname, tmp_docname)
			self.deferred_tasks.append(
				lambda: rename_folder(tmp_docname, new_docname))


@dataclass
class TheData:
	folder: Optional[str]
	file_name: str

	content: Union[str, bytes, None]

	data: dict
	post_insert_data: dict

	def create_document(self):
		file_doc = frappe.get_doc({'doctype': 'File'})
		self.apply_to_existing_document(file_doc, force_full_update=True)
		return file_doc

	def apply_to_existing_document(self, file_doc: 'File', force_full_update=False):
		# Document should already exist in the database
		if (self.content is not None) or force_full_update:
			set_flag(file_doc)
			file_doc.update(self.data)
			file_doc.content = self.content
			file_doc.save()
			file_doc.db_set(self.post_insert_data, update_modified=False)
		else:
			set_flag(file_doc)
			# should update variable, not only the database
			file_doc.update(self.data)
			file_doc.update(self.post_insert_data)
			file_doc.db_set(
				{** self.data, **self.post_insert_data}, update_modified=False)

		# if file_doc.is_folder:
		# 	auto_rename_folder(file_doc)


def rename_folder(old_name: str, new_name: str):
	# print('FOLDER', old_name)
	# print('    ->', new_name)
	rename_doc('File', old_name, new_name, ignore_permissions=True)


def auto_rename_folder(file_doc: 'File'):
	rename_folder(file_doc.name, file_doc.get_name_based_on_parent_folder())
