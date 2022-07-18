from typing import Iterable

from .Common import Common
from .DeferredTasks import DeferredTasks
from .utils_normalize_paths import util_denormalize_to_local_path
from .Action import Action

# NOTE: possible optimisation, sort prefixes and do a binary search by length then text

import frappe  # type: ignore


class ConflictTracker:
	def __init__(self):
		self._conflict_prefixes = set()
		self._confict_paths = set()
		self._local_conflicts = []

	def chain(self, it: Iterable[Action]):
		"""
		Returns an iterator over the input actions, effectively being transparent.
		"""
		for action in it:
			self.on_before_action_run(action)
			yield action

	def _check_conflict_for_path(self, path: str):
		if path in self._confict_paths:
			return True
		for prefix in self._conflict_prefixes:
			if path.startswith(prefix):
				return True
		return False

	def _track_conflict(self, action: Action):
		l, r = action.local, action.remote
		path = r.path if r else l.path if l else ''
		is_dir = (r.is_dir() if r else False) or (l.is_dir() if l else False)

		if is_dir:
			prefix = path.rstrip('/') + '/'
			self._conflict_prefixes.add(prefix)
		self._confict_paths.add(path)
		self._local_conflicts.append(action)

	def on_before_action_run(self, action: Action) -> bool:
		"""
		Returns False if the action can be run.
		Returns True if the action should be skipped.
		"""
		if action.type.startswith('conflict'):
			self._track_conflict(action)
			return True
		return False


class ConflictStopper(ConflictTracker):
	def __init__(self):
		super().__init__()
		self._skipped_actions = []

	def chain(self, it: Iterable[Action]):
		"""
		Returns an iterator over the non-conflicted actions.
		"""
		for action in it:
			if self.on_before_action_run(action):
				continue
			yield action

	def map_state(self, it: Iterable[Action]):
		for action in it:
			skip = self.on_before_action_run(action)
			yield skip, action

	def on_before_action_run(self, action: Action):
		if action.type.startswith('conflict'):
			self._track_conflict(action)
			return True

		path = action.remote.path if action.remote else action.local.path if action.local else ''
		if self._check_conflict_for_path(path):
			print(f'\x1b[1;31m[conflict]\x1b[0m',
				  action.type, action.local, action.remote)
			self._skipped_actions.append(action)
			return True

		return False


class ConflictResolverNCF(ConflictTracker):
	def __init__(self, common: Common):
		super().__init__()
		self.common = common
		self.deferred_tasks = DeferredTasks()
		# self.repaired_list = []

	def chain(self, it: Iterable[Action]):
		"""
		Returns an iterator over the non-conflicted actions, and resolves conflicts if possible.
		"""
		for action in it:
			actions_to_resolve_now = self.on_before_action_run(action)
			if actions_to_resolve_now:
				yield from actions_to_resolve_now
			else:
				yield action

		# run deferred task and emit their actions too
		for actions in self.deferred_tasks:
			if actions:
				yield from actions


	@staticmethod
	def _upload_frappe_file(action: Action):
		yield Action(type='remote.createOrForceUpdate', local=action.local, remote=action.remote)

	def _resolve_conflict(self, action: Action):
		t = action.type
		l = action.local
		r = action.remote

		# print(action)
		# try:
		#     while True:
		#         cmd = input("break> ")
		#         if not cmd:
		#             break
		#         print(eval(cmd))
		# except EOFError:
		#     exit()

		if t == 'conflict.localIsNewer':
			return self.deferred_tasks.push(self._upload_frappe_file, action)
			# raise NotImplementedError
			assert l
			doc = frappe.get_doc('File', l._frappe_name)
			doc.save()
			# self.common.cloud_client.put_file_contents(l.path, l)
			yield  # empty generator
			return print('save file')
		elif t == 'conflict.incompatibleTypesDirVsFile':
			raise NotImplementedError
			assert l
			assert r
			# rename the file by appending __local
			if not l.is_dir():
				# Local is the simple file
				folder, file_name = util_denormalize_to_local_path(l.path)
				frappe.db.set_value(
					'File', l._frappe_name,
					'file_name', file_name + '__conflicted',
					modified=r.last_updated)
			else:
				# Remote is the simple file
				p = self.common.denormalize_remote(r.path)
				print(f"move({p}, {p + '__conflicted'})")
				# self.common.cloud_client.move(p, p + '__conflicted')

			yield  # empty generator
			return print('delete file')
		elif t == 'conflict.differentIds':
			yield
			raise NotImplementedError
		else:
			yield
			raise NotImplementedError

		# self.repaired_list.append(action)
		# l, r = action.local, action.remote
		# if not (l and r):
		#     print(f'\x1b[1;31m[conflict]\x1b[0m')
		#     return False
		# if action.type == 'local.join':
		#     etagL, etagR = l.etag, r.etag
		#     if etagL != etagR:
		#         self.action

	def on_before_action_run(self, action: Action):
		if action.type.startswith('conflict'):
			self._track_conflict(action)
			return self._resolve_conflict(action)

		path = action.remote.path if action.remote else action.local.path if action.local else ''
		if self._check_conflict_for_path(path):
			return self._resolve_conflict(action)
