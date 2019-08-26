# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from urllib.parse import urlencode
from frappe.utils import get_url, call_hook_method, cint, flt
from frappe.integrations.utils import create_request_log, create_payment_gateway, finalize_request
import stripe
import json
import erpnext

class StripeSettings(Document):
	supported_currencies = [
		"AED", "ALL", "ANG", "ARS", "AUD", "AWG", "BBD", "BDT", "BIF", "BMD", "BND",
		"BOB", "BRL", "BSD", "BWP", "BZD", "CAD", "CHF", "CLP", "CNY", "COP", "CRC", "CVE", "CZK", "DJF",
		"DKK", "DOP", "DZD", "EGP", "ETB", "EUR", "FJD", "FKP", "GBP", "GIP", "GMD", "GNF", "GTQ", "GYD",
		"HKD", "HNL", "HRK", "HTG", "HUF", "IDR", "ILS", "INR", "ISK", "JMD", "JPY", "KES", "KHR", "KMF",
		"KRW", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD", "MAD", "MDL", "MNT", "MOP", "MRO", "MUR", "MVR",
		"MWK", "MXN", "MYR", "NAD", "NGN", "NIO", "NOK", "NPR", "NZD", "PAB", "PEN", "PGK", "PHP", "PKR",
		"PLN", "PYG", "QAR", "RUB", "SAR", "SBD", "SCR", "SEK", "SGD", "SHP", "SLL", "SOS", "STD", "SVC",
		"SZL", "THB", "TOP", "TTD", "TWD", "TZS", "UAH", "UGX", "USD", "UYU", "UZS", "VND", "VUV", "WST",
		"XAF", "XOF", "XPF", "YER", "ZAR"
	]

	currency_wise_minimum_charge_amount = {
		'JPY': 50, 'MXN': 10, 'DKK': 2.50, 'HKD': 4.00, 'NOK': 3.00, 'SEK': 3.00,
		'USD': 0.50, 'AUD': 0.50, 'BRL': 0.50, 'CAD': 0.50, 'CHF': 0.50, 'EUR': 0.50,
		'GBP': 0.30, 'NZD': 0.50, 'SGD': 0.50
	}

	def __init__(self, *args, **kwargs):
		super(StripeSettings, self).__init__(*args, **kwargs)
		self.configure_stripe()

	def configure_stripe(self):
		self.stripe = stripe
		self.stripe.api_key = self.get_password(fieldname="secret_key", raise_exception=False)
		self.stripe.default_http_client = stripe.http_client.RequestsClient()

	def on_update(self):
		create_payment_gateway('Stripe-' + self.gateway_name, settings='Stripe Settings', controller=self.gateway_name)
		call_hook_method('payment_gateway_enabled', gateway='Stripe-' + self.gateway_name)
		if not self.flags.ignore_mandatory:
			self.validate_stripe_credentials()

	def validate_stripe_credentials(self):
		try:
			balance = self.stripe.Balance.retrieve()
			return balance
		except Exception as e:
			frappe.throw(_("Stripe connection could not be initialized.<br>Error: {0}").format(str(e)))

	def validate_transaction_currency(self, currency):
		if currency not in self.supported_currencies:
			frappe.throw(_("Please select another payment method. Stripe does not support transactions in currency '{0}'").format(currency))

	def validate_minimum_transaction_amount(self, currency, amount):
		if currency in self.currency_wise_minimum_charge_amount:
			if flt(amount) < self.currency_wise_minimum_charge_amount.get(currency, 0.0):
				frappe.throw(_("For currency {0}, the minimum transaction amount should be {1}").format(currency,
					self.currency_wise_minimum_charge_amount.get(currency, 0.0)))

	def validate_subscription_plan(self, currency, plan):
		try:
			stripe_plan = self.stripe.Plan.retrieve(plan)

			if not stripe_plan.active:
				frappe.throw(_("Payment plan {0} is no longer active.").format(plan))
			if not currency == stripe_plan.currency.upper():
				frappe.throw(_("Payment plan {0} is in currency {1}, not {2}.")\
					.format(plan, stripe_plan.currency.upper(), currency))
			return stripe_plan
		except frappe.ValidationError:
			return
		except Exception:
			frappe.log_error(frappe.get_traceback(), _("Stripe plan verification error"))
			frappe.throw(_("An error occured while trying to fetch your payment plan on Stripe.<br>Please check your error logs."))

	def get_payment_url(self, **kwargs):
		return get_url("./integrations/stripe_checkout?{0}".format(urlencode(kwargs)))

	def create_request(self, data):
		self.data = frappe._dict(data)

		try:
			self.integration_request = create_request_log(self.data, "Payment", "Stripe")
			self.reference_document = frappe.get_doc(self.data.reference_doctype, self.data.reference_docname)
			self.origin_transaction = frappe.get_doc(self.reference_document.reference_doctype,\
				self.reference_document.reference_name)

			subscription = False
			if hasattr(self.reference_document, 'is_linked_to_a_subscription'):
				subscription = self.reference_document.is_linked_to_a_subscription()

			return self.create_new_subscription() if subscription else self.create_new_charge()
			
		except Exception as e:
			self.change_integration_request_status("Failed", "error", str(e))
			return self.error_message(402, _("Stripe request creation failure"))

	def create_new_subscription(self):
		if hasattr(self.reference_document, 'get_subscription_plans_details'):
			self.payment_plans = self.reference_document.get_subscription_plans_details('Stripe-' + self.gateway_name)
			if self.payment_plans:
				self.create_customer_on_stripe()
				self.create_subscription_on_stripe()
		else:
			self.change_integration_request_status("Failed", "error",\
				_("Reference document doesn't have the 'get_subscription_plans_details' method to process subscriptions"))

		return finalize_request(self)

	def create_new_charge(self):
		self.create_charge_on_stripe()
		return finalize_request(self)

	def create_customer_on_stripe(self):
		try:
			if self.get_existing_customer():
				self.customer = self.get_existing_customer()
			else:
				self.customer = self.stripe.Customer.create(
					name=self.data.payer_name,
					email=self.data.payer_email,
					source=self.data.stripe_token_id
				)

				self.register_new_stripe_customer()

			return self.customer
		except Exception as e:
			self.change_integration_request_status("Failed", "error", str(e))
			return self.error_message(402, _("Stripe customer creation error"))

	def get_existing_customer(self):
		if self.origin_transaction.get("customer") and frappe.db.exists("Integration References",\
			dict(customer=self.origin_transaction.get("customer"))):
			return frappe.db.get_value("Integration References", dict(customer=self.origin_transaction.get("customer")), "stripe_customer_id")

	def register_new_stripe_customer(self):
		if self.origin_transaction.get("customer"):
			if frappe.db.exists("Integration References", dict(customer=self.origin_transaction.get("customer"))):
				doc = frappe.get_doc("Integration References", dict(customer=self.origin_transaction.get("customer")))
				doc.stripe_customer_id = self.customer_id
				doc.save(ignore_permissions=True)

			else:
				frappe.get_doc({
					"doctype": "Integration References",
					"customer": self.origin_transaction.get("customer"),
					"stripe_customer_id": self.customer.id,
					"stripe_settings": self.name
				}).insert(ignore_permissions=True)

	def create_subscription_on_stripe(self):
		try:
			self.subscription = self.stripe.Subscription.create(
				customer=self.customer,
				items=self.payment_plans
			)
			self.invoice_id = self.subscription.latest_invoice
			return self.process_subscription_output()
		except Exception as e:
			self.change_integration_request_status("Failed", "error", str(e))
			return self.error_message(402, _("Stripe subscription creation error"))

	def retrieve_subscription_latest_invoice(self):
		try:
			self.invoice = self.stripe.Invoice.retrieve(self.invoice_id)
			self.charge_id = self.invoice.charge
			return self.process_invoice_output()
		except Exception as e:
			self.change_integration_request_status("Failed", "error", str(e))
			return self.error_message(402, _("Stripe invoice retrieval error"))

	def create_charge_on_stripe(self):
		try:
			self.charge = self.stripe.Charge.create(
				amount=cint(flt(self.data.amount)*100),
				currency=self.data.currency,
				source=self.data.stripe_token_id,
				description=self.data.description,
				expand=[
					"balance_transaction"
				]
			)
			return self.process_charge_output()
		except Exception as e:
			self.change_integration_request_status("Failed", "error", str(e))
			return self.error_message(402, _("Stripe charge creation error"))

	def retrieve_charge_on_stripe(self):
		try:
			self.charge = self.stripe.Charge.retrieve(
				self.charge_id,
				expand=[
					"balance_transaction"
				]
			)
			return self.process_charge_output()
		except Exception as e:
			self.change_integration_request_status("Failed", "error", str(e))
			return self.error_message(402, _("Stripe charge creation error"))

	def add_stripe_base_amount_and_fee(self):
		if self.reference_document.currency\
			!= erpnext.get_company_currency(self.reference_document.get("company")):
			self.add_base_amount()
		return self.add_stripe_charge_fee()

	def add_base_amount(self):
		if self.charge.balance_transaction.get("currency").casefold()\
			== erpnext.get_company_currency(self.origin_transaction.get("company")).casefold():
			self.reference_document.db_set('base_amount', self.charge.balance_transaction.get("amount") / 100, update_modified=True)
			self.reference_document.db_set('exchange_rate', self.charge.balance_transaction.get("exchange_rate"), update_modified=True)

	def add_stripe_charge_fee(self):
		if not self.reference_document.get("fee_amount"):
			fee_amount = self.get_fee_amount(self.charge.balance_transaction)
			self.reference_document.db_set('fee_amount', fee_amount, update_modified=True)

		self.change_integration_request_status("Completed", "output", json.dumps(self.charge))

	def get_fee_amount(self, balance):
		return flt(balance["fee"]) / 100

	def process_charge_output(self):
		try:
			if self.charge.captured == True:
				return self.add_stripe_base_amount_and_fee()
			else:
				self.change_integration_request_status("Failed", "error", json.dumps(self.charge))
				return self.error_message(402, _("Stripe charge error"))
		except Exception as e:
			self.change_integration_request_status("Failed", "error", str(e))
			return self.error_message(402, _("Stripe charge processing error"))

	def process_subscription_output(self):
		try:
			if self.subscription.status == "active":
				return self.retrieve_subscription_latest_invoice()
			else:
				self.change_integration_request_status("Failed", "error", json.dumps(self.subscription))
				return self.error_message(402, _("Stripe subscription error"),\
					_('Subscription N°{0} is inactive.\
					<br>See integration request {1} for additional details.')\
					.format(subscription.id, self.integration_request.name)
				)

		except Exception:
			self.change_integration_request_status("Failed", "error", str(e))
			return self.error_message(402, _("Stripe subscription processing error"))

	def process_invoice_output(self):
		try:
			if self.invoice.status == "paid":
				return self.retrieve_charge_on_stripe()
			else:
				self.change_integration_request_status("Failed", "error", json.dumps(self.invoice))
				return self.error_message(402, _("Stripe invoice processing error"),\
					json.dumps(self.invoice)
				)

		except Exception:
			self.change_integration_request_status("Failed", "error", str(e))
			return self.error_message(402, _("Stripe invoice processing error"))

	def change_integration_request_status(self, status, type, error):
		self.flags.status_changed_to = status
		self.integration_request.db_set('status', status, update_modified=True)
		self.integration_request.db_set(type, error, update_modified=True)

	def error_message(self, error_number=500, title=None, error=None):
		if error is None:
			error = frappe.get_traceback()
		frappe.log_error(error, title)
		if error_number == 402:
			return {
					"redirect_to": frappe.redirect_to_message(_('Server Error'),\
						_("It seems that there is an issue with our Stripe integration.\
						<br>In case of failure, the amount will get refunded to your account.")),
					"status": 402,
					"error": error
				}
		else:
			return {
					"redirect_to": frappe.redirect_to_message(_('Server Error'),\
						_("It seems that there is an issue with our Stripe integration.\
						<br>In case of failure, the amount will get refunded to your account.")),
					"status": 500,
					"error": error
				}

def get_gateway_controller(doctype, docname):
	reference_doc = frappe.get_doc(doctype, docname)
	gateway_controller = frappe.db.get_value("Payment Gateway", reference_doc.payment_gateway, "gateway_controller")
	return gateway_controller
