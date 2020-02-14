import frappe

def execute():
	for dt in ["Dashboard Chart", "Dashboard Card"]:
		docs = frappe.get_all(dt, filters={"timespan": "No Timespan"})

		for doc in docs:
			frappe.db.set_value(dt, doc.name, "timespan", "All Time")
