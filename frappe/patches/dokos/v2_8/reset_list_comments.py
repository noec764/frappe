import frappe

from frappe.core.doctype.comment.comment import update_comment_in_doc

def execute():
	for comm in frappe.get_all("Comment"):
		doc = frappe.get_doc("Comment", comm.name)
		update_comment_in_doc(doc)


	communications = frappe.get_all("Communication", filters={"reference_doctype": ("is", "set"), "seen": 1})
	for comm in communications:
		doc = frappe.get_doc("Communication", comm.name)
		update_comment_in_doc(doc)
