import frappe
from frappe.translate import get_dict, send_translations


@frappe.whitelist()
def get_slide_view_by_route(route):
	# if frappe.db.exists('Slide View', route):
	# 	return frappe.get_doc('Slide View', route)
	if frappe.db.exists("Slide View", {"route": route}):
		return frappe.get_doc("Slide View", {"route": route})
