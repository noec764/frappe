import frappe

def execute():
	for shortcut in frappe.get_all("Desk Shortcut", filters={"color": "Grey"}):
		frappe.db.set_value("Desk Shortcut", shortcut.name, "color", "Gray")