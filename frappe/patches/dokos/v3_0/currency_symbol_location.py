import frappe


def execute():
	frappe.db.set_value("Currency", "EUR", "symbol_on_right", 1)
