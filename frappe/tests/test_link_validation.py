import frappe
from frappe.tests.utils import FrappeTestCase


class TestBaseDocument(FrappeTestCase):
	def test_link_validation(self):
		meta = frappe.get_meta("ToDo")
		if (
			not meta.has_field("reference_type")
			or not meta.has_field("reference_name")
			or not meta.has_field("assigned_by")
		):
			return

		user = frappe.get_all("User", limit=1)[0].name

		todo1 = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Test",
				"assigned_by": user,
			}
		)
		todo1.insert()

		todo2 = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Test",
				"assigned_by": "THIS USER DOES NOT EXIST",
			}
		)
		self.assertRaises(frappe.LinkValidationError, todo2.insert)

		todo3 = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Test",
				"reference_type": "User",
				"reference_name": user,
			}
		)
		todo3.insert()

		todo4 = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Test",
				"reference_type": "User",
				"reference_name": "THIS USER DOES NOT EXIST",
			}
		)
		self.assertRaises(frappe.LinkValidationError, todo4.insert)

		todo5 = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Test",
				"reference_type": "User",
				"reference_name": 1234,
			}
		)
		self.assertRaises(frappe.LinkValidationError, todo5.insert)

		todo6 = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Test",
				"reference_type": "User",
				"reference_name": {"name": user},  # Still not a valid link
			}
		)
		self.assertRaises(frappe.LinkValidationError, todo6.insert)

		frappe.db.rollback()
