import frappe

def execute():
	for communication in frappe.get_all("Communication", filters={"seen_internally": 1}):
		frappe.db.set_value("Communication", communication.name, "seen", 1)
