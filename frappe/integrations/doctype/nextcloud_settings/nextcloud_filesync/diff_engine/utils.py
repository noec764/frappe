import frappe
from typing import Optional
from functools import lru_cache

def maybe_int(v: Optional[str]) -> Optional[int]:
	if isinstance(v, str) and v != '':
		return int(v)
	if isinstance(v, int):
		return v
	return None

# Environment variables:
# NEXTCLOUD_DONT_VERIFY_CERTS
# NEXTCLOUD_FORCE_VERIFY_CERTS
# NEXTCLOUD_ALLOW_TESTS
# NEXTCLOUD_SKIP_TESTS

FLAG_NEXTCLOUD_DISABLE_HOOKS = 'nextcloud_disable_filesync_hooks'
FLAG_NEXTCLOUD_IGNORE = 'nextcloud_triggered_update'


def set_flag(doc):
	doc.flags.nextcloud_triggered_update = True


def check_flag(doc):
	return doc.flags.nextcloud_triggered_update


def get_home_folder():
	return frappe.get_doc("File", {"is_home_folder": 1})


@lru_cache(maxsize=None)
def get_home_folder_name() -> str:
	docname = frappe.db.get_value("File", {"is_home_folder": 1})
	if not docname:
		raise frappe.exceptions.DoesNotExistError('missing home folder')
	return docname
