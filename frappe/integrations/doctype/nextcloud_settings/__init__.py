import frappe
from frappe.integrations.doctype.nextcloud_settings.nextcloud_settings import NextcloudSettings

def get_nextcloud_settings() -> NextcloudSettings:
	return frappe.get_single('Nextcloud Settings')

def get_nextcloud_settings_and_client(**kwargs):
	settings = get_nextcloud_settings()
	return settings.nc_connect(**kwargs), settings

def get_nextcloud_client(**kwargs):
	return get_nextcloud_settings().nc_connect(**kwargs)
