import frappe

def execute():
	doctypes = frappe.get_all("DocType", filters={"istable": 0, "issingle": 0, "is_submittable": 1})

	for doctype in doctypes:
		frappe.reload_doctype(doctype.name, force=True)