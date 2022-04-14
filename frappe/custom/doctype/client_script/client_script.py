# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class ClientScript(Document):
	def on_update(self):
		frappe.clear_cache(doctype=self.dt)

	def on_trash(self):
		frappe.clear_cache(doctype=self.dt)
