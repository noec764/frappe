import frappe

from .sync import sync_log, sync_module
from .diff_engine.utils import check_flag

@frappe.whitelist()
def check_id_of_home():
	with sync_module() as syncer:
		if not syncer: return 'skip'
		return syncer.check_id_of_home()

@frappe.whitelist()
def clear_id_of_home():
	with sync_module() as syncer:
		if not syncer: return 'skip'
		return syncer.check_id_of_home()

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
	# sync_log(f'file_on_trash({doc}, {event})')
	if check_flag(doc): return
	with sync_module() as syncer:
		if syncer:
			syncer.file_on_trash(doc)


@frappe.whitelist()
def file_on_update(doc, event):
	# sync_log(f'file_on_update({doc}, {event})')
	if check_flag(doc): return
	if doc.get('nextcloud_id', None) is None: return
	with sync_module() as syncer:
		if syncer:
			syncer.file_on_update(doc)


@frappe.whitelist()
def file_on_create(doc, event):
	# sync_log(f'file_on_create({doc}, {event})')
	if check_flag(doc): return
	with sync_module() as syncer:
		if syncer:
			syncer.file_on_create(doc)
