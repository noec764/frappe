from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple, Union
from typing_extensions import Literal

# from frappe.core.doctype.file.file import File
from owncloud import FileInfo  # type: ignore


@dataclass
class Entry():
	path: str  # normalized path
	etag: str  # hash of content
	nextcloud_id: Optional[int]  # id of file in the remote nextcloud
	parent_id: Optional[int]
	last_updated: Optional[datetime] = None

	_type: Literal['local', 'remote', None] = None

	# _hint_deletion: Optional[
	#     Literal['deletedFromLocal', 'deletedFromRemote']] = None

	def is_dir(self) -> bool:
		return self.path.endswith('/')

	def __hash__(self) -> int:
		return hash(self._type) + hash(self.path) + hash(self.etag) + hash(self.nextcloud_id) + hash(self.parent_id)

	def __eq__(self, o: object) -> bool:
		if not isinstance(o, Entry):
			return NotImplemented

		return all((
			self._type == o._type,
			self.path == o.path,
			self.etag == o.etag,
			self.nextcloud_id == o.nextcloud_id,
			self.parent_id == o.parent_id,
			self.last_updated == o.last_updated,
		))

	def __repr__(self):
		c = {"local": 33, "remote": 36, None: 35}[self._type]
		l = (self._type or '?')[0].upper()
		p = self.path
		e = (self.etag or '')[:8] or '?'
		i = self.nextcloud_id
		if type(self.last_updated).__name__ == 'datetime':
			u = self.last_updated.strftime('%m-%d %H:%M')
		else:
			u = self.last_updated or ''

		# return f"{i}@{l}:{p}[{e}|{u}]"
		return f"\x1b[{c};2m{i}@{l}:\x1b[22m{p}\x1b[2m[{e}|{u}]\x1b[m"

	def toJSON(self):
		l = (self._type or '?')[0].upper()
		p = self.path
		e = (self.etag or '')[:8] or '?'
		i = self.nextcloud_id
		if type(self.last_updated).__name__ == 'datetime':
			u = self.last_updated.strftime('%m-%d %H:%M')
		else:
			u = self.last_updated or ''

		return f"{i}@{l}:{p}[{e}|{u}]"

@dataclass
class EntryLocal(Entry):
	_type: Literal['local'] = 'local'
	_frappe_name: Optional[str] = None

	__hash__ = Entry.__hash__
	__eq__ = Entry.__eq__
	__repr__ = Entry.__repr__

	def make_copy(self) -> 'EntryLocal':
		return EntryLocal(
			path=self.path,
			etag=self.etag,
			nextcloud_id=self.nextcloud_id,
			parent_id=self.parent_id,
			last_updated=self.last_updated,

			_frappe_name=self._frappe_name,
		)



@dataclass
class EntryRemote(Entry):
	_type: Literal['remote'] = 'remote'
	nextcloud_id: int
	_file_info: Optional[FileInfo] = None

	__hash__ = Entry.__hash__
	__eq__ = Entry.__eq__
	__repr__ = Entry.__repr__

	def make_copy(self) -> 'EntryRemote':
		return EntryRemote(
			path=self.path,
			etag=self.etag,
			nextcloud_id=self.nextcloud_id,
			parent_id=self.parent_id,
			last_updated=self.last_updated,

			_file_info=self._file_info,
		)


def convert_entry_local_to_remote(local: EntryLocal):
	return EntryRemote(
		path=local.path,
		etag=local.etag,
		nextcloud_id=local.nextcloud_id,
		parent_id=local.parent_id,
		last_updated=local.last_updated,
	)

EntryPair = Tuple[EntryLocal, EntryRemote]
EntryPairOptLoc = Tuple[Optional[EntryLocal], EntryRemote]
EntryPairOptRem = Tuple[EntryLocal, Optional[EntryRemote]]
EntryPairOptional = Union[EntryPair, Tuple[EntryLocal, None], Tuple[None, EntryRemote], Tuple[Optional[EntryLocal], Optional[EntryRemote]]]
