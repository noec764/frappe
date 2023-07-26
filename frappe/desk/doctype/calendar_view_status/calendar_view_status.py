# Copyright (c) 2021, Dokos SAS and contributors
# License: MIT. See LICENSE

from frappe.model.document import Document


class CalendarViewStatus(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		color: DF.Literal["green", "blue", "yellow", "grey", "darkgray", "red", "orange"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		value: DF.Literal
	# end: auto-generated types

	pass
