# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE


import json

import frappe
from frappe import _
from frappe.model import core_doctypes_list
from frappe.model.docfield import supports_translation
from frappe.model.document import Document
from frappe.query_builder.functions import IfNull
from frappe.utils import cstr


class CustomField(Document):
	def autoname(self):
		self.set_fieldname()
		self.name = self.dt + "-" + self.fieldname

	def set_fieldname(self):
		if not self.fieldname:
			label = self.label
			if not label:
				if self.fieldtype in ["Section Break", "Column Break", "Tab Break"]:
					label = self.fieldtype + "_" + str(self.idx)
				else:
					frappe.throw(_("Label is mandatory"))

			# remove special characters from fieldname
			self.fieldname = "".join(
				filter(lambda x: x.isdigit() or x.isalpha() or "_", cstr(label).replace(" ", "_"))
			)

		# fieldnames should be lowercase
		self.fieldname = self.fieldname.lower()

	def before_insert(self):
		self.set_fieldname()

	def validate(self):
		# these imports have been added to avoid cyclical import, should fix in future
		from frappe.core.doctype.doctype.doctype import check_fieldname_conflicts
		from frappe.custom.doctype.customize_form.customize_form import CustomizeForm

		# don't always get meta to improve performance
		# setting idx is just an improvement, not a requirement
		if self.is_new() or self.insert_after == "append":
			meta = frappe.get_meta(self.dt, cached=False)
			fieldnames = [df.fieldname for df in meta.get("fields")]

			if self.is_new() and self.fieldname in fieldnames:
				frappe.throw(
					_("A field with the name {0} already exists in {1}").format(
						frappe.bold(self.fieldname), _(self.dt)
					)
				)

			if self.insert_after == "append":
				self.insert_after = fieldnames[-1]

			if self.insert_after and self.insert_after in fieldnames:
				self.idx = fieldnames.index(self.insert_after) + 1

		if (
			not self.is_virtual
			and (doc_before_save := self.get_doc_before_save())
			and (old_fieldtype := doc_before_save.fieldtype) != self.fieldtype
			and not CustomizeForm.allow_fieldtype_change(old_fieldtype, self.fieldtype)
		):
			frappe.throw(
				_("Fieldtype cannot be changed from {0} to {1}").format(old_fieldtype, self.fieldtype)
			)

		if not self.fieldname:
			frappe.throw(_("Fieldname not set for Custom Field"))

		if self.get("translatable", 0) and not supports_translation(self.fieldtype):
			self.translatable = 0

		check_fieldname_conflicts(self)

	def on_update(self):
		if not frappe.flags.in_setup_wizard:
			frappe.clear_cache(doctype=self.dt)

		if not self.flags.ignore_validate:
			# validate field
			from frappe.core.doctype.doctype.doctype import validate_fields_for_doctype

			validate_fields_for_doctype(self.dt)

		# update the schema
		if not frappe.db.get_value("DocType", self.dt, "issingle") and not frappe.flags.in_setup_wizard:
			frappe.db.updatedb(self.dt)

	def on_trash(self):
		# check if Admin owned field
		if self.owner == "Administrator" and frappe.session.user != "Administrator":
			frappe.throw(
				_(
					"Custom Field {0} is created by the Administrator and can only be deleted through the Administrator account."
				).format(frappe.bold(self.label))
			)

		# delete property setter entries
		frappe.db.delete("Property Setter", {"doc_type": self.dt, "field_name": self.fieldname})

		frappe.clear_cache(doctype=self.dt)

	def validate_insert_after(self, meta):
		if not meta.get_field(self.insert_after):
			frappe.throw(
				_(
					"Insert After field '{0}' mentioned in Custom Field '{1}', with label '{2}', does not exist"
				).format(self.insert_after, self.name, self.label),
				frappe.DoesNotExistError,
			)

		if self.fieldname == self.insert_after:
			frappe.throw(_("Insert After cannot be set as {0}").format(meta.get_label(self.insert_after)))


@frappe.whitelist()
def get_fields_label(doctype=None):
	meta = frappe.get_meta(doctype)

	if doctype in core_doctypes_list:
		return frappe.msgprint(_("Custom Fields cannot be added to core DocTypes."))

	if meta.custom:
		return frappe.msgprint(_("Custom Fields can only be added to a standard DocType."))

	return [
		{"value": df.fieldname or "", "label": _(df.label or "")}
		for df in frappe.get_meta(doctype).get("fields")
	]


def create_custom_field_if_values_exist(doctype, df):
	df = frappe._dict(df)
	if df.fieldname in frappe.db.get_table_columns(doctype) and frappe.db.count(
		dt=doctype, filters=IfNull(df.fieldname, "") != ""
	):
		create_custom_field(doctype, df)


def create_custom_field(doctype, df, ignore_validate=False, is_system_generated=True):
	df = frappe._dict(df)
	if not df.fieldname and df.label:
		df.fieldname = frappe.scrub(df.label)
	if not frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": df.fieldname}):
		custom_field = frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": doctype,
				"permlevel": 0,
				"fieldtype": "Data",
				"hidden": 0,
				"is_system_generated": is_system_generated,
			}
		)
		custom_field.update(df)
		custom_field.flags.ignore_validate = ignore_validate
		custom_field.insert()


def create_custom_fields(custom_fields, ignore_validate=False, update=True):
	"""Add / update multiple custom fields

	:param custom_fields: example `{'Sales Invoice': [dict(fieldname='test')]}`"""

	if not ignore_validate and frappe.flags.in_setup_wizard:
		ignore_validate = True

	for doctypes, fields in custom_fields.items():
		if isinstance(fields, dict):
			# only one field
			fields = [fields]

		if isinstance(doctypes, str):
			# only one doctype
			doctypes = (doctypes,)

		for doctype in doctypes:
			for df in fields:
				field = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": df["fieldname"]})
				if not field:
					try:
						df["owner"] = "Administrator"
						create_custom_field(doctype, df, ignore_validate=ignore_validate)
					except frappe.exceptions.DuplicateEntryError:
						pass
				elif update:
					custom_field = frappe.get_doc("Custom Field", field)
					custom_field.flags.ignore_validate = ignore_validate
					custom_field.update(df)
					custom_field.save()

		frappe.clear_cache(doctype=doctype)
		frappe.db.updatedb(doctype)


@frappe.whitelist()
def add_custom_field(doctype, df):
	df = json.loads(df)
	return create_custom_field(doctype, df)
