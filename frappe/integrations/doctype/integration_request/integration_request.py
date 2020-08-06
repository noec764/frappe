# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json

class IntegrationRequest(Document):
	def autoname(self):
		if self.flags._name:
			self.name = self.flags._name

	def update_status(self, params, status):
		data = frappe.parse_json(self.data)
		data.update(params)

		self.data = json.dumps(data, indent=4)
		self.status = status
		self.save(ignore_permissions=True)
		frappe.db.commit()

	@frappe.whitelist()
	def retry_webhook(self):
		handlers = frappe.get_hooks("webhooks_handler")
		method = handlers.get(self.integration_request_service, [])
		if method:
			frappe.get_attr(method[0])(**{"doctype": "Integration Request", "docname": self.name})

		return {"status": "executed"}

def retry_failed_webhooks(service=None):
	filters = {
		"status": ["in", ["Failed", "Queued"]],
		"integration_type": "Webhook"
	}

	if service:
		filters["integration_request_service"] = service

	failed_webhooks = frappe.get_all("Integration Request", filters=filters)

	for webhook in failed_webhooks:
		w = frappe.get_doc("Integration Request", webhook.name)
		w.retry_webhook()
