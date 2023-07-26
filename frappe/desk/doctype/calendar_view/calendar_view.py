# Copyright (c) 2021, Frappe Technologies and contributors
# License: MIT. See LICENSE


from frappe.model.document import Document


class CalendarView(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.desk.doctype.calendar_view_status.calendar_view_status import CalendarViewStatus
		from frappe.types import DF

		all_day_field: DF.Literal
		color_field: DF.Literal
		daily_maximum_time: DF.Time | None
		daily_minimum_time: DF.Time | None
		display_event_end: DF.Check
		display_event_time: DF.Check
		end_date_field: DF.Literal
		first_day: DF.Literal[
			"Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
		]
		recurrence_rule_field: DF.Literal
		reference_doctype: DF.Link
		secondary_status: DF.Table[CalendarViewStatus]
		secondary_status_field: DF.Literal
		start_date_field: DF.Literal
		status_field: DF.Literal
		subject_field: DF.Literal
	# end: auto-generated types

	pass
