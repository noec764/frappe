# Copyright (c) 2021, Frappe Technologies and contributors
# License: MIT. See LICENSE
import datetime
import json
from urllib.parse import parse_qs, urlencode

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_request_session


def make_request(method, url, auth=None, headers=None, data=None):
	auth = auth or ""
	data = data or {}
	headers = headers or {}

	try:
		s = get_request_session()
		frappe.flags.integration_request = s.request(method, url, data=data, auth=auth, headers=headers)
		frappe.flags.integration_request.raise_for_status()

		if frappe.flags.integration_request.headers.get("content-type") == "text/plain; charset=utf-8":
			return parse_qs(frappe.flags.integration_request.text)

		return frappe.flags.integration_request.json()
	except Exception as exc:
		frappe.log_error()
		raise exc


def make_get_request(url, **kwargs):
	return make_request("GET", url, **kwargs)


def make_post_request(url, **kwargs):
	return make_request("POST", url, **kwargs)


def make_put_request(url, **kwargs):
	return make_request("PUT", url, **kwargs)


def create_request_log(
	data,
	integration_type=None,
	service_name=None,
	name=None,
	error=None,
	request_headers=None,
	output=None,
	**kwargs,
):
	"""
	DEPRECATED: The parameter integration_type will be removed in the next major release.
	Use is_remote_request instead.
	"""
	if integration_type == "Remote":
		kwargs["is_remote_request"] = 1

	else:
		kwargs["request_description"] = integration_type

	reference_doctype = reference_docname = None
	if "reference_doctype" not in kwargs:
		if isinstance(data, str):
			data = json.loads(data)

		reference_doctype = data.get("reference_doctype")
		reference_docname = data.get("reference_docname")

	integration_request = frappe.get_doc(
		{
			"doctype": "Integration Request",
			"integration_request_service": service_name,
			"request_headers": get_json(request_headers),
			"data": get_json(data),
			"output": get_json(output),
			"error": get_json(error),
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
			**kwargs,
		}
	)

	if name:
		integration_request.flags._name = name

	integration_request.insert(ignore_permissions=True)
	frappe.db.commit()

	return integration_request


def get_json(obj):
	return obj if isinstance(obj, str) else frappe.as_json(obj, indent=2)


def json_handler(obj):
	if isinstance(obj, (datetime.date, datetime.timedelta, datetime.datetime)):
		return str(obj)


def get_gateway_controller(doctype, docname):
	reference_doc = frappe.get_doc(doctype, docname)
	gateway_controller = frappe.db.get_value(
		"Payment Gateway", reference_doc.payment_gateway, "gateway_controller"
	)
	return gateway_controller


class PaymentGatewayController(Document):
	def finalize_request(self, reference_no=None):
		redirect_to = self.data.get("redirect_to")
		redirect_message = self.data.get("redirect_message")

		if (
			self.flags.status_changed_to in ["Completed", "Autorized", "Pending"]
			and self.reference_document
		):
			custom_redirect_to = None
			try:
				custom_redirect_to = self.reference_document.run_method(
					"on_payment_authorized", self.flags.status_changed_to, reference_no
				)
			except Exception:
				frappe.log_error(frappe.get_traceback(), _("Payment custom redirect error"))

			if custom_redirect_to and custom_redirect_to != "no-redirection":
				redirect_to = custom_redirect_to

			redirect_url = self.redirect_url if self.get("redirect_url") else "/payment-success"

		else:
			redirect_url = "/payment-failed"

		if redirect_to and redirect_to != "no-redirection":
			redirect_url += "?" + urlencode({"redirect_to": redirect_to})
		if redirect_message:
			redirect_url += "&" + urlencode({"redirect_message": redirect_message})

		return {"redirect_to": redirect_url, "status": self.integration_request.status}

	def change_integration_request_status(self, status, error_type, error):
		if hasattr(self, "integration_request"):
			self.flags.status_changed_to = status
			self.integration_request.db_set("status", status, update_modified=True)
			self.integration_request.db_set(error_type, error, update_modified=True)

		if hasattr(self, "update_reference_document_status"):
			self.update_reference_document_status(status)
