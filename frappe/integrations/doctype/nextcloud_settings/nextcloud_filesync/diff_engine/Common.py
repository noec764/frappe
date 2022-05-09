import os
from typing import Callable, Dict, List, Optional, Set, TypeVar

import frappe  # type: ignore
from owncloud import HTTPResponseError, FileInfo

from frappe.core.doctype.file.file import File
from frappe.integrations.doctype.nextcloud_settings import NextcloudSettings
from frappe.integrations.doctype.nextcloud_settings.client import NextcloudIntegrationClient

from .Entry import Entry, EntryLocal, EntryRemote
from .utils_time import convert_utc_to_local_time, strip_datetime_milliseconds, set_timezone_to_local
from .utils_normalize_paths import util_denormalize_to_local_path, util_denormalize_to_remote_path, util_normalize_local_path, util_normalize_remote_path
from .utils import maybe_int


Pathable = TypeVar('Pathable', Entry, FileInfo)


class Common:
	@staticmethod
	def Default():
		from frappe.integrations.doctype.nextcloud_settings import get_nextcloud_settings_and_client  # type: ignore

		client, settings = get_nextcloud_settings_and_client()

		def logger(*args, **kwargs):
			print('\x1b[35;2mlog\x1b[m', *args, **kwargs)

		return Common(client, settings, logger)

	@staticmethod
	def Test(logger: Callable = None, test_root_dir_name='@test'):
		from frappe.integrations.doctype.nextcloud_settings import get_nextcloud_settings_and_client  # type: ignore

		client, settings = get_nextcloud_settings_and_client(debug=False)
		settings.get_path_to_files_folder = lambda: test_root_dir_name

		if not logger:
			def logger(*args, **kwargs):
				print('\x1b[35;2mtest\x1b[m\x1b[2m', *args, '\x1b[m', **kwargs)

		return Common(client=client, settings=settings, logger=logger)

	@staticmethod
	def sort_key(entry: Entry):
		return entry.path

	def __init__(
		self,
		client: NextcloudIntegrationClient,
		settings: NextcloudSettings,  # type: ignore
		logger: Callable,
	):
		self.cloud_client = client
		self.cloud_settings = settings
		self.logger = logger

		p = self.cloud_settings.get_path_to_files_folder()
		self.root = ('/' + p.strip('/')).rstrip('/') + '/'
		self.remote_prefix_to_remove: str = '/' + self.root.strip('/')

		self._FILE_ID = '{http://owncloud.org/ns}fileid'
		self._QUERY_PROPS = [
			self._FILE_ID,  # nextcloud_id
			'{DAV:}getetag',  # etag
			# '{DAV:}getcontentlength',
			# '{DAV:}getcontenttype',
			'{DAV:}getlastmodified',
		]
		# self._QUERY_PROPS = self.cloud_client._QUERY_PROPS

		self._map_remote_path_to_id: Dict[str, int] = {}

	def log(self, *args, **kwargs):
		self.logger(*args, **kwargs)

	def _normalize_remote_path(self, path: str, is_dir: bool) -> str:
		return util_normalize_remote_path(path, is_dir, self.remote_prefix_to_remove)

	def denormalize_remote(self, path: str) -> str:
		return util_denormalize_to_remote_path(path, self.remote_prefix_to_remove)

	def convert_remote_file_to_entry(self, file: FileInfo) -> EntryRemote:
		path = self._normalize_remote_path(file.path, file.is_dir())

		nextcloud_id = int(file.attributes[self._FILE_ID])

		self._map_remote_path_to_id['/' + path.strip('/')] = nextcloud_id

		etag = file.get_etag()

		parent_path = '/' + os.path.dirname(path.strip('/'))
		parent_id = None
		# if path != parent_path:
		if path != '/':
			parent_id = self._map_remote_path_to_id.get(parent_path, None)

		# assumed timezone is UTC -> convert to local time
		last_updated = file.get_last_modified()
		last_updated = convert_utc_to_local_time(last_updated)
		last_updated = strip_datetime_milliseconds(last_updated)

		return EntryRemote(
			path=path,
			etag=etag,
			nextcloud_id=nextcloud_id,
			parent_id=parent_id,
			_file_info=file,
			last_updated=last_updated,
			# extra=dict(file=file)
		)

	def convert_local_doc_to_entry(self, doc: File) -> EntryLocal:
		assert isinstance(doc, File)
		path = util_normalize_local_path(doc.folder, doc.file_name, doc.is_folder)

		last_updated = frappe.utils.get_datetime(doc.modified)
		last_updated = strip_datetime_milliseconds(last_updated)

		return EntryLocal(
			path=path,
			etag=doc.nextcloud_etag or '?',
			nextcloud_id=doc.nextcloud_id or None,
			parent_id=doc.nextcloud_parent_id or None,
			last_updated=last_updated,
			_frappe_name=doc.name,
		)

	def _get_remote_entry_by_norm_path(self, path: str):
		p = '/' + self.root.strip('/') + '/' + path.strip('/')
		f = self.cloud_client.file_info(p, self._QUERY_PROPS)
		return self.convert_remote_file_to_entry(f)

	def _get_local_entry_from_frappe_db(self, filters, **kwargs):
		fields = [
			'name',  # frappe unique id
			'folder',  # parent dir
			'file_name',  # name of the file
			'is_folder',  # is dir
			'nextcloud_etag',  # etag
			'nextcloud_id',  # nextcloud id
			'nextcloud_parent_id',  # parent id
			'modified',  # last modified
		]
		try:
			values = frappe.db.get_value('File', filters, fields, **kwargs)
			if values is None:
				raise frappe.DoesNotExistError

			frappe_name, dir, file_name, is_dir, etag, nextcloud_id, nextcloud_parent_id, modified = values
			path = util_normalize_local_path(dir, file_name, bool(is_dir))
			nextcloud_id = maybe_int(nextcloud_id)
			parent_id = maybe_int(nextcloud_parent_id)

			# assumed local timezone
			last_updated = modified  # local time
			last_updated = set_timezone_to_local(modified)
			last_updated = strip_datetime_milliseconds(last_updated)

			return EntryLocal(
				path=path,
				etag=etag,
				nextcloud_id=nextcloud_id,
				parent_id=parent_id,
				last_updated=last_updated,
				_frappe_name=frappe_name,
				# extra=dict(frappe_name=frappe_name)
			)
		except frappe.DoesNotExistError:
			frappe.clear_last_message()
			return None
		except Exception as e:
			frappe.clear_last_message()
			self.log(e)
			raise

	def get_local_entry_by_id(self, id: int) -> Optional[EntryLocal]:
		return self._get_local_entry_from_frappe_db({'nextcloud_id': id})

	def get_local_entry_by_path(self, path: str) -> Optional[EntryLocal]:
		"""
		:param path: normalized path
		:return: EntryLocal if found
		"""
		folder, file_name = util_denormalize_to_local_path(path)

		filters = {'file_name': file_name}
		if folder:
			filters['folder'] = folder

		if self.cloud_settings.filesync_exclude_private:
			filters['is_private'] = 0

		# self.log(f"get_local_entry_by_path: {path} -> {folder}:{file_name}", filters)
		return self._get_local_entry_from_frappe_db(filters)

	def get_remote_entry_by_id(self, id: int) -> Optional[EntryRemote]:
		props = self._QUERY_PROPS
		file = self.cloud_client.file_info_by_fileid(id, props)
		if file is not None:
			return self.convert_remote_file_to_entry(file)
		return None

	def get_remote_entry_by_path(self, path: str) -> Optional[EntryRemote]:
		"""
		:param path: normalized path
		:return: EntryRemote if found
		"""
		remote_path = self.denormalize_remote(path)
		return self.get_remote_entry_by_real_path(remote_path)

	def get_remote_entry_by_real_path(self, remote_path: str) -> Optional[EntryRemote]:
		"""
		:param path: denormalized path
		:return: EntryRemote if found
		"""
		try:
			file = self.cloud_client.file_info(remote_path, self._QUERY_PROPS)
			return self.convert_remote_file_to_entry(file)
		except HTTPResponseError:
			return None
		return None

	def get_local_children_ids(self, local_dir: EntryLocal) -> Set[int]:
		filters = {}
		filters['nextcloud_id'] = ('!=', '')

		# dir_name = '/'.join(util_denormalize_to_local_path(local_dir.path))
		dir_name = local_dir._frappe_name  # NOTE: optimization
		# dir_name = frappe.db.exists('File', {'nextcloud_id': local_dir.nextcloud_id})
		if dir_name:
			filters['folder'] = dir_name
		else:
			filters['nextcloud_parent_id'] = local_dir.nextcloud_id

		if self.cloud_settings.filesync_exclude_private:
			filters['is_private'] = '0'

		# get all children
		old_children_ids = frappe.db.get_values(
			'File', filters=filters, fieldname='nextcloud_id')
		# keep only their nextcloud ids
		old_children_ids = set(map(lambda x: int(x[0]), old_children_ids))
		return old_children_ids

	def get_remote_children_entries(self, of_dir: EntryRemote) -> Dict[int, EntryRemote]:
		# if self.mode == 'full':
		#     # All the remote entries are available.
		#     # Skip network requests to directly find children
		#     # in the self.pairs_queue.
		#     ...

		if of_dir._file_info is None:
			raise Exception('of_dir._file_info is None')

		cur_list = self.cloud_client.list(
			of_dir._file_info.path,
			depth=1,
			properties=self._QUERY_PROPS)
		cur_list = self._filter(cur_list)
		cur_list.sort(key=self.sort_key)

		children_ids = {}
		for file in cur_list:
			entry = self.convert_remote_file_to_entry(file)
			children_ids[entry.nextcloud_id] = entry

		return children_ids

	def _filter(self, files: List[Pathable]) -> List[Pathable]:
		def f(file: Pathable) -> bool:
			path = file.path
			return all((
				path.startswith(self.root),
				'/.' not in path[len(self.root)-1:],
			))
		return list(filter(f, files))
