# Copyright (c) 2022, Dokos SAS and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EventReference(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		name: DF.Int | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_docname: DF.DynamicLink
		reference_doctype: DF.Link
	# end: auto-generated types

	pass
