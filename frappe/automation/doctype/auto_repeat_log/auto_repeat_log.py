# Copyright (c) 2021, Dokos SAS and contributors
# License: MIT. See LICENSE

from frappe.model.document import Document


class AutoRepeatLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		auto_repeat: DF.Link | None
		generated_docname: DF.Data | None
		generated_doctype: DF.Link | None
		generation_date: DF.Datetime | None
		transaction_date: DF.Date | None
	# end: auto-generated types

	pass
