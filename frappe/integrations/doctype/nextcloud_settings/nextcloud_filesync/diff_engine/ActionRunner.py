import os
from dataclasses import dataclass
from typing import Iterable, Optional, Set, Union

import frappe  # type: ignore
from frappe.model.rename_doc import rename_doc  # type: ignore
from frappe.core.doctype.file.file import File
from frappe.utils.data import cint, cstr  # type: ignore

from .Action import Action
from .BaseActionRunner import _BaseActionRunner
from .Common import Common
from .DeferredTasks import DeferredTasks
from .Entry import EntryRemote, EntryLocal
from .utils import FLAG_NEXTCLOUD_IGNORE, set_flag
from .utils_normalize_paths import util_denormalize_to_local_path

def is_iterable(obj):
	try:
		iter(obj)
		return True
	except TypeError:
		return False


def make_folder_docname(parent_folder: str, file_name: str):
	if parent_folder:
		return parent_folder + '/' + file_name
	return file_name


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

		self.deferred_tasks = DeferredTasks()
		# self.folder_renamer = FolderRenamer()

		# self._all_runned_actions: List[Action] = []
		# self._add_rollback_observer()

	def log(self, *args, **kwargs):
		self.common.log(*args, **kwargs)

	def get_remote_content(self, remote_real_path: str):
		try:
			data = self.cloud_client.get_file_contents(remote_real_path)
		except Exception as e:
			self.log('Exception trying to download', remote_real_path)
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
		# _profile_dt_start = frappe.utils.now_datetime()

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
			# self.common.logger(
			# 	'skipping action:', action.type,
			# 	'local:', action.local.toJSON() if action.local else None,
			# 	'remote:', action.remote.toJSON() if action.remote else None,
			# )
			# TODO: do not throw to avoid breaking the whole sync
			# but… how to recover and report the error?
			# frappe.throw('Unknown action type: {}'.format(t))
			return False

		# self._all_runned_actions.append(action)

		# self.common.logger(
		# 	'ran action:', action.type,
		# 	'local:', action.local.toJSON() if action.local else None,
		# 	'remote:', action.remote.toJSON() if action.remote else None,
		# 	'in duration:', (frappe.utils.now_datetime() - _profile_dt_start).total_seconds(), 'seconds',
		# )
		return True

	def _run_deferred_tasks(self):
		# print('\x1b[7mStarting to run deferred tasks…\x1b[0m')
		for actions in self.deferred_tasks:
			if actions and is_iterable(actions):
				for action in actions:
					self._run_action(action)
		# print('\x1b[7mFinished running deferred tasks…\x1b[0m')


	def _get_frappe_name_by_id(self, nextcloud_id: int) -> Optional[str]:
		return frappe.db.exists('File', {'nextcloud_id': nextcloud_id})

	def _get_frappe_name(self, local: EntryLocal) -> Optional[str]:
		# if local._frappe_name and ('/' not in local._frappe_name):
		# 	#return self.folder_renamer.get(local._frappe_name) or local._frappe_name
		# 	return local._frappe_name

		if local.nextcloud_id is not None:
			return self._get_frappe_name_by_id(local.nextcloud_id) or local._frappe_name
		elif local._frappe_name:
			# no .nextcloud_id, but ._frappe_name
			return local._frappe_name

		# TODO: else, find by path?
		return None

	def action_local_file_mv(self, action: Action):
		l, r = action.local, action.remote
		assert l is not None
		assert r is not None
		frappe_name = self._get_frappe_name(l)
		assert frappe_name

		folder, file_name = util_denormalize_to_local_path(r.path)

		# next line is indeed needed:
		#   folder is not expected to be* correct
		#   *(will become correct once all deferred renames
		#   are settled) in the case of a cross-rename
		# folder = self.folder_renamer.get(folder) or folder

		if r.parent_id is not None:
			folder = self._get_frappe_name_by_id(r.parent_id)

		# print('\x1b[34m★', l.parent_id, action.local.path, '->', r.parent_id, action.remote.path, folder, '\x1b[m')

		frappe.db.set_value('File', frappe_name, {
			'file_name': file_name,
			'folder': folder,
			'nextcloud_parent_id': r.parent_id,
			# NOTE: do not forget to update
			# the nextcloud_parent_id field
			# when programmatically moving files.
			'modified': r.last_updated,
		}, update_modified=False)

		assert frappe.db.get_value('File', frappe_name, ['folder', 'file_name', 'modified']) == (folder, file_name, r.last_updated)

		if r.is_dir():
			if frappe_name != make_folder_docname(folder, file_name):
				# print('\x1b[34m★', l.parent_id, action.local.path, '->', r.parent_id, action.remote.path, folder, '\x1b[m')
				self.rename_folder_maybe_deferred(
					frappe_name, folder, file_name)

	def action_local_dir_mv(self, action: Action):
		l, r = action.local, action.remote
		assert l is not None
		assert r is not None
		# frappe_name = self._get_frappe_name(l)
		# assert frappe_name
		self.action_local_file_mv(action)

	def action_local_delete(self, action: Action):
		assert action.local
		frappe_name = self._get_frappe_name(action.local)
		assert frappe_name

		if not frappe.db.exists('File', frappe_name):
			return  # skip, deletion should be idempotent

		delete_filedoc_and_children_by_name(frappe_name)

	def action_local_file_update_content(self, action: Action):
		l, r = action.local, action.remote
		assert l is not None
		assert r is not None
		assert l.path != '/'
		frappe_name = self._get_frappe_name(action.local)
		assert frappe_name

		d = self._remote_to_data(r, fetch_content=True)
		file_doc = frappe.get_doc('File', frappe_name)
		d.apply_to_existing_document(file_doc)

	def action_meta_update_etag(self, action: Action):
		assert action.local is not None
		assert action.remote is not None
		frappe_name = self._get_frappe_name(action.local)
		assert frappe_name

		frappe.db.set_value('File', frappe_name, {
			'modified': action.remote.last_updated,
			'content_hash': action.remote.etag,
		})

	def action_remote_create_or_update(self, action: Action):
		frappe_name = self._get_frappe_name(action.local)
		assert frappe_name

		new_remote_path = self.common.denormalize_remote(action.local.path)
		is_folder = action.local.is_dir()
		doc: File = frappe.get_doc('File', frappe_name)

		data_path: str = None
		if not is_folder:  # find file path for upload
			data_path = os.path.abspath(doc.get_full_path())
			if not os.path.exists(data_path):
				self.log('Missing data file')
				raise Exception('Missing data file')

		if action.remote:  # just update the remote file/dir
			old_remote_path = self.common.denormalize_remote(action.remote.path)
			if old_remote_path != new_remote_path:
				self.log(f'C.move({old_remote_path}, {new_remote_path})')
				self.cloud_client.move(old_remote_path, new_remote_path)

			if not is_folder:
				self.log(f'C.put_file({new_remote_path}, {data_path})')
				self.cloud_client.put_file(new_remote_path, data_path)
		else:  # create the remote file/dir
			if is_folder:
				self.log(f'C.mkdir({new_remote_path})')
				self.cloud_client.mkdir(new_remote_path)
			else:
				self.log(f'C.put_file({new_remote_path}, {data_path})')
				self.cloud_client.put_file(new_remote_path, data_path)

		new_remote = self.common.get_remote_entry_by_real_path(new_remote_path)
		if new_remote is None:
			self.log('Failed to create file/dir')
			raise Exception('Failed to create file/dir')

		parent_id = new_remote.parent_id
		if parent_id is None and new_remote.path != '/':
			parent_id = self._fetch_parent_id(new_remote_path)

		doc.db_set({
			'nextcloud_id': new_remote.nextcloud_id,
			'nextcloud_parent_id': parent_id,
			'content_hash': new_remote.etag,
			'modified': new_remote.last_updated,
		})

		nextcloud_id = new_remote.nextcloud_id

		if is_folder or (action.remote is None):
			def f():
				new_remote2 = self.common.get_remote_entry_by_id(nextcloud_id)
				if new_remote2 is None:
					raise Exception('Failed to fetch file/dir')

				parent_id2 = new_remote2.parent_id
				if parent_id2 is None and new_remote2.path != '/':
					parent_id2 = self._fetch_parent_id(new_remote_path)

				if new_remote.nextcloud_id != new_remote2.nextcloud_id:
					self.log('NCID:', new_remote, new_remote2)
					doc.db_set('nextcloud_id', new_remote2.nextcloud_id, update_modified=False)
				if parent_id != parent_id2:
					self.log('P_ID:', new_remote, new_remote2)
					doc.db_set('nextcloud_parent_id', parent_id2, update_modified=False)
				if new_remote.etag != new_remote2.etag:
					self.log('ETAG:', new_remote, new_remote2)
					doc.db_set('content_hash', new_remote2.etag, update_modified=False)
				if new_remote.last_updated != new_remote2.last_updated:
					self.log('UPDT:', new_remote, new_remote2)
					doc.db_set('modified', new_remote2.last_updated, update_modified=False)

			self.deferred_tasks.push(f)

		self.log()


	def action_local_create(self, action: Action):
		assert not action.local
		assert action.remote

		d = self._remote_to_data(action.remote, fetch_content=True)

		# TODO: might be a mistake
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
		frappe_name = self._get_frappe_name(action.local)
		assert frappe_name

		existing_docname = frappe_name
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
			self.common.logger('conflict')
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
		# TODO: what if we move the remote home
		# inside of a new handmade home with the same path?
		if remote.parent_id is not None:
			data["nextcloud_parent_id"] = remote.parent_id

		post_insert_data = {
			# force "file name" because it is changed by frappe
			"file_name": file_name,
			"modified": remote.last_updated,
			"content_hash": remote.etag,
		}

		return TheData(folder, file_name, content, data, post_insert_data)

	def rename_folder_maybe_deferred(self, cur_docname: str, folder: str, file_name: str):
		# assume that the parent folder has already been renamed
		# if '/' in cur_docname:
		# 	cur_docname = self.folder_renamer.get(cur_docname)

		new_docname = make_folder_docname(folder, file_name)
		if cur_docname == new_docname:
			print('skipping rename: docname did not change', cur_docname)
			return

		exists = frappe.db.exists('File', new_docname)
		if not exists:
			# safe to rename now
			self.rename_folder(cur_docname, new_docname)
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

			tmp_folder = folder
			if '/' in cur_docname:
				i = cur_docname.rfind('/')
				tmp_folder = cur_docname[:i]
				# tmp_folder = self.folder_renamer.get(tmp_folder)

			tmp_docname = 'tmp_' + frappe.utils.random_string(12)
			tmp_docname = (tmp_folder + '/' + tmp_docname).strip('/')

			# print("\x1b[31;1m" + f'cross-rename detected: {new_docname} already exists' + "\x1b[m")
			# print("\x1b[31;1m" + f'doing: {cur_docname} -> {tmp_docname} -> {new_docname}' + "\x1b[m")

			idx = self.rename_folder(cur_docname, tmp_docname)
			self.deferred_tasks.push(self.rename_folder, tmp_docname, new_docname, idx)

	def rename_folder(self, cur_docname: str, new_docname: str, idx: int = None):
		# if idx is not None:
		# 	cur_docname = self.folder_renamer.get(cur_docname, -idx)  # apply posterior renames

		if not frappe.flags.nextcloud_in_rename:
			frappe.flags.nextcloud_in_rename = 0

		frappe.flags.nextcloud_in_rename += 1
		frappe_rename_folder(cur_docname, new_docname)
		frappe.flags.nextcloud_in_rename -= 1
		# return self.folder_renamer.register_folder_move(cur_docname, new_docname)

	def _fetch_parent_id(self, real_path: str):
		parent_path = real_path.rstrip('/').rsplit('/', 1)[0]
		remote_parent = self.common.get_remote_entry_by_real_path(parent_path)
		return remote_parent.nextcloud_id

	# def _add_rollback_observer(self):
	# 	frappe.local.rollback_observers.append(self)

	# def on_rollback(self):
	# 	for action in self._all_runned_actions:
	# 		rollback_action = action
	# 	self.run_actions

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
			if file_doc.get("__islocal") or not file_doc.get("name"):
				file_doc.insert(ignore_links=True)
			else:
				file_doc.save()
			file_doc.db_set(self.post_insert_data, update_modified=False)
		else:
			set_flag(file_doc)
			# should update variable, not only the database
			file_doc.update(self.data)
			file_doc.update(self.post_insert_data)
			file_doc.db_set({**self.data, **self.post_insert_data}, update_modified=False)

		# if file_doc.is_folder:
		# 	old_name = file_doc.name
		# 	file_doc.autoname()
		# 	new_name = file_doc.name
		# 	if old_name != new_name:
		# 		frappe_rename_folder()


def frappe_rename_folder(old_name: str, new_name: str):
	rename_doc('File', old_name, new_name, ignore_permissions=True)

def delete_filedoc_and_children_by_name(frappe_name: str):
	doc: File = frappe.get_doc('File', frappe_name)
	set_flag(doc)
	is_folder = doc.is_folder
	if is_folder:
		doc.folder_delete_children(flags={FLAG_NEXTCLOUD_IGNORE: True})
	doc.delete()
