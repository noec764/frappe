# Copyright (c) 2022, Dokos SAS and contributors
# For license information, please see license.txt


import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doctype("Workspace")
	rename_field("Workspace", "hidden", "is_hidden")
