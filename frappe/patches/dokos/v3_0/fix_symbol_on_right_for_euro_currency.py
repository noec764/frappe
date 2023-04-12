import frappe


def execute():
	"""Set symbol_on_right=1 for currency EUR"""

	frappe.db.set_value("Currency", "EUR", "symbol_on_right", 1)
