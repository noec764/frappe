# Copyright (c) 2021, Dokos SAS and contributors
# License: MIT. See LICENSE


from frappe.model.document import Document


class CoverPage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cover_page: DF.Attach | None
		cover_page_name: DF.Data | None
	# end: auto-generated types

	pass
