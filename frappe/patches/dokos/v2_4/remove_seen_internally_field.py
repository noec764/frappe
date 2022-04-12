import frappe


def execute():
	if not frappe.get_meta("Communication").has_field("seen_internally"):
		return

	for communication in frappe.get_all("Communication", filters={"seen_internally": 1}):
		frappe.db.set_value("Communication", communication.name, "seen", 1)
