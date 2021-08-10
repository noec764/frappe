import frappe

from frappe.translate import get_dict, send_translations

@frappe.whitelist()
def get_slide_view(route):
	# if frappe.db.exists('Slide View', route):
	# 	return frappe.get_doc('Slide View', route)
	if frappe.db.exists('Slide View', {'route': route}):
		return frappe.get_doc('Slide View', {'route': route})

@frappe.whitelist()
def get_translations(doctype=None):
	m = get_dict("doctype", 'Slide View')
	if doctype:
		m.update(get_dict("doctype", doctype))
	send_translations(m)
