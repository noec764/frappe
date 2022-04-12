# Copyright (c) 2021, Dokos SAS and Contributors
# License: MIT. See LICENSE

import frappe
from frappe import _

no_cache = 1


def get_context(context):
	context.show_sidebar = False if frappe.session.user == "Guest" else True
