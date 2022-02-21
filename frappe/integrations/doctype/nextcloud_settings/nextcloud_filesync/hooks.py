import frappe

from contextlib import contextmanager

from frappe.integrations.doctype.nextcloud_settings.nextcloud_filesync.sync import NextcloudFileSync

@contextmanager
def _sync_module():
	# frappe.db.begin()  # begin transaction
	# frappe.db.commit()  # begin transaction
	try:
		if frappe.flags.cached_nextcloud_sync_client:
			yield frappe.flags.cached_nextcloud_sync_client
		else:
			sync = NextcloudFileSync()
			frappe.flags.cached_nextcloud_sync_client = sync
			yield sync

		# if len(frappe.message_log) > 0:
		# 	frappe.msgprint(None, json.dumps(sync._timing, indent=2))
		frappe.db.commit()
	except:
		frappe.db.rollback()  # rollback on error
		raise

@frappe.whitelist()
def check_id_of_home():
	with _sync_module() as syncer:
		return syncer.check_id_of_home()

@frappe.whitelist()
def clear_id_of_home():
	with _sync_module() as syncer:
		return syncer.check_id_of_home()

@frappe.whitelist()
def sync_from_remote_all():
	with _sync_module() as syncer:
		syncer.sync_from_remote_all()

@frappe.whitelist()
def sync_from_remote_since_last_update():
	with _sync_module() as syncer:
		syncer.sync_from_remote_since_last_update()

# @frappe.whitelist()
# def enable_conflict_resolution_for_next_sync():
# 	frappe.get_single("Nextcloud Settings")\
# 		.db_set('next_filesync_ignore_id_conflicts', True)


# @frappe.whitelist()
# def save_file_doc_to_remote(doc, event=None):
# 	with _sync_module() as sync:
# 		sync.save_to_remote(doc, event)


# @frappe.whitelist()
# def file_on_trash(doc, event):
# 	# event == 'on_trash'
# 	with _sync_module() as sync:
# 		sync.file_on_trash(doc)


# @frappe.whitelist()
# def file_on_update(doc, event):
# 	with _sync_module() as sync:
# 		sync.file_on_update(doc)


# @frappe.whitelist()
# def sync_to_remote():
# 	with _sync_module() as sync:
# 		sync.sync_to_remote()
