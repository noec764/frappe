# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE


import frappe
import frappe.www.list
from frappe import _

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)

	active_tokens = frappe.get_all(
		"OAuth Bearer Token",
		filters=[["user", "=", frappe.session.user]],
		fields=["client"],
		distinct=True,
		order_by="creation",
	)
	context.third_party_apps = True if active_tokens else False

	context.current_user = frappe.get_doc("User", frappe.session.user)
	context.show_sidebar = True
