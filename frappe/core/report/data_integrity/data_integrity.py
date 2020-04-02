# Copyright (c) 2019, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import hashlib
from frappe import _, scrub
from frappe.utils import format_datetime, get_datetime, now_datetime
from frappe.utils.seal import get_sealed_doc, get_chained_seal
from frappe.modules import load_doctype_module
import json

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)

	return columns, data

def get_data(filters=None):
	if filters is None:
		return []

	documents = frappe.get_all(filters.get("doctype"), filters={"docstatus": [">", 0]})
	modules = get_versions_data(filters.get("doctype"))
	doc_meta = frappe.get_meta(filters.get("doctype"))

	if not modules:
		frappe.throw(_("The versioning document for this doctype could not be found"))

	result = []
	for document in documents:
		doc = frappe.get_doc(filters.get("doctype"), document.name)

		if doc._seal is None:
			comment = _("This document is not sealed")
			result.append([doc.name, format_datetime(doc.creation), doc.owner,\
				"Out", comment, "", "", "", ""])
			continue

		sealed_doc = get_sealed_doc(doc, modules, doc._seal_version, True)

		# Check for renamed links
		link_fields = get_link_fields(sealed_doc, doc_meta)
		sealed_doc = revise_renamed_links(sealed_doc, link_fields)

		if sealed_doc:
			seal = get_chained_seal(sealed_doc)
			integrity = "Yes" if seal == doc._seal else "No"
			comment = _("Data integrity verified") if integrity == "Yes" else _("Data integrity could not be verified")

			result.append([doc.name, format_datetime(doc.creation), doc.owner,\
				integrity, comment, seal, doc._seal, doc._seal_version])

	return result

def get_link_fields(doc, meta):
	links = []
	for field in doc:
		links.extend([f for f in meta.fields if f.fieldname == field and f.fieldtype == "Link"])

	return links

def revise_renamed_links(doc, fields):
	for field in fields:
		docname = doc[field.fieldname]
		versions = frappe.get_all("Renamed Document",\
			filters={
				"document_type": field.options,\
				"new_name": docname
			},
			fields=["old_name", "new_name"])

		if docname in [x.get("new_name") for x in versions]:
			doc[field.fieldname] = [x.get("new_name") for x in versions if x.get("new_name") == docname]

	return doc


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
			"width": 50
		},
		{
			"label": _("Comments"),
			"fieldname": "comments",
			"fieldtype": "Data",
			"width": 280
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

	sealed_doctypes = [d[0] for d in frappe.db.get_values("DocType", {"is_sealed": 1}) if get_versions_data(d[0])]

	out = []
	for dt in can_read:
		if txt.lower().replace("%", "") in dt.lower() and dt in sealed_doctypes:
			out.append([dt])

	return out