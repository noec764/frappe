import frappe

def execute():
	name = frappe.get_value("Web Form", dict(name="event", is_standard=1))

	if name:
		frappe.delete_doc("Web Form", name)
