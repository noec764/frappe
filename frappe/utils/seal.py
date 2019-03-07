# -*- coding: utf-8 -*-
# Copyright (c) 2019, Dokos and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.model.document import Document
from frappe.utils import now, format_datetime
import datetime
import hashlib
import uuid
import os

def get_seal_doc_and_version(doc):
	try:
		module = scrub(doc.meta.module)
		app = frappe.local.module_app[module]
		doctype = scrub(doc.doctype)

		modules = frappe.get_attr("{app}.{module}.doctype.{doctype}.{doctype}_version.get_data".format(
			app=app,
			module=module,
			doctype=doctype
		))() or []

		version = frappe.get_attr("{app}.{module}.doctype.{doctype}.{doctype}_version.DOCTYPE_VERSION".format(
			app=app,
			module=module,
			doctype=doctype
		))
	except ImportError:
		"""
			If the versionning has not been configured, no seal will be recorded.
		"""
		return None

	return get_sealed_doc(doc, modules, version)

def get_sealed_doc(doc, modules, version, report=False):
	current_mapping = [d for d in modules if d["version"] == version]
	meta_fields = frappe.get_meta(doc.doctype).fields

	if current_mapping:
		current_mapping = current_mapping[0]

		sealed_doc = {
			"version": version,
			"doctype": doc.doctype,
			"timestamp": format_datetime(doc.creation, "YYYYMMDDHHmmss")
		}
		for k, v in doc.as_dict().items():
			if k in current_mapping["fields"]:
				if k in current_mapping["tables"].keys():
					child_table = []
					for i in doc.as_dict()[k]:
						table_item = {}
						for j in i:
							if j in current_mapping["tables"][k]:
								table_item[j] = sanitize_value(i[j], [m for m in meta_fields if m.fieldname == j]) if report else i[j]

						child_table.append(table_item)

					sealed_doc[k] = child_table

				else:
					sealed_doc[k] = sanitize_value(doc.as_dict()[k], [m for m in meta_fields if m.fieldname == k]) if report else doc.as_dict()[k]

		return sealed_doc
	else:
		return None

def sanitize_value(value, meta):
	if not meta:
		return value

	if meta and isinstance(meta, list):
		meta = meta[0]

	from frappe.utils.data import DATE_FORMAT, TIME_FORMAT, DATETIME_FORMAT
	if meta.fieldtype == "Datetime":
		value = value.strftime(DATETIME_FORMAT)

	elif meta.fieldtype == "Date":
		value = value.strftime(DATE_FORMAT)

	elif meta.fieldtype == "Time":
		value = value.strftime(TIME_FORMAT)

	return value

def get_chained_seal(doc, calculated=False):

	if not isinstance(doc, dict):
		doc = doc.as_dict()

	if calculated:
		previous_seal = frappe.db.sql("""
			SELECT _seal, max(creation)
			FROM `tab%s`
			WHERE creation < '%s' and _seal!=NULL""" % (doc["doctype"], doc["timestamp"]), as_dict=True)[0]
	else:
		previous_seal = frappe.db.sql("""
			SELECT _seal, max(creation)
			FROM `tab%s`
			WHERE _seal!=NULL""" % doc["doctype"], as_dict=True)[0]

	if not previous_seal._seal:
		if frappe.db.get_global("initial_hash"):
			previous_seal._seal = frappe.db.get_global("initial_hash")
		else:
			previous_seal._seal = hash_line(uuid.uuid4().hex)
			frappe.db.set_global("initial_hash", previous_seal._seal)
			frappe.db.commit()

	current_seal = hash_line(doc)

	return hash_chain(previous_seal._seal, current_seal)

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
