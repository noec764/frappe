# Copyright (c) 2021, Frappe Technologies and contributors
# License: MIT. See LICENSE


import frappe
from frappe.model.document import Document


class Color(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		color: DF.Color
	# end: auto-generated types

	pass


@frappe.whitelist()
def get_colors_used_in_documents(doctype: str, fieldname: str = None):
	try:
		out = list()

		if fieldname:
			color_fields = [fieldname]
		else:
			meta = frappe.get_meta(doctype)
			color_fields = [df.fieldname for df in meta.fields if df.fieldtype == "Color"]

		for fieldname in color_fields:
			colors = frappe.get_list(
				doctype,
				pluck=fieldname,
				distinct=True,
				filters={
					fieldname: ("like", "#%"),
				},
				limit=21,
				order_by="modified desc",
			)
			for color in colors:
				# Ordered set
				color = str(color).upper()
				if color not in out:
					out.append(color)

		return out
	except Exception:
		frappe.clear_last_message()
		return []
