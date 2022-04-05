from contextlib import contextmanager
import json
import os
from datetime import datetime
from operator import attrgetter
from typing import Optional, Generator

import frappe
from frappe.core.doctype.file.file import File

from frappe.integrations.doctype.nextcloud_settings import NextcloudSettings, get_nextcloud_settings
from frappe.integrations.doctype.nextcloud_settings.exceptions import NextcloudSyncMissingRoot

from .diff_engine.Action import Action
from .diff_engine.utils import check_flag, doc_has_nextcloud_id, get_home_folder, set_flag
from .diff_engine.Entry import Entry
from .diff_engine.ConflictTracker import ConflictResolverNCF, ConflictStopper
from .diff_engine.utils_time import convert_local_time_to_utc

from owncloud.owncloud import FileInfo, HTTPResponseError

from frappe.utils.data import cstr

from .diff_engine import Common, DiffEngine, ActionRunner, RemoteFetcher

@contextmanager
def sync_module(*, commit_after=True, raise_exception=True, rollback_on_exception=True):
	# frappe.db.begin()  # begin transaction
	# frappe.db.commit()  # begin transaction
	try:
		settings = get_nextcloud_settings()
		sync = NextcloudFileSync(settings=settings)
		yield sync
		sync.client.logout()

		if commit_after:
			frappe.db.commit()
	except:
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
	with open('/tmp/nc_sync.txt', 'a') as f:
		f.write(' '.join(map(str, args)) + '\n')

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

		self.conflict_strategy = 'ignore'
		if self.settings.next_filesync_ignore_id_conflicts:
			self.conflict_strategy = 'resolve-from-diff'
			# self.conflict_strategy = 'resolve'

		if self.settings.filesync_override_conflict_strategy:
			self.conflict_strategy = self.settings.filesync_override_conflict_strategy

		self.client = self.settings.nc_connect()

		self.common = Common(
			client=self.client,
			settings=self.settings,
			logger=self.log,
		)

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

		self.runner = ActionRunner(self.common)

		self.fetcher = RemoteFetcher(self.common)

		self.use_profiler = False

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
		_profile_dt_start = frappe.utils.now_datetime()
		self.log(frappe.now().center(40, '-'))
		self.log(f'Sync started {last_update_dt.strftime("since %F %X (local time)") if last_update_dt else "from scratch"}')
		# self.log()

		# fetch all remote entries
		remote_entries = self._fetch(last_update_dt)
		self.log(f'fetched {len(remote_entries)} remote entries')
		# self.log(J(remote_entries))
		# self.log()
		if len(remote_entries) == 0:
			# this case will never be run,
			# since the root dir is always returned
			self.log('nothing to do, stopping')
			self.log()
			return

		# initialize diffing
		# remote_entries = frappe_realtime_tqdm(remote_entries, lambda e: e.path)
		actions_iterator = self.differ.diff_from_remote(remote_entries)

		if self.conflict_strategy == 'stop':
			conflict_stopper = ConflictStopper(self.common)
			actions_iterator = conflict_stopper.chain(actions_iterator)
		elif self.conflict_strategy == 'resolver-only':
			conflict_resolver = ConflictResolverNCF(self.common)
			actions_iterator = conflict_resolver.chain(actions_iterator)

		actions_iterator = list(actions_iterator)
		self.log(f'got {len(actions_iterator)} actions to run, conflict strategy is: {self.conflict_strategy}')
		self.log(J(actions_iterator))
		# self.log()

		# perform diffing + execute actions
		self.runner.run_actions(actions_iterator)

		# return the new value of the last_filesync_dt field of Nextcloud Settings
		newest_remote_entry = max(remote_entries, key=attrgetter('last_updated'))

		# self.log('* DONE at:', frappe.now())
		self.log('duration:', (frappe.utils.now_datetime() - _profile_dt_start).total_seconds(), 'seconds')
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
		# if last_update is None:
		# 	last_update = datetime.fromordinal(1)  # smallest date
		# for (i, d) in enumerate(dirs):
		# 	frappe.publish_realtime("progress", {
		# 		'progress': [i + 1, N],
		# 		'title': 'Cleaning up',
		# 		'description': d.file.path,
		# 	}, task_id='sync', user=frappe.session.user)
		# return last_update

	def sync_to_remote(self):
		...
		# self.timer_start('sync_to')

		# files = frappe.db.get_all(
		# 	'File', filters={'is_folder': 0}, fields=['name', 'nextcloud_id'])

		# files_with_id, unsynced_files = partition(
		# 	lambda f: f['nextcloud_id'] is None, files)

		# N = len(unsynced_files)
		# for (i, f) in enumerate(unsynced_files):
		# 	name = f['name']
		# 	doc = frappe.get_doc('File', name)
		# 	sync_log(f'* sync to remote: {doc} (no nextcloud id)')
		# 	self.save_to_remote(doc, event='sync')

		# 	frappe.publish_realtime("progress", {
		# 		'progress': [i + 1, N],
		# 		'title': 'Syncing Files',
		# 		'description': name,
		# 	}, task_id='sync', user=frappe.session.user)

		# frappe.publish_realtime(
		# 	"progress",
		# 	{'progress': [100, 100]},
		# 	task_id='sync',
		# 	user=frappe.session.user,
		# )

		# N = len(files_with_id)
		# for (i, f) in enumerate(files_with_id):
		# 	name = f['name']
		# 	nextcloud_id = f['nextcloud_id']
		# 	doc = frappe.get_doc('File', name)
		# 	sync_log(f'* sync to remote: {doc} ({nextcloud_id}@nextcloud)')
		# 	self.save_to_remote(doc, event='sync')

		# 	frappe.publish_realtime("progress", {
		# 		'progress': [i + 1, N],
		# 		'title': 'Syncing Files',
		# 		'description': name,
		# 	}, task_id='sync', user=frappe.session.user)

		# frappe.publish_realtime(
		# 	"progress",
		# 	{'progress': [100, 100]},
		# 	task_id='sync',
		# 	user=frappe.session.user,
		# )

	def save_to_remote(self, doc: File, event=None):
		...
		# sync_log(f'* save to remote: {doc}')

		# if check_flag(doc):
		# 	sync_log(f'  # skipping, flag nextcloud_triggered_update is set')
		# 	return  # avoid recursive updates

		# if doc.is_private:
		# 	sync_log(f'  # skipping, private file')
		# 	return

		# if doc.nextcloud_id:
		# 	try:
		# 		file = self.client.file_info_by_fileid(doc.nextcloud_id)
		# 	except HTTPResponseError:
		# 		file = None

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

		# site_path = frappe.utils.get_site_path()
		# subdir = 'public' if not doc.is_private else None
		# file_path = path_join_strip(site_path, subdir, doc.file_url)

	def _delete_remote_file_of_doc(
		self,
		doc,
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
			doc.nextcloud_id = None
			doc.nextcloud_parent_id = None
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


	def _create_or_force_update_doc_in_remote(self, doc: File, check_remote: bool = False):
		"""
			Upload the local file to the remote.
			If `check_remote` is True, try to find the matching remote file first, in order to perform a smarter sync if possible.
		"""
		local = self.common.convert_local_doc_to_entry(doc)

		remote = None
		if check_remote:
			if doc_has_nextcloud_id(doc):
				remote = self.common.get_remote_entry_by_id(doc.nextcloud_id)
			if remote is None:
				remote = self.common.get_remote_entry_by_path(local.path)

		self.runner.run_actions([
			Action(type='remote.createOrForceUpdate', local=local, remote=remote)
		])

	def check_id_of_home(self):
		try:
			local_home = get_home_folder()
		except:
			raise  # TODO: this is bad

		try:
			remote_home = self.fetcher.fetch_root(create_if_missing=False)
		except NextcloudSyncMissingRoot:
			remote_home = None
		except:
			raise

		local_id = cstr(local_home.nextcloud_id) \
			if local_home else None
		remote_id = cstr(remote_home.attributes[self.common._FILE_ID]) \
			if remote_home else None

		# local_etag = cstr(local_home.content_hash)
		# remote_etag = cstr(remote_home.get_etag()).strip('"')

		if (not local_id) and (not remote_id):  # never synced
			return { 'type': 'warn', 'message': 'never-synced', 'remoteId': local_id }
		elif local_id and (not remote_id):  # root was removed
			return { 'type': 'warn', 'message': 'no-remote', 'remoteId': local_id }
		elif (not local_id) and remote_id:  # root exists but is not synced
			return { 'type': 'warn', 'message': 'to-migrate', 'remoteId': None }
		elif local_id == remote_id:
			return { 'type': 'ok', 'message': 'same-ids', 'localId': local_id }
		elif local_id != remote_id:
			# if local_etag == remote_etag:
			# 	return {
			# 		'type':'ok',
			# 		'message': 'different-ids-but-same-etag',
			# 		'localId': local_id,
			# 		'remoteId': remote_id,
			# 	}
			return {
				'type': 'error',
				'localId': local_id,
				'remoteId': remote_id,
				'reason': 'different-ids',
			}

	def post_sync_success(self, last_update_dt2):
		self.settings.set_last_filesync_dt(dt_local=last_update_dt2)
		self.settings.db_set('next_filesync_ignore_id_conflicts', False)
		self.settings.db_set('filesync_override_conflict_strategy', '')

	# def enable_conflict_resolution_for_next_sync(self):
	# 	self.settings.db_set({
	# 		'next_filesync_ignore_id_conflicts': False,
	# 		'filesync_override_conflict_strategy': 'resolver-only',
	# 	})
