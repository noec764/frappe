# Copyright (c) 2021, Dokos SAS and contributors
# License: MIT. See LICENSE


# import frappe
from frappe.model.document import Document


class RenamedDocument(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date
		document_type: DF.Link
		new_name: DF.Data
		previous_name: DF.Data
	# end: auto-generated types

	pass
