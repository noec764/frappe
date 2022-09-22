import frappe


def execute():
	frappe.flags.in_install = True
	frappe.reload_doc("core", "doctype", "doctype_state", force=True)
	frappe.reload_doc("core", "doctype", "doctype", force=True)
	frappe.reload_doc("core", "doctype", "docfield", force=True)
	frappe.flags.in_install = False
