import frappe

from ..role import desk_properties


def execute():
	frappe.reload_doctype("User")
	frappe.reload_doctype("Role")
	frappe.reload_doctype("User Email")
	for role in frappe.get_all("Role", ["name", "desk_access"]):
		if not role.desk_access:
			continue

		if role.name in ["All", "Guest", "Employee Self Service"]:
			continue

		role_doc = frappe.get_doc("Role", role.name)
		is_bad = all(role_doc.get(key) == 0 for key in desk_properties)

		if not is_bad:
			continue

		print(f"Fixing desk role {role_doc.name!r}")
		for key in desk_properties:
			role_doc.set(key, role_doc.desk_access)
		role_doc.save()
