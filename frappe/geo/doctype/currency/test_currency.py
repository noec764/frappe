# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: See license.txt

# pre loaded


import frappe
from frappe.tests.utils import FrappeTestCase


class TestUser(FrappeTestCase):
	def test_default_currency_on_setup(self):
		usd = frappe.get_doc("Currency", "USD")
		self.assertDocumentEqual({"enabled": 1, "fraction": "Cent"}, usd)
