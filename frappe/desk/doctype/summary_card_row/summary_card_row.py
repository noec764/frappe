# Copyright (c) 2023, Dokos SAS and contributors
# For license information, please see license.txt

from typing import Literal

import frappe
from frappe.model.document import Document


class SummaryCardRow(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		collapsible: DF.Check
		color: DF.Color | None
		counter_format: DF.Data | None
		dt: DF.Link | None
		filters_code: DF.Code | None
		icon_first: DF.Check
		label: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		type: DF.Literal["Section Break", "Count"]
	# end: auto-generated types
	pass
