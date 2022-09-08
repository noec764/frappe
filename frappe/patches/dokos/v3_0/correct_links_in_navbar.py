import frappe


def execute():
	for route in ("#background_jobs", "#user-profile"):
		if field := frappe.db.get_value("Navbar Item", dict(route=route)):
			frappe.db.set_value("Navbar Item", field, "route", route.replace("#", "/app/"))
