from contextlib import contextmanager
import os
import json
from datetime import datetime
from operator import attrgetter
from typing import List, Optional, Generator
from typing_extensions import Literal
from dataclasses import dataclass

import frappe
from frappe.core.doctype.file.file import File

from frappe.integrations.doctype.nextcloud_settings import NextcloudSettings, get_nextcloud_settings
from frappe.integrations.doctype.nextcloud_settings.exceptions import NextcloudException, NextcloudSyncMissingRoot

from .diff_engine.Action import Action
from .diff_engine.utils import check_flag, doc_has_nextcloud_id, get_home_folder, set_flag
from .diff_engine.Entry import Entry, EntryRemote
from .diff_engine.ConflictTracker import ConflictResolverNCF, ConflictStopper
from .diff_engine.utils_time import convert_local_time_to_utc

from owncloud.owncloud import FileInfo, HTTPResponseError

from frappe.utils.data import cstr

from .diff_engine import Common, DiffEngine, ActionRunner, RemoteFetcher



logger = frappe.logger("nextcloud", allow_site=True, file_count=50)
logger.setLevel("DEBUG")


@dataclass
class BeforeSyncStatus:
	status: Literal['ok', 'error']
	sync_type: Literal['none', 'normal', 'all', 'initial', 'overwrite'] = 'none'
	message: str = ''


@contextmanager
def sync_module(*, commit_after=True, raise_exception=True, rollback_on_exception=True) -> Generator['NextcloudFileSync', None, None]:
	# frappe.db.begin()  # begin transaction
	# frappe.db.commit()  # begin transaction
	try:
		settings = get_nextcloud_settings()
		sync = NextcloudFileSync(settings=settings)
		yield sync
		sync.client.logout()

		if commit_after:
			frappe.db.commit()
	except Exception:
		if rollback_on_exception:
			frappe.db.rollback()  # rollback on error
		if raise_exception:
			raise


@contextmanager
def optional_sync_module(**kwargs) -> Generator[Optional['NextcloudFileSync'], None, None]:
	settings = get_nextcloud_settings()

	if frappe.flags.nextcloud_disable_filesync:
		yield None
		return

	if not (settings.enabled and settings.enable_sync):
		yield None
		return

	with sync_module(**kwargs) as syncer:
		yield syncer


def sync_log(*args):
	s = ' '.join(map(str, args))
	print(s)
	logger.info(s)

class MyEncoder(json.JSONEncoder):
	def default(self, obj):
		from dataclasses import is_dataclass
		if isinstance(obj, Entry):
			return obj.toJSON()
		elif isinstance(obj, FileInfo):
			return f"FileInfo<{obj.path}>"
		elif isinstance(obj, datetime):
			return obj.isoformat()
		elif is_dataclass(obj):
			return obj.__dict__
		else:
			return json.JSONEncoder.default(self, obj)

def J(x):
	return json.dumps(x, cls=MyEncoder, indent=2)

# def frappe_realtime_tqdm(iterable, desc: callable, count: int=None):
# 	if count is None and hasattr(iterable, '__len__'):
# 		count = len(iterable)
# 	if count is None:
# 		count = 9999999999999
# 	for (i, x) in enumerate(iterable):
# 		frappe.publish_realtime("progress", {
# 			'progress': [i + 1, count],
# 			'title': 'Cleaning up',
# 			'description': desc(x),
# 		}, task_id='sync', user=frappe.session.user)
# 		yield x


