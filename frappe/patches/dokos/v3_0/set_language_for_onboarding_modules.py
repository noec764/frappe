import frappe


def execute():
	for module in frappe.get_all("Module Onboarding", filters={"language": ("is", "not set")}):
		frappe.db.set_value("Module Onboarding", module.name, "language", "en")
