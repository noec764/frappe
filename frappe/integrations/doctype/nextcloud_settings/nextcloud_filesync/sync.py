import json
import os
from datetime import datetime
from operator import attrgetter

import frappe
from frappe.core.doctype.file.file import File
from frappe.integrations.doctype.nextcloud_settings import get_nextcloud_settings
from frappe.integrations.doctype.nextcloud_settings.nextcloud_filesync.diff_engine.ConflictTracker import ConflictResolverNCF
from frappe.integrations.doctype.nextcloud_settings.nextcloud_filesync.diff_engine.utils_time import convert_local_time_to_utc
from frappe.integrations.doctype.nextcloud_settings.nextcloud_settings import NextcloudSettings

from owncloud.owncloud import FileInfo, HTTPResponseError

from frappe.utils.data import cstr

from .diff_engine import Common, DiffEngine, ActionRunner, RemoteFetcher

def sync_log(*args):
	with open('/tmp/nc_sync.txt', 'a') as f:
		f.write(' '.join(map(str, args)) + '\n')

class MyEncoder(json.JSONEncoder):
	def default(self, obj):
		from dataclasses import is_dataclass
		if isinstance(obj, FileInfo):
			return f"FileInfo<{obj.path}>"
		if isinstance(obj, datetime):
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
	def __init__(self):
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

		self.settings = get_nextcloud_settings()
		self.client = self.settings.nc_connect(debug=True)
		self.common = Common(
			owncloud_client=self.client,
			settings=self.settings,
			logger=self.log,
		)
		self.differ = DiffEngine(self.common)
		self.runner = ActionRunner(self.common)
		self.fetcher = RemoteFetcher(self.common)

		self.use_profiler = False

	def log(self, *args):
		sync_log(*args)

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
		self.log('-'*40)
		self.log('Sync started')
		self.log(f'last_update_dt: {last_update_dt.strftime("%F %X") if last_update_dt else None}')
		self.log()

		# fetch all remote entries
		remote_entries = self._fetch(last_update_dt)
		self.log(f'fetched {len(remote_entries)} remote entries:')
		self.log(J(remote_entries))
		self.log()
		if len(remote_entries) == 0:
			return

		# initialize diffing
		# remote_entries = frappe_realtime_tqdm(remote_entries, lambda e: e.path)
		actions_iterator = self.differ.diff_from_remote(remote_entries)

		# if self.settings.next_filesync_ignore_id_conflicts:
		# 	conflict_resolver = ConflictResolverNCF(self.common)
		# 	actions_iterator = conflict_resolver.chain(actions_iterator)

		actions_iterator = list(actions_iterator)
		self.log(f'got {len(actions_iterator)} actions to run:')
		self.log(J(actions_iterator))
		self.log()

		# perform diffing + execute actions
		self.runner.run_actions(actions_iterator)

		# return the new value of the last_filesync_dt field of Nextcloud Settings
		newest_remote_entry = max(remote_entries, key=attrgetter('last_updated'))

		self.log('*DONE*')
		self.log()
		last_update_dt2 = min(frappe.utils.now_datetime(), newest_remote_entry.last_updated)
		self.post_sync_success()
		return last_update_dt2

	def sync_from_remote_all(self):
		last_update_dt = self._sync(last_update_dt=None)
		self.settings.set_last_filesync_dt(dt_local=last_update_dt)
		return last_update_dt

	def sync_from_remote_since_last_update(self):
		return self.sync_from_remote_since(self.settings.get_last_filesync_dt())

	def sync_from_remote_since(self, last_update_dt: datetime):
		new_last_update_dt = self._sync(last_update_dt=last_update_dt)
		self.settings.set_last_filesync_dt(new_last_update_dt)
		return last_update_dt
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

		# files = frappe.db.get_list(
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

		# if doc.flags.nextcloud_triggered_update:
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

		# 	if file is None:
		# 		sync_log(f'  ! has nextcloud_id but no remote file')
		# 		doc.nextcloud_id = None
		# 	else:
		# 		sync_log(f'  # skipping, is already remote')
		# 		return

		# if doc.is_folder:
		# 	sync_log(f'  - is folder')
		# 	# folder, only create on remote
		# 	base_path = self.settings.get_upload_path()
		# 	remote_dir = path_join_strip(
		# 		base_path, doc.folder.lstrip('Home/'), doc.file_name)
		# 	sync_log(f'  - remote.mkdir_p: {remote_dir}')
		# 	self.client.mkdir_p(remote_dir)
		# 	return

		# sync_log(f'  - is normal file')
		# if not doc.file_url:
		# 	sync_log(f'  ! missing file_url')
		# 	# doc should at least have a file_url,
		# 	# which should also be a filesystem path (check later)
		# 	return

		# site_path = frappe.utils.get_site_path()
		# subdir = 'public' if not doc.is_private else None
		# file_path = path_join_strip(site_path, subdir, doc.file_url)

		# if not os.path.exists(file_path):
		# 	sync_log(f'  ! missing file on filesystem')
		# 	# missing file on Frappe's side,
		# 	# therefore can't upload it to remote
		# 	return

		# base_path = self.settings.get_path_to_files_folder()
		# remote_dir = path_join_strip(
		# 	base_path, doc.owner, doc.attached_to_doctype)

		# sync_log(f'  - remote.mkdir_p: "{remote_dir}"')
		# self.client.mkdir_p(remote_dir)

		# remote_path = path_join_strip(remote_dir, doc.file_name)
		# sync_log(f'  - remote.put_file: "{remote_path}" <- "{file_path}"')
		# self.client.put_file(remote_path, file_path)

		# file: FileInfo = self.client.file_info(
		# 	remote_path, properties=self._QUERY_PROPS)
		# if file:
		# 	res = self._get_res(file)
		# 	nextcloud_id = res.file_id
		# 	doc.db_set('nextcloud_id', nextcloud_id, update_modified=False)
		# 	meta = create_or_update_filemeta(res)
		# 	sync_log(f'  - .nextcloud_id: {nextcloud_id}')
		# 	sync_log(f'  - .meta: {meta}')
		# else:
		# 	sync_log(f'  ! maybe failed to upload remote file')

		# remove local file data
		# if nextcloud_settings.enable_migrate_to_nextcloud:
		# 	update_with_link(doc, build_link(nextcloud_settings, remote_path))

	def file_on_trash(self, doc: File):
		...
		# sync_log(f'* on_trash: {doc}')

		# nextcloud_id = doc.get('nextcloud_id', None)
		# if nextcloud_id is None:
		# 	return

		# try:  # remove remote file
		# 	remote_file = self.client.file_info_by_fileid(nextcloud_id)
		# 	self.client.delete(remote_file.get_path())
		# 	sync_log(
		# 		f'* {doc} ({nextcloud_id}@nextcloud): remove nextcloud file')
		# except Exception:
		# 	sync_log(
		# 		f'! {doc} ({nextcloud_id}@nextcloud): failed to remove nextcloud file')

		# try:  # remove meta
		# 	meta = get_frappe_filemeta(nextcloud_id)
		# 	if meta:
		# 		meta.delete()
		# 	sync_log(f'* {doc} ({nextcloud_id}@nextcloud): removed meta')
		# except Exception:
		# 	sync_log(
		# 		f'! {doc} ({nextcloud_id}@nextcloud): failed to remove meta')

	def file_on_update(self, doc: File):
		...
		# nextcloud_id = doc.get('nextcloud_id', None)
		# if nextcloud_id is None:
		#     return

	def check_id_of_home(self):
		try:
			local_home = frappe.get_doc('File', 'Home')
		except:
			raise  # TODO: this is bad

		try:
			remote_home = self.fetcher.fetch_root()
		except:
			raise  # failed to make root

		local_id = cstr(local_home.nextcloud_id)
		remote_id = cstr(remote_home.attributes[self.common._FILE_ID])

		if not local_id:
			# never synced
			return { 'type': 'ok', 'message': 'never-synced', 'remoteId': local_id }
		elif not remote_id:
			# TODO: bad
			raise ValueError('could not get the fileid of the remote home')
		elif local_id == remote_id:
			return { 'type': 'ok', 'message': 'same-ids', 'localId': local_id }
		elif local_id != remote_id:
			return {
				'type':'error',
				'localId': local_id,
				'remoteId': remote_id,
				'reason': 'different-ids',
			}

	def post_sync_success(self):
		self.settings.db_set({
			'next_filesync_ignore_id_conflicts': False,
		})

	def enable_conflict_resolution_for_next_sync(self):
		self.settings.db_set({
			'next_filesync_ignore_id_conflicts': False,
		})