class NextcloudFileSync:
	def __init__(self, settings: NextcloudSettings):
		# TODO: Il faut que la première synchronisation soit [peut-être] faite manuellement ?
		# car très longue

		# TODO: Au-delà de 5000 fichiers (500 secondes) à synchroniser, on peut alerter l'utilisateur
		# pour le prévenir du risque de performances diminuées.
		# ET que la synchronisation sera pas complète avant un certain temps.

		# Mapping Dossier --> User (implicitement avec le nom du dossier)
		# TODO: ne synchroniser que les utilisateurs (email) existants
		# TODO: quand utilisateur créé -> synchro dossier vers utilisateur
		# « Mon dossier n'existe pas dans Dodock » --> Indiquer qu'il faut créer un utilisateur.

		# frappe.log_error()

		self.settings = settings

		self.client = self.settings.nc_connect()

		self.common = Common(
			client=self.client,
			settings=self.settings,
			logger=self.log,
		)

		self.runner = ActionRunner(self.common)

		self.fetcher = RemoteFetcher(self.common)

		self.conflicts: List[Action] = []

		if self.settings.filesync_override_conflict_strategy:
			self.set_conflict_strategy(
				self.settings.filesync_override_conflict_strategy
			)
		elif self.settings.next_filesync_ignore_id_conflicts:
			self.set_conflict_strategy('resolve-from-diff')  # or 'resolve'
		else:
			self.set_conflict_strategy('ignore')


	def set_conflict_strategy(self, new_conflict_strategy: str):
		self.conflict_strategy = new_conflict_strategy

		use_conflict_detection = True  # pessimistic
		diff_even_when_conflict = False  # optimisation

		if self.conflict_strategy == 'resolver-only':
			# emit conflicts, but leave their resolution to the resolver
			use_conflict_detection, diff_even_when_conflict = True, False
		elif self.conflict_strategy == 'resolve-from-diff':
			# emit conflicts, but also emit corrective actions from differ
			use_conflict_detection, diff_even_when_conflict = True, True
		elif self.conflict_strategy == 'UNSAFE-disable-conflict-detection':
			# emit conflicts, but also emit corrective actions from differ
			use_conflict_detection, diff_even_when_conflict = False, True
		else:
			use_conflict_detection, diff_even_when_conflict = True, False

		self.differ = DiffEngine(
			self.common,
			use_conflict_detection=use_conflict_detection,
			continue_diffing_after_conflict=diff_even_when_conflict,
		)


	def complete_sync(
		self,
		conflict_strategy: str = None,
		down_sync_all: bool = False,
		force_upload: bool = False,
		interactive: bool = False,
		commit: bool = True,
		rollback_on_error: bool = True,
	):
		"""
		Do a complete sync, including uploading unsynced files, logging conflicts to the user, database commit/rollback.

		Args:
			conflict_strategy (str): The strategy to use for conflict resolution. Defaults to None (aka 'ignore').
			down_sync_all (bool): Detect files even if their modification date is prior to the last sync. Defaults to False.

			force_upload (bool): Clear all the nextcloud_id's of the local Files before uploading them again. Defaults to False.

			interactive (bool): Display real time messages to the user. Defaults to False.
			commit (bool): Defaults to True.
			rollback_on_error (bool): Defaults to True.
		"""

		self.log(f"complete_sync(conflict_strategy={conflict_strategy}, down_sync_all={down_sync_all}, force_upload={force_upload})")

		if not self.can_run_filesync():
			self.log("↳ complete_sync cancelled")
			return

		if conflict_strategy:
			self.set_conflict_strategy(conflict_strategy)

		try:
			# Perform a pre-sync migration to the cloud
			self.migrate_to_remote(force=force_upload)

			# Perform the sync, mirroring the cloud
			if down_sync_all:
				self.sync_from_remote_all()
			else:
				self.sync_from_remote_since_last_update()

			# Log conflicts to the user
			if interactive and self.conflicts:
				frappe.msgprint(frappe._('Some conflicts were found during the Nextcloud sync, check the Error Log for more information.'))

			# success
			if commit:
				frappe.db.commit()
		except:
			if rollback_on_error:
				frappe.db.rollback()
			raise

	def preserve_remote_root_bak(self):
		self.log('* Creating backup of remote root dir...')
		bak = self.common.root.rstrip('/') + '.bak'

		try:
			self.client.delete(bak)
			self.log('↳ deleted previous backup')
		except HTTPResponseError as e:
			if e.status_code != 404:
				raise

		try:
			self.client.move(self.common.root, bak)
			self.log('↳ created backup by renaming')
		except HTTPResponseError as e:
			if e.status_code != 404:
				raise

		self.log('↳ done: ' + bak)
		return True

	def _log(self, *args):
		sync_log(*args)

	def log(self, *args):
		self._log(*args)

	def _fetch(self, last_update_dt: datetime = None):
		if last_update_dt is None:
			files = self.fetcher.fetch_all()
		else:
			dt_utc = convert_local_time_to_utc(last_update_dt)
			files = self.fetcher.fetch_since_utc(dt_utc)

		remote_entries = list(map(self.common.convert_remote_file_to_entry, files))
		remote_entries.sort(key=attrgetter('path'))
		return remote_entries

	def _sync(self, last_update_dt: datetime = None):
		sync_start_dt = frappe.utils.now_datetime()

		self.log(f'Sync all {last_update_dt.strftime("updated since %F %X (local time)") if last_update_dt else "from scratch"}')

		# fetch all remote entries
		remote_entries = self._fetch(last_update_dt)
		self.log(f'fetched {len(remote_entries)} remote entries:', J(remote_entries))

		if len(remote_entries) == 0:
			# this case will never be run,
			# since the root dir is always returned
			self.log('nothing to do, stopping')
			return

		# initialize diffing
		# remote_entries = frappe_realtime_tqdm(remote_entries, lambda e: e.path)
		actions_iterator = self.differ.diff_from_remote(remote_entries)

		if self.conflict_strategy == 'stop':
			conflict_stopper = ConflictStopper()
			actions_iterator = list(conflict_stopper.chain(actions_iterator))
			self.conflicts.extend(conflict_stopper._local_conflicts)
		elif self.conflict_strategy == 'resolver-only':
			conflict_resolver = ConflictResolverNCF(self.common)
			actions_iterator = list(conflict_resolver.chain(actions_iterator))

		self.log(f'got {len(actions_iterator)} actions to run:', J(actions_iterator))

		self.log(f'running actions... (conflict strategy is "{self.conflict_strategy}")')

		# perform diffing + execute actions
		self.runner.run_actions(actions_iterator)

		# return the new value of the last_filesync_dt field of Nextcloud Settings
		newest_remote_entry = max(remote_entries, key=attrgetter('last_updated'))

		sync_duration = frappe.utils.now_datetime() - sync_start_dt
		self.log('all done in:', round(sync_duration.total_seconds(), 3), 'seconds')
		self.log()

		last_update_dt2 = min(sync_start_dt, newest_remote_entry.last_updated)
		if last_update_dt is not None and (last_update_dt2 < last_update_dt):
			last_update_dt2 = last_update_dt  # can't be decreasing

		self.post_sync_success(last_update_dt2)

	def sync_from_remote_all(self):
		self._sync(last_update_dt=None)

	def sync_from_remote_since_last_update(self):
		self.sync_from_remote_since(self.settings.get_last_filesync_dt())

	def sync_from_remote_since(self, last_update_dt: datetime):
		self._sync(last_update_dt=last_update_dt)


	def _unjoin_all_files(self):
		"""Clear the `nextcloud_id` and `nextcloud_parent_id` of all the local Files."""
		frappe.db.sql("""
			update `tabFile` set `nextcloud_id` = NULL, `nextcloud_parent_id` = NULL
		""")


	def migrate_to_remote(self, force=False, *, DANGER_clear_remote_files=False):
		if not self.can_run_filesync(): return

		if DANGER_clear_remote_files:
			self.client.delete(self.common.root)

		if force:
			self._unjoin_all_files()

		# unsynced files are those that:
		# - have no nextcloud_id
		# - have been modified after the last sync
		unsynced_files = frappe.db.sql("""
			select `name` from `tabFile`
			where (
					ifnull(`nextcloud_id`, '') = ''
					or `modified` > %(last_sync)s
				) and not (`is_private` and %(exclude_private)s)
			order by folder, file_name
		""", values={
			'last_sync': self.settings.get_last_filesync_dt(),
			'exclude_private': self.settings.filesync_exclude_private,
		},
			as_dict=True,
		)

		for f in unsynced_files:
			name = f['name']
			doc = frappe.get_doc('File', name)
			self._upload_to_remote(doc, event='sync')


	def _upload_to_remote(self, doc: File, event=None):
		self.log(f'* upload to remote: {doc} (event={event})')

		if check_flag(doc):
			self.log('↳ skipping, flag nextcloud_triggered_update is set')
			return  # avoid recursive updates

		if self.settings.filesync_exclude_private:
			if doc.is_private:
				self.log('↳ skipping, file is private')
				return  # skipping private files

		self._create_or_force_update_doc_in_remote(doc, check_remote=True)


	def file_on_trash(self, doc: File):
		self.log(f'* DELETE: {doc}')
		if not self.can_run_filesync(doc): return

		if not doc_has_nextcloud_id(doc):
			self.log(f'↳ skipping: no nextcloud_id')
			return

		try:
			self._delete_remote_file_of_doc(
				doc,
				update_doc=False,  # don't need to update document, because it will be deleted
				update_parent_etag=True  # do update the parent's etag (its content changed)
			)
		except:
			return


	def _delete_remote_file_of_doc(
		self,
		doc: File,
		*,
		update_doc=False,
		update_parent_etag=False,
	):
		nextcloud_id = doc.nextcloud_id
		try:  # remove remote file
			remote_file = self.client.file_info_by_fileid(nextcloud_id)
			assert remote_file is not None
			self.client.delete(remote_file.path)
			self.log(f'↳ okay {doc} ({nextcloud_id}@nextcloud): removed nextcloud file')
		except Exception as e:
			self.log(f'↳ fail {doc} ({nextcloud_id}@nextcloud): failed to remove nextcloud file')
			self.log(e)
			raise

		if update_parent_etag:
			if doc.nextcloud_parent_id:
				self._update_etag_for_id(doc.nextcloud_parent_id)

		if update_doc:
			doc.db_set({
				'nextcloud_id': None,
				'nextcloud_parent_id': None,
			})
			self.log(f'↳ updated {doc} to remove nextcloud_id')
			set_flag(doc)


	def _update_etag_for_id(self, nextcloud_id: int):
		local = self.common.get_local_entry_by_id(nextcloud_id)
		remote = self.common.get_remote_entry_by_id(nextcloud_id)
		if local and remote:
			self.runner.run_actions([
				Action(type='meta.updateEtag', remote=remote, local=local)
			])


	def file_on_create(self, doc: File):
		self.log(f'* CREATE: {doc}')
		if not self.can_run_filesync(doc): return

		if doc_has_nextcloud_id(doc):
			raise ValueError('File already has a nextcloud_id')

		self._create_or_force_update_doc_in_remote(doc, check_remote=True)
		set_flag(doc)


	def file_on_update(self, doc: File):
		self.log(f'* UPDATE: {doc}')
		if not self.can_run_filesync(doc, ignore_private_check=True): return

		is_excluded_because_private = doc.is_private and self.settings.filesync_exclude_private
		if is_excluded_because_private:
			self.log('↳ checking if private file was public…')
			# We should not update this private file, but...

			# if the file has been synced
			if not doc_has_nextcloud_id(doc): return self.log(' → skip (not synced)')

			# and if the file WAS public
			prev_doc: dict = doc.get_doc_before_save() or {}
			was_public = not prev_doc.get('is_private')
			if not was_public: return self.log(' → skip (was not public)')

			# then it is BECOMING private
			# so, it must be deleted from the remote
			# because it might have been uploaded before.
			self.log('↳ file is becoming private: delete from remote')
			self._delete_remote_file_of_doc(doc, update_doc=True, update_parent_etag=True)
			return

		if not self.can_run_filesync(doc): return  # maybe not needed
		self._create_or_force_update_doc_in_remote(doc, check_remote=True)


	def can_run_filesync(self, doc: File = None, *, ignore_private_check=False, is_hook=False):
		if not self.settings.enabled:
			self.log('↳ WILL NOT RUN: nextcloud integration disabled')
			return False

		if not self.settings.enable_sync:
			self.log('↳ WILL NOT RUN: file sync disabled')
			return False

		if frappe.flags.nextcloud_disable_filesync:
			self.log('↳ WILL NOT RUN: file sync disabled by flag')
			return False

		if is_hook and frappe.flags.nextcloud_disable_filesync_hooks:
			self.log('↳ WILL NOT RUN: all hooks disabled')
			return False

		if doc:
			if check_flag(doc):
				# skipping because the file was already handled
				self.log('↳ WILL NOT RUN: flag is set on file', doc)
				return False

			if self.settings.filesync_exclude_private and not ignore_private_check:
				if doc.is_private:  # skipping private files
					self.log('↳ WILL NOT RUN: file is private', doc)
					return False

		return True


	def _check_weird_duplicate(self, doc: File, remote: EntryRemote):
		if not doc_has_nextcloud_id(doc):
			exists = frappe.db.exists('File', {'nextcloud_id': remote.nextcloud_id})
			if exists and doc.name != exists:
				return exists

		return False

	def _create_or_force_update_doc_in_remote(self, doc: File, check_remote: bool = False):
		"""
			Upload the local file to the remote.
			If `check_remote` is True, try to find the matching remote file first, in order to perform a smarter sync if possible.
		"""
		local = self.common.convert_local_doc_to_entry(doc)

		self.log('*** _create_or_force_update_doc_in_remote', doc, check_remote)

		remote = None
		if check_remote:
			if doc_has_nextcloud_id(doc):
				remote = self.common.get_remote_entry_by_id(doc.nextcloud_id)
			if remote is None:
				remote = self.common.get_remote_entry_by_path(local.path)
				if remote:
					dupl: str = self._check_weird_duplicate(doc, remote)
					if dupl:
						dupl_doc: File = frappe.get_doc('File', dupl)
						self.log(f'a duplicate of file {doc} has been found: {dupl_doc}')
						name, ext = os.path.splitext(dupl_doc.file_name)
						dupl_doc.file_name = name + ' (2)' + ext
						dupl_doc.add_comment(text='Nextcloud: This file is a duplicate.')
						dupl_doc.save()

		try:
			self.runner.run_actions([
				Action(type='remote.createOrForceUpdate', local=local, remote=remote)
			])
		except HTTPResponseError as e:
			if e.status_code == 409 or e.status_code == 404 or e.status_code == 405:
				# The remote parent dir is missing,
				# so we try to create the parent hierarchy.
				# The system could also just wait for the next sync to upload the missing files.
				self.log(e)
				self.log('Failed to do remote.createOrForceUpdate', local, remote)
				self.log('Trying by first creating parent hierarchy')

				actions = []
				cur_doc = doc
				loop_guard = 10

				while cur_doc and cur_doc.folder not in ('', None):
					l = self.common.convert_local_doc_to_entry(cur_doc)
					r = None

					if l.nextcloud_id:
						r = self.common.get_remote_entry_by_id(l.nextcloud_id)

					if not r:
						r = self.common.get_remote_entry_by_path(l.path)

					if r:
						break

					a = Action(type='remote.createOrForceUpdate', local=l, remote=None)
					actions.append(a)

					loop_guard -= 1
					if loop_guard < 0:
						raise NextcloudException('Failed to create hierarchy after failed remote.createOrForceUpdate: hierarchy is deeper than 10 directories') from e

					cur_doc = frappe.get_doc('File', cur_doc.folder)

				actions.reverse()
				self.log(' * ' + '\n * '.join(map(repr, actions)))
				self.runner.run_actions(actions)
			else:
				raise

	def get_before_sync_status(self):
		if not self.can_run_filesync():
			return BeforeSyncStatus('ok', 'none', message='disabled')

		# Fetch local and remote root directories
		try:
			local_home = get_home_folder()
		except frappe.DoesNotExistError:
			raise  # TODO: this is bad

		local_id = cstr(local_home.nextcloud_id)

		try:
			remote_home = self.fetcher.fetch_root(create_if_missing=False)
		except NextcloudSyncMissingRoot:
			remote_home = None

		# If the remote dir does not exist
		if not remote_home:
			if local_id:
				potential_remote_home = self.client.file_info_by_fileid(local_id)
				if potential_remote_home:
					print('RENAMED', self.settings.path_to_files_folder, '->', potential_remote_home.path)
					self.settings.db_set('path_to_files_folder', potential_remote_home.path)
					# The remote root directory was moved/renamed.
					# We have to make a choice here:

					# 1. We can ignore the fact that a remote directory
					# already exists and pursue with a force-upload,
					# creating a new remote directory. In this case,
					# data loss can NOT happen, data duplication might.

					# 2. Or we can adjust the `path_to_files_folder` value
					# by assuming that the users wanted to rename the folder
					# but keep it synchronized. In this case, data loss CAN
					# happen on the local files, because most local files
					# are expected to not be uploaded before syncing, which
					# means that, in the case of a wrong rename detection,
					# a possibly empty remote dir might get synced to the
					# local files.
					# return BeforeSyncStatus('ok', ['adjust-root', 'force-upload', 'down-sync'])
					return BeforeSyncStatus('ok', 'initial')

			# Knowing that the Home directory is not synced is not enough
			# to be sure that all its local children are also not synced.
			# Simply soft-uploading the files, some of which could have a
			# nextcloud_id, possibly a remote mirror, would not be enough
			# to correctly copy all the local files to the remote server.
			# So, the files have to be force-uploaded.
			# return BeforeSyncStatus('ok', ['force-upload', 'down-sync'])
			return BeforeSyncStatus('ok', 'initial')

		# Both local and remote dirs exist
		# Detect if they are correctly linked
		if not local_id:
			# Local and remote roots are not linked.
			# But the remote root dir exists, which means that an up-sync
			# COULD lead to data loss (by overwrite) on the remote files.
			# remote_is_empty = len(self.client.list(remote_home.path))
			# return BeforeSyncStatus('ok', ['up-sync', 'down-sync'])
			return BeforeSyncStatus('ok', 'normal')

		remote_id = cstr(remote_home.attributes[self.common._FILE_ID])
		if local_id != remote_id:
			# return BeforeSyncStatus('error', message='home-different-ids')
			return BeforeSyncStatus('ok', 'overwrite')

		# return BeforeSyncStatus('ok', ['up-sync', 'down-sync'])
		return BeforeSyncStatus('ok', 'normal')

	def post_sync_success(self, last_update_dt2):
		self.settings.set_last_filesync_dt(dt_local=last_update_dt2)
		self.settings.db_set('next_filesync_ignore_id_conflicts', False)
		self.settings.db_set('filesync_override_conflict_strategy', '')

	# def enable_conflict_resolution_for_next_sync(self):
	# 	self.settings.db_set({
	# 		'next_filesync_ignore_id_conflicts': False,
	# 		'filesync_override_conflict_strategy': 'resolver-only',
	# 	})
