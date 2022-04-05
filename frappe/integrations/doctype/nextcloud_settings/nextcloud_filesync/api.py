import frappe
from frappe.integrations.doctype.nextcloud_settings import get_nextcloud_settings

from .sync import sync_log, sync_module, optional_sync_module
from .diff_engine.utils import check_flag, get_home_folder, doc_has_nextcloud_id


@frappe.whitelist()
def check_id_of_home():
	with optional_sync_module() as syncer:
		if not syncer: return 'skip'
		return syncer.check_id_of_home()


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


@frappe.whitelist()
def sync_from_remote_all():
	with optional_sync_module() as syncer:
		if not syncer: return 'skip'
		syncer.sync_from_remote_all()


@frappe.whitelist()
def sync_from_remote_since_last_update():
	with optional_sync_module() as syncer:
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

	with optional_sync_module() as syncer:
		if not syncer: return 'skip'
		syncer.sync_from_remote_all()


## HOOKS
def can_run_hook(doc=None):
	if frappe.flags.nextcloud_disable_filesync_hooks:
		sync_log('↳ skipping hook: all nc hooks disabled')
		return False
	if frappe.flags.nextcloud_disable_filesync:
		sync_log('↳ skipping hook: file sync disabled')
		return False
	if doc and check_flag(doc):
		sync_log('↳ skipping hook: flag is set on file', doc)
		return False
	return True


@frappe.whitelist()
def file_on_trash(doc, event):
	sync_log(f'file_on_trash({doc}, {event}, nc_id={doc.nextcloud_id})')
	if not can_run_hook(doc): return
	if not doc_has_nextcloud_id(doc): return  # not linked to remote
	if doc.flags.in_parent_delete:
		# sync_log('File on_trash Nextcloud hook: skipping, parent is already being deleted on remote')
		return

	try:
		with sync_module(rollback_on_exception=False) as syncer:
			syncer.file_on_trash(doc)

	except Exception as e:
		sync_log(e)
		return

@frappe.whitelist()
def file_on_update(doc, event):
	sync_log(f'file_on_update({doc}, {event})')
	if not can_run_hook(doc): return

	## <TODO> move all this code inside of Syncer or ActionRunner…
	if frappe.flags.nextcloud_in_rename:
		# ignore: children are all "needlessly" updated
		# because of the parent's name being updated
		prev_doc = doc.get_doc_before_save()
		if prev_doc:
			modified = prev_doc.modified

			with sync_module(rollback_on_exception=False) as syncer:
				entry = syncer.common.get_remote_entry_by_id(doc.nextcloud_id)
				if entry:
					modified = entry.last_updated

			doc.db_set('modified', modified, update_modified=False)
			sync_log(f'corrected time of {doc}: ', modified)
			frappe.db.commit()
		return
	## </TODO>

	try:
		with sync_module(rollback_on_exception=False) as syncer:
			syncer.file_on_update(doc)
	except Exception as e:
		sync_log(e)
		return

@frappe.whitelist()
def file_on_create(doc, event):
	sync_log(f'file_on_create({doc}, {event})')
	if not can_run_hook(doc): return

	# if doc_has_nextcloud_id(doc):
	# 	return  # How did this file get a nextcloud_id?

	try:
		with sync_module(rollback_on_exception=False) as syncer:
			syncer.file_on_create(doc)
	except Exception as e:
		sync_log(e)
		return
