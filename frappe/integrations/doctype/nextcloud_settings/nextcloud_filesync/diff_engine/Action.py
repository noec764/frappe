from dataclasses import dataclass
from typing import Optional
from typing_extensions import Literal

from .Entry import EntryLocal, EntryRemote


@dataclass(unsafe_hash=True, frozen=True)
class Action():
	# NOTE:
	# All actions should be idempotent.
	# This means that if you run the same action twice,
	# it should have the same result.

	# 'local' actions assume the remote nextcloud file to be the source of truth
	# 'remote' actions assume the local File document to be the source of truth
	# 'meta' actions handle metadata changes (local)
	# 'conflict' action is simply a marker of a conflict (local)

	type: Literal[
		# create a file, create a directory
		# NOTE: Frappe File documents aren't checked for duplication before insertion
		'local.create',
		'remote.create',

		# rename/move a file
		# NOTE: is done by updating the file_name and folder
		'local.file.moveRename',
		'remote.file.moveRename',

		# recursively rename/move a directory and its children
		# NOTE: the children's path changes MAY not appear in the diff
		#       if only the dir's filename changes.
		'local.dir.moveRenamePlusChildren',
		'remote.dir.moveRenamePlusChildren',

		# if file: delete a file
		# if dir: delete a directory and its children
		'local.delete',
		'remote.delete',

		# update the content of a file
		'local.file.updateContent',
		'remote.file.updateContent',

		# special case: update the etag of a directory
		'meta.updateEtag',

		# merge remote and local entries, with the remote entry being the source of truth
		'local.join',
		# merge remote and local entries, with the local entry being the source of truth
		'remote.join',

		# triggered by a local update (hook) ???
		'remote.createOrForceUpdate',

		# conflict
		'conflict',

		# conflict: local file has been updated after remote file
		'conflict.localIsNewer',

		# conflict: remote file has been updated after local file
		'conflict.remoteIsNewer',

		# conflict: one is a directory, the other is a file
		'conflict.incompatibleTypesDirVsFile',

		# conflict: different ids
		'conflict.differentIds',
	]
	local: Optional[EntryLocal] = None
	remote: Optional[EntryRemote] = None

	def __repr__(self) -> str:
		z = self.local if self.local else '\x1b[31mø\x1b[m'
		return f'{self.type.ljust(15)} {z} {self.remote}'

	def __eq__(self, o: object) -> bool:
		if not isinstance(o, Action):
			return NotImplemented

		return all((
			self.type == o.type,
			self.local == o.local,
			self.remote == o.remote,
		))

	def __post_init__(self):
		# valid_types = Action.__annotations__['type'].__args__
		valid_types = [
			'local.create',
			'local.file.moveRename',
			'local.dir.moveRenamePlusChildren',
			'local.delete',
			'local.file.updateContent',
			'local.join',
			'remote.create',
			'remote.file.moveRename',
			'remote.dir.moveRenamePlusChildren',
			'remote.delete',
			'remote.file.updateContent',
			'remote.join',
			'meta.updateEtag',
			'remote.createOrForceUpdate',
			'conflict',
			'conflict.localIsNewer',
			'conflict.incompatibleTypesDirVsFile',
			'conflict.differentIds',
		]
		valid_types += map(
			lambda s: s.replace('local', 'remote'),
			filter(lambda s: s.startswith('local'), valid_types))

		if self.type not in valid_types:
			raise ValueError(f'invalid type: {self.type}')

	def _invert(self):
		"""
		Convert remote/local action to local/remote action.
		Keep conflicts. Keep meta updates.
		"""

		t = self.type

		if t.startswith('local'):
			t = t.replace('local', 'remote')
		elif t.startswith('remote'):
			t = t.replace('remote', 'local')
		else:
			return self

		return Action(type=t, local=self.local, remote=self.remote)
