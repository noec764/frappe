import frappe
from frappe.integrations.doctype.nextcloud_settings import get_nextcloud_settings

from .sync import sync_log, sync_module
from .diff_engine.utils import check_flag, get_home_folder

def can_run_hook(doc=None):
	if frappe.flags.nextcloud_disable_filesync_hooks: return False
	if frappe.flags.nextcloud_disable_filesync: return False
	if doc and check_flag(doc): return False
	return True

@frappe.whitelist()
def check_id_of_home():
	with sync_module() as syncer:
		if not syncer: return 'skip'
		return syncer.check_id_of_home()

@frappe.whitelist()
def clear_id_of_home():
	get_home_folder().db_set('nextcloud_id', None)

@frappe.whitelist()
def sync_from_remote_all():
	with sync_module() as syncer:
		if not syncer: return 'skip'
		syncer.sync_from_remote_all()

@frappe.whitelist()
def sync_from_remote_since_last_update():
	with sync_module() as syncer:
		if not syncer: return 'skip'
		syncer.sync_from_remote_since_last_update()

@frappe.whitelist()
def sync_from_remote_all__force():
	sync_log('Force sync: un-syncing all local Files')
	res = True
	while res:
		res = frappe.get_all(
			'File',
			fields=['name'],
			filters = [['nextcloud_id', '!=', '']],
			limit_page_length=100)

		for f in res:
			docname = f['name']
			frappe.db.set_value('File', docname, 'nextcloud_id', None)

		if len(res) < 100:
			break

	settings = frappe.get_single("Nextcloud Settings")
	# settings.set('next_filesync_ignore_id_conflicts', True)
	settings.set('filesync_override_conflict_strategy', 'UNSAFE-disable-conflict-detection')
	settings.save()

	with sync_module() as syncer:
		if not syncer: return 'skip'
		syncer.sync_from_remote_all()

# @frappe.whitelist()
# def enable_conflict_resolution_for_next_sync():
# 	frappe.get_single("Nextcloud Settings")\
# 		.db_set('next_filesync_ignore_id_conflicts', True)


# @frappe.whitelist()
# def save_file_doc_to_remote(doc, event=None):
# 	with sync_module() as sync:
# 		sync.save_to_remote(doc, event)


@frappe.whitelist()
def file_on_trash(doc, event):
	if not can_run_hook(doc): return
	if doc.flags.in_parent_delete:
		# sync_log('File on_trash Nextcloud hook: skipping, parent is already being deleted on remote')
		return

	try:
		sync_log(f'file_on_trash({doc}, {event})')
		with sync_module(rollback_on_exception=False) as syncer:
			if syncer:
				syncer.file_on_trash(doc)
	except Exception as e:
		sync_log(e)
		return

@frappe.whitelist()
def file_on_update(doc, event):
	if not can_run_hook(doc): return
	if doc.get('nextcloud_id', None) is None: return

	## <TODO> move all this code inside of Syncer or ActionRunner…
	if frappe.flags.nextcloud_in_rename:
		# ignore: children are all "needlessly" updated
		# because of the parent's name being updated
		if doc._doc_before_save:
			modified = doc._doc_before_save.modified

			with sync_module(rollback_on_exception=False) as syncer:
				if syncer:
					entry = syncer.common.get_remote_entry_by_id(doc.nextcloud_id)
					if entry:
						modified = entry.last_updated

			doc.db_set('modified', modified, update_modified=False)
			sync_log(f'corrected time of {doc}: ', modified)
			frappe.db.commit()
		return
	## </TODO>

	try:
		sync_log(f'file_on_update({doc}, {event})')
		with sync_module(rollback_on_exception=False) as syncer:
			if syncer:
				syncer.file_on_update(doc)
	except Exception as e:
		sync_log(e)
		return

@frappe.whitelist()
def file_on_create(doc, event):
	if not can_run_hook(doc): return
	try:
		sync_log(f'file_on_create({doc}, {event})')
		with sync_module(rollback_on_exception=False) as syncer:
			if syncer:
				syncer.file_on_create(doc)
	except Exception as e:
		sync_log(e)
		return


@frappe.whitelist()
def check_server():
	try:
		settings = get_nextcloud_settings()
		settings.nc_connect()
		# no exception raised
		return {'status': 'ok'}
	except Exception as e:
		frappe.clear_last_message()
		msg = '\n'.join(map(str, e.args))
		return {'status': 'error', 'error': msg}
