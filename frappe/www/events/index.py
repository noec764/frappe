# Copyright (c) 2020, Dokos SAS and Contributors
# See license.txt

import frappe
from frappe import _

no_cache = 1

def get_context(context):
	if frappe.session.user == "Guest" or not frappe.has_permission("Event"):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	context.show_sidebar=True