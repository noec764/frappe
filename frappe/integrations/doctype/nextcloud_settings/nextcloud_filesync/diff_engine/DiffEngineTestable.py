from typing import Dict, Optional, Set, List
import unicodedata

from .Entry import Entry, EntryLocal, EntryRemote
from .BaseDiffEngine import BaseDiffEngineNC


def unicode_str_equals(a: str, b: str):
	if a == b:
		return True
	return unicodedata.normalize('NFC', a) == unicodedata.normalize('NFC', b)


class DiffEngineTest(BaseDiffEngineNC):
	"""
	The diffing engine for testing.
	"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def _test_init(self, L: List[EntryLocal], R: List[EntryRemote]):
		self._test_FRAPPE_local_entries = L
		self._test_UNKNOWN_all_remote_entries = R

	def get_local_entry_by_id(self, id: int) -> Optional[EntryLocal]:
		if id is None:
			return None
		for local in self._test_FRAPPE_local_entries:
			if local.nextcloud_id is not None and local.nextcloud_id == id:
				return local
		return None

	def get_local_entry_by_path(self, path: str) -> Optional[EntryLocal]:
		for local in self._test_FRAPPE_local_entries:
			if unicode_str_equals(local.path, path):
				return local
		return None

	def get_remote_entry_by_id(self, id: int) -> Optional[EntryRemote]:
		if id is None:
			return None
		for remote in self._test_UNKNOWN_all_remote_entries:
			if remote.nextcloud_id == id:
				return remote
		return None

	def get_remote_entry_by_path(self, path: str) -> Optional[EntryRemote]:
		for remote in self._test_UNKNOWN_all_remote_entries:
			if unicode_str_equals(remote.path, path):
				return remote
		return None

	def get_local_children_ids(self, of_dir: Entry) -> Set[int]:
		old_children_ids: Set[int] = set(
			map(lambda f: f.nextcloud_id or 0,
				filter(lambda f: (f.nextcloud_id is not None) and (f.parent_id == of_dir.nextcloud_id),
					   self._test_FRAPPE_local_entries))
		)
		return old_children_ids

	def get_remote_children_entries(self, of_dir: EntryRemote) -> Dict[int, EntryRemote]:
		cur_list = [
			entry for entry in self._test_UNKNOWN_all_remote_entries if entry.parent_id == of_dir.nextcloud_id
		]
		# cur_list.sort(key=lambda f: f.path)

		new_children = {
			# key: value
			int(e.nextcloud_id): e for e in cur_list
			# int(file.attributes[self._FILE_ID]): file for file in cur_list
		}

		return new_children
