# Copyright (c) 2019, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import hashlib
from frappe import _, scrub
from frappe.utils import format_datetime
from frappe.utils.seal import get_sealed_doc, get_chained_seal
from frappe.modules import load_doctype_module

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)

	return columns, data

def get_data(filters=None):
	if filters is None:
		return []

	documents = frappe.get_all(filters.get("doctype"))
	modules = get_versions_data(filters.get("doctype"))

	if not modules:
		frappe.throw(_("The versioning document for this doctype could not be found"))

	result = []
	for document in documents:
		doc = frappe.get_doc(filters.get("doctype"), document.name)

		if doc._seal is None:
			continue

		sealed_doc = get_sealed_doc(doc, modules, doc._seal_version, True)
		if sealed_doc:
			seal = get_chained_seal(sealed_doc, True)
			integrity = True if seal == doc._seal else False

			result.append([doc.name, format_datetime(doc.creation), doc.owner, integrity, seal, doc._seal, doc._seal_version])

	return result

def get_versions_data(doctype):
	try:
		data = []

		module = load_doctype_module(doctype, suffix='_version')
		if hasattr(module, 'get_data'):
				data = module.get_data()

	except ImportError:
		return []

	return data


def get_columns(filters=None):
	columns = [
		{
			"label": _("Document Name"),
			"fieldname": "document_name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Creation Date"),
			"fieldname": "creation_date",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Owner"),
			"fieldname": "owner",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Integrity"),
			"fieldname": "integrity",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Calculated Seal"),
			"fieldname": "calculated_seal",
			"fieldtype": "Data",
			"width": 220
		},
		{
			"label": _("Registered Seal"),
			"fieldname": "registered_seal",
			"fieldtype": "Data",
			"width": 220
		},
		{
			"label": _("Seal Version"),
			"fieldname": "version",
			"fieldtype": "Data",
			"width": 100
		}
	]
	return columns

def query_doctypes(doctype, txt, searchfield, start, page_len, filters):
	user = frappe.session.user
	user_perms = frappe.utils.user.UserPermissions(user)
	user_perms.build_permissions()
	can_read = user_perms.can_read

	sealed_doctypes = [d[0] for d in frappe.db.get_values("DocType", {"is_sealed": 1})]

	out = []
	for dt in can_read:
		if txt.lower().replace("%", "") in dt.lower() and dt in sealed_doctypes:
			out.append([dt])

	return out