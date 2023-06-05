import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("core", "doctype", "system_settings")

	if frappe.db.get_system_setting("template_for_welcome_email"):
		rename_field("System Settings", "template_for_welcome_email", "welcome_email_template")
