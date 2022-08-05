from .BaseDiffEngine import BaseDiffEngineNC
from .Common import Common
from .Entry import EntryLocal, EntryRemote


class DiffEngine(BaseDiffEngineNC):
	def __init__(self, common: Common, **kwargs):
		super().__init__(logger=common.logger, **kwargs)
		self.common = common

	def get_local_entry_by_id(self, id: int) -> EntryLocal | None:
		return self.common.get_local_entry_by_id(id)

	def get_local_entry_by_path(self, path: str) -> EntryLocal | None:
		return self.common.get_local_entry_by_path(path)

	def get_remote_entry_by_id(self, id: int) -> EntryRemote | None:
		return self.common.get_remote_entry_by_id(id)

	def get_remote_entry_by_path(self, path: str) -> EntryRemote | None:
		return self.common.get_remote_entry_by_path(path)

	def get_local_children_ids(self, of_dir: EntryLocal) -> set[int]:
		return self.common.get_local_children_ids(of_dir)

	def get_remote_children_entries(self, of_dir: EntryRemote) -> dict[int, EntryRemote]:
		return self.common.get_remote_children_entries(of_dir)
