# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE


import frappe
from frappe.model.document import Document
from frappe import _

class PaymentGateway(Document):
	def validate_subscription_plan(self, currency, plan=None):
		settings = frappe.get_doc(self.gateway_settings, self.gateway_controller)

		if hasattr(settings, 'validate_subscription_plan'):
			settings.validate_subscription_plan(currency, plan)
		else:
			frappe.throw(_("Payment gateway {0} doesn't allow subscriptions").format(self.name))
