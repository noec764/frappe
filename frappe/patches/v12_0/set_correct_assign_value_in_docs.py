import frappe
from frappe.query_builder.functions import GroupConcat, Coalesce

def execute():
	frappe.reload_doc("desk", "doctype", "todo")

	ToDo = frappe.qb.Table("ToDo")
	assignees = GroupConcat("owner").distinct().as_("assignees")

	query = (
		frappe.qb.from_(ToDo)
		.select(ToDo.name, ToDo.reference_type, assignees)
		.where(Coalesce(ToDo.reference_type, "") != "")
		.where(Coalesce(ToDo.reference_name, "") != "")
		.where(ToDo.status != "Cancelled")
		.groupby(ToDo.reference_type, ToDo.reference_name)
	)

	assignments = frappe.db.sql(query, as_dict=True)

	for doc in assignments:
		users = doc.assignees.split(",")
		frappe.db.set_value(
			doc.reference_type,
			doc.reference_name,
			"_assign",
			frappe.as_json(users),
			update_modified=False
		)