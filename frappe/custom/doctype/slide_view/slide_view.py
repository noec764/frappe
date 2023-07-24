# Copyright (c) 2021, Dokos SAS and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SlideView(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		add_fullpage_edit_btn: DF.Check
		allow_any: DF.Check
		allow_back: DF.Check
		can_create_doc: DF.Check
		can_edit_doc: DF.Check
		done_state: DF.Check
		reference_doctype: DF.Link | None
		route: DF.Data
		title: DF.Data
	# end: auto-generated types

	pass
