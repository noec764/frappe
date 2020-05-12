# -*- coding: utf-8 -*-
# Copyright (c) 2019, Dokos and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.model.document import Document
from frappe.utils import now, get_datetime
from frappe.utils.data import DATE_FORMAT, TIME_FORMAT, DATETIME_FORMAT
from six import string_types
import datetime
import hashlib
import uuid
import os
from frappe.modules import load_doctype_module

def get_seal_doc_and_version(doc):
	try:
		data = []
		version = None

		module = load_doctype_module(doc.doctype, suffix='_version')
		if hasattr(module, 'get_data'):
				data = module.get_data()
				version = module.DOCTYPE_VERSION

	except (ImportError, AttributeError):
		"""
			If the versionning has not been configured, no seal will be recorded.
		"""
		return None

	return get_sealed_doc(doc, data, version)

def get_sealed_doc(doc, modules, version, sanitize=False):
	current_mapping = [d for d in modules if d["version"] == version]
	meta_fields = frappe.get_meta(doc.doctype).fields

	if current_mapping:
		current_mapping = current_mapping[0]

		timestamp = None
		if isinstance(doc._submitted, datetime.date):
			timestamp = datetime.datetime.strftime(doc._submitted, DATETIME_FORMAT)
		elif doc._submitted:
			timestamp = datetime.datetime.strftime(get_datetime(doc._submitted), DATETIME_FORMAT)

		sealed_doc = {
			"version": version,
			"doctype": doc.doctype,
			"docname": doc.name,
			"timestamp": timestamp
		}

		sanitize = True if "sanitize" in current_mapping else False

		for k, v in doc.as_dict().items():
			if k in current_mapping["fields"]:
				if k in current_mapping["tables"].keys():
					child_table = []
					for i in doc.as_dict()[k]:
						table_item = {}
						for j in i:
							if j in current_mapping["tables"][k]:
								table_item[j] = sanitize_value(i[j], [m for m in meta_fields if m.fieldname == j]) if sanitize else i[j]

						child_table.append(table_item)

					sealed_doc[k] = child_table

				else:
					sealed_doc[k] = sanitize_value(doc.as_dict()[k], [m for m in meta_fields if m.fieldname == k]) if sanitize else doc.as_dict()[k]

		return sealed_doc
	else:
		return None

def sanitize_value(value, meta):
	if not meta or not value:
		return value

	if meta and isinstance(meta, list):
		meta = meta[0]

	if meta.fieldtype == "Datetime" and not isinstance(value, string_types):
		value = value.strftime(DATETIME_FORMAT)

	elif meta.fieldtype == "Date" and not isinstance(value, string_types):
		value = value.strftime(DATE_FORMAT)

	elif meta.fieldtype == "Time" and not isinstance(value, string_types):
		if isinstance(value, datetime.timedelta):
			value = (datetime.datetime.min + value).time()

		value = value.strftime(TIME_FORMAT)

	return value

def get_chained_seal(doc):
	if not isinstance(doc, dict):
		doc = doc.as_dict()

	previous_seal = dict()
	if doc.get("timestamp"):
		previous_entry = frappe.db.sql("""
			SELECT name, _seal, _submitted
			FROM `tab%s`
			WHERE _submitted < '%s' AND _seal IS NOT NULL
			ORDER BY _submitted DESC LIMIT 1""" % (doc["doctype"],\
			doc.get("timestamp")), as_dict=True)

		if previous_entry:
			previous_seal = previous_entry[0]

	if not previous_seal:
		if frappe.db.get_global("initial_hash"):
			previous_seal['_seal'] = frappe.db.get_global("initial_hash")
		else:
			previous_seal['_seal'] = hash_line(uuid.uuid4().hex)
			frappe.db.set_global("initial_hash", previous_seal['_seal'])
			frappe.db.commit()

	current_seal = hash_line(doc)

	return hash_chain(previous_seal['_seal'], current_seal)

def hash_line(data):
	sha = hashlib.sha256()
	sha.update(
		frappe.safe_encode(str(data))
	)
	return sha.hexdigest()

def hash_chain(prev, current):
	sha = hashlib.sha256()
	sha.update(
		frappe.safe_encode(str(prev)) + \
		frappe.safe_encode(str(current))
	)
	return sha.hexdigest()
