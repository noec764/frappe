# Copyright (c) 2023, Dokos SAS and contributors
# For license information, please see license.txt

from typing import Literal

import frappe
from frappe.model.document import Document


class SummaryCardRow(Document):
	type: Literal["Section Break", "Count"]
	label: str
	dt: str
	counter_format: str
	filters_code: str
	collapsible: bool
	color: str
	icon: str
