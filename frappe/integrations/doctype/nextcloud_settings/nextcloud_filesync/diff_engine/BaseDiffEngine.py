import itertools
from operator import attrgetter, itemgetter
from typing import Dict, Generator, Iterable, List, Optional, Set

from .Action import Action
from .Entry import Entry, EntryLocal, EntryPair, EntryPairOptional, EntryRemote


class BaseDiffEngineNC():
	"""
	The diffing engine, assumes entries have a 'nextcloud_id' field.
	"""

	# Static methods
	@staticmethod
	def sort_key(entry: Entry):
		return entry.path

	def log(self, *args, **kwargs):
		if self.logger:
			return self.logger(*args, **kwargs)
		print("\x1b[35;2m" "∂" "\x1b[m", *args, **kwargs)

	# Constructor
	def __init__(self, logger=None, use_conflict_detection=True):
		self.seen_pairs: Set[EntryPairOptional] = set()
		self.potential_deletions: Set[int] = set()
		self.pairs_queue: List[EntryPairOptional] = []

		self.sort_key = attrgetter('path')
		self.use_conflict_detection = use_conflict_detection
		self.logger = logger

	# Local access
	def get_local_entry_by_id(self, id: int) -> Optional[EntryLocal]:
		raise NotImplementedError

	def get_local_entry_by_path(self, path: str) -> Optional[EntryLocal]:
		raise NotImplementedError

	def get_local_children_ids(self, of_dir: Entry) -> Set[int]:
		raise NotImplementedError

	# Remote access
	def get_remote_entry_by_id(self, id: int) -> Optional[EntryRemote]:
		raise NotImplementedError

	def get_remote_entry_by_path(self, path: str) -> Optional[EntryRemote]:
		raise NotImplementedError

	def get_remote_children_entries(self, of_dir: EntryRemote) -> Dict[int, EntryRemote]:
		raise NotImplementedError

	# Individual diffing
	def _find_renames_and_deletions(self, directory: EntryPair):
		dir_entry: EntryRemote = directory[1]

		# self.log(' · find renames and deletions in', dir_entry.path)
		old_children_ids = self.get_local_children_ids(dir_entry)
		new_children = self.get_remote_children_entries(dir_entry)

		# ids of deleted files (deleted from this dir, on the remote)
		deletions: List[int] = []

		# ids of added files (added in this dir, on the remote)
		add_or_updates: List[int] = []

		# pairs of renamed files (still in this dir, in the remote)
		renames: List[EntryPair] = []

		# self.log(' · fetched/LOCAL  children ids:',
		#          ' '.join(map(str, old_children_ids)))
		# self.log(' · fetched/REMOTE children ids:',
		#          ' '.join(map(str, new_children.keys())))

		for id in old_children_ids:
			if id in new_children:
				# self.log('   |', 'L🏠 R🌐', id, self.get_local_entry_by_id(
				#     id), '<-', self.get_remote_entry_by_id(id), '[check renames]')

				# check renames
				remote = new_children[id]
				local = self.get_local_entry_by_id(remote.nextcloud_id)
				if not local:
					# self.log('   |', 'L🏠 R🌐', id, '<-',
					#          remote, '[no local entry]')
					continue

				# dp = dir_entry.path
				# lp = remove prefix of (local.path, dp)
				# rp = remove prefix of (remote.path, dp)
				# if lp != rp:
				#     renames.append((local, remote))  # renamed in dir
				#     self.log('> renamed in dir', lp, rp)
				if local.path != remote.path:
					renames.append((local, remote))  # moved
			else:
				# self.log('   |', 'L🏠 r×', id, self.get_local_entry_by_id(
				#     id), '<-', self.get_remote_entry_by_id(id), '[re/moved on remote]')
				# removed on remote
				deletions.append(id)

		for id in new_children:
			if id in old_children_ids:
				# self.log('   |', 'L🏠 R🌐', id, self.get_local_entry_by_id(
				#     id), '<-', self.get_remote_entry_by_id(id), '[do nothing]')
				# do nothing
				# is already inside the list anyway (addition or moved)
				pass  # add_or_updates.append(id)
			else:
				# self.log('   |', 'l× R🌐', id, self.get_local_entry_by_id(
				#     id), '<-', self.get_remote_entry_by_id(id), '[pot. del.]')
				# maybe removed from local
				add_or_updates.append(id)
				# deletions.append(id)

		# self.log(" -", f"{renames=}")
		# self.log(" -", f"{deletions=}")
		# self.log(" -", f"{add_or_updates=}")
		return renames, deletions, add_or_updates

	def _examine_now(self, pairs: Iterable[EntryPairOptional]):
		"""insert all the pairs at the beginning of the queue"""
		self.pairs_queue[0:0] = pairs

	def diff_file(self, local: EntryLocal, remote: EntryRemote) -> Generator[Action, None, None]:
		if local.path != remote.path:
			yield Action(type='local.file.moveRename', local=local, remote=remote)

		if local.etag != remote.etag:
			yield Action(type='local.file.updateContent', local=local, remote=remote)

	def diff_dir(self, local: EntryLocal, remote: EntryRemote) -> Generator[Action, None, None]:
		if local.path != remote.path:
			# Assumes that the rename is recursively applied to all the children
			yield Action(type='local.dir.moveRenamePlusChildren', local=local, remote=remote)

		if local.etag != remote.etag:
			renames, deletions, add_or_updates = self._find_renames_and_deletions(
				(local, remote))

			self.potential_deletions.update(deletions)
			self.potential_deletions.difference_update(add_or_updates)

			def id_to_pair(id: int):
				l = self.get_local_entry_by_id(id)
				r = self.get_remote_entry_by_id(id)
				return (l, r)

			add_or_updates = map(id_to_pair, add_or_updates)
			it: Iterable[EntryPair] = itertools.chain(renames, add_or_updates)
			it = filter(itemgetter(1), it)
			it = sorted(
				it,
				key=lambda x: self.sort_key(x[1]),
				reverse=True)

			self._examine_now(it)
			# self.log()

			yield Action(type='meta.updateEtag', local=local, remote=remote)

	def yield_if_conflict(self, local: EntryLocal, remote: EntryRemote, source='remote'):
		if not self.use_conflict_detection:
			return

		l_upd, r_upd = local.last_updated, remote.last_updated
		if source and (l_upd is not None) and (r_upd is not None):
			if (source == 'remote') and (l_upd > r_upd):
				yield Action('conflict.localIsNewer', local, remote)
			elif (source == 'local') and (l_upd < r_upd):
				yield Action('conflict.remoteIsNewer', local, remote)

		l_id, r_id = local.nextcloud_id, remote.nextcloud_id
		if (l_id is not None) and (r_id is not None) and (l_id != r_id):
			yield Action('conflict.differentIds', local, remote)

		if local.is_dir() != remote.is_dir():
			yield Action('conflict.incompatibleTypesDirVsFile', local, remote)

	def conflicts(self, local: EntryLocal, remote: EntryRemote, source='remote'):
		it = self.yield_if_conflict(local, remote, source)
		return list(it)

	def diff_pair(self, local: EntryLocal, remote: EntryRemote):
		if self.use_conflict_detection:
			c = self.conflicts(local, remote, source='remote')
			if c:
				yield from c
				return

		is_dir = remote.path.endswith('/')
		if is_dir:
			yield from self.diff_dir(local, remote)
		else:
			yield from self.diff_file(local, remote)

	def diff_remote_only(self, remote: EntryRemote):
		potential_local = self.get_local_entry_by_path(remote.path)
		if not potential_local:
			yield Action(type='local.create', remote=remote)
			return

		if self.use_conflict_detection:
			c = self.conflicts(potential_local, remote, 'remote')
			if c:
				yield from c
				return

		yield Action(type='local.join', local=potential_local, remote=remote)

	def diff_local_only(self, local: EntryLocal):
		potential_remote = self.get_remote_entry_by_path(local.path)
		if not potential_remote:
			yield Action(type='remote.create', local=local)
			return

		if self.use_conflict_detection:
			c = self.conflicts(local, potential_remote, 'local')
			if c:
				yield from c
				return

		yield Action(type='remote.join', local=local, remote=potential_remote)

	def diff_pair_from_remote(self, local: Optional[EntryLocal], remote: EntryRemote):
		if local:
			yield from self.diff_pair(local, remote)
		else:
			yield from self.diff_remote_only(remote)

	def diff_pair_from_local(self, local: EntryLocal, remote: Optional[EntryRemote]):
		if remote:
			yield from map(lambda a: a._invert(), self.diff_pair(local, remote))
		else:
			yield from self.diff_local_only(local)

	def diff_from_local(self, local_entries: List[EntryLocal]):
		"""[EXPERIMENTAL] diff all given entries"""
		local_entries.sort(key=self.sort_key)
		for local in local_entries:
			remote = None
			if local.nextcloud_id is not None:
				remote = self.get_remote_entry_by_id(local.nextcloud_id)
			yield from self.diff_pair_from_local(local, remote)

	def diff_from_remote(self, remote_entries: List[EntryRemote]):
		remote_entries.sort(key=self.sort_key)

		self.pairs_queue.extend(
			(self.get_local_entry_by_id(remote.nextcloud_id), remote)
			for remote in remote_entries
		)

		while self.pairs_queue:
			pair = self.pairs_queue.pop(0)
			local, remote = pair

			if not remote:
				self.log('\x1b[31mSKIP\x1b[m', local, remote)
				continue

			# self.log()
			# self.log('L' if local else '×',
			#          'R' if remote else '×', local, remote)

			if pair in self.seen_pairs:
				# self.log('\x1b[35mSEEN\x1b[m', local, remote)
				continue

			# self.log('\x1b[32mPAIR\x1b[m', pair)
			self.seen_pairs.add(pair)

			yield from self.diff_pair_from_remote(local, remote)

		seen_ids = set(
			map(lambda p: p[0].nextcloud_id if p[0] else None, self.seen_pairs))
		for deletion in self.potential_deletions:
			self.log('\x1b[31mdel ???', deletion, '\x1b[m')
			if deletion is not None and deletion not in seen_ids:
				self.log('\x1b[31mdel ...', deletion, '\x1b[m')
				local = self.get_local_entry_by_id(deletion)
				if local:
					self.log('\x1b[31;1mDEL !!!', local, '\x1b[m')
					yield Action(type='local.delete', local=local)
