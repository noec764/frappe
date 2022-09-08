import frappe


def execute():
	for dt in frappe.get_all(
		"DocType", filters={"issingle": 0, "is_virtual": 0, "istable": 0}, pluck="name"
	):
		for dn in frappe.get_all(dt, filters={"_assign": "[]"}, pluck="name"):
			frappe.db.set_value(dt, dn, "_assign", None)
