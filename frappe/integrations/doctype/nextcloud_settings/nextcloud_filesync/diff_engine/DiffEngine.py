from typing import Dict, Optional, Set

from .BaseDiffEngine import BaseDiffEngineNC
from .Entry import Entry, EntryLocal, EntryRemote
from .Common import Common


class DiffEngine(BaseDiffEngineNC):
	def __init__(self, common: Common):
		super().__init__(logger=common.logger)
		self.common = common

	def get_local_entry_by_id(self, id: int) -> Optional[EntryLocal]:
		return self.common.get_local_entry_by_id(id)

	def get_local_entry_by_path(self, path: str) -> Optional[EntryLocal]:
		return self.common.get_local_entry_by_path(path)

	def get_remote_entry_by_id(self, id: int) -> Optional[EntryRemote]:
		return self.common.get_remote_entry_by_id(id)

	def get_remote_entry_by_path(self, path: str) -> Optional[EntryRemote]:
		return self.common.get_remote_entry_by_path(path)

	def get_local_children_ids(self, of_dir: Entry) -> Set[int]:
		return self.common.get_local_children_ids(of_dir)

	def get_remote_children_entries(self, of_dir: EntryRemote) -> Dict[int, EntryRemote]:
		return self.common.get_remote_children_entries(of_dir)
