# Copyright (c) 2023, Dokos SAS and contributors
# For license information, please see license.txt

from functools import cache
from typing import TYPE_CHECKING, Any, Literal

import frappe
import frappe.utils
from frappe import _
from frappe.model.document import Document
from frappe.modules.utils import export_module_json
from frappe.utils.safe_block_eval import safe_block_eval

if TYPE_CHECKING:
	from frappe.desk.doctype.summary_card_row.summary_card_row import SummaryCardRow


@cache
def get_filters_global_context():
	today = frappe.utils.nowdate()
	week_start = frappe.utils.get_first_day_of_week(today)
	week_end = frappe.utils.add_days(week_start, 7)
	month_start = frappe.utils.get_first_day(today)
	month_end = frappe.utils.get_last_day(today)
	quarter_start = frappe.utils.get_quarter_start(today)
	quarter_end = frappe.utils.get_quarter_ending(today)
	year_start = frappe.utils.format_date(today, "yyyy-01-01")
	year_end = frappe.utils.format_date(today, "yyyy-12-31")

	return {
		"today": today,
		"week_start": week_start,
		"week_end": week_end,
		"month_start": month_start,
		"month_end": month_end,
		"quarter_start": quarter_start,
		"quarter_end": quarter_end,
		"year_start": year_start,
		"year_end": year_end,
		"last_7_days": frappe.utils.add_days(today, -7),
		"last_month": frappe.utils.add_months(today, -1),
		"last_year": frappe.utils.add_years(today, -1),
	}


class SummaryCard(Document):
	is_standard: bool
	module: str
	dt: str
	label: str
	show_liked_by_me: bool
	show_assigned_to_me: bool
	rows: list["SummaryCardRow"]
	button_view: Literal[
		"",
		"List",
		"Report",
		"Dashboard",
		"Kanban",
		"Calendar",
		"Gantt",
		"Tree",
		"Image",
		"Inbox",
		"Map",
		"No button",
	]
	button_label: str

	def autoname(self):
		if frappe.session.user == "Administrator" or self.is_standard:
			self.name = self.label
		else:
			self.name = self.label + "-" + frappe.session.user

	def validate(self):
		if self.is_standard and not frappe.conf.developer_mode:
			frappe.throw(_("Cannot edit standard document"))
		self.validate_summary_card_rows()

	def on_update(self):
		if self.is_standard and frappe.conf.developer_mode:
			export_module_json(self, self.is_standard, self.module)

	def validate_summary_card_rows(self):
		if not self.rows:
			return
		try:
			idx = 0
			# parse all the filters
			for row in self.iterate_rows():
				idx += 1
		except Exception as e:
			row = self.rows[idx]
			msg = _("{0} {1}").format(f"#{idx + 1}", row.label)
			msg = _("Invalid Filter: {0}").format(msg)
			msg += f" ({e})"
			frappe.throw(msg, exc=e)

	def iterate_rows(self):
		parent = self
		for i, row in enumerate(self.rows):
			yield self.set_row_context(row, parent, i)

			if row.type == "Section Break":
				parent = row

	def set_row_context(
		self, row: "SummaryCardRow", parent: "SummaryCardRow | SummaryCard", index: int
	):
		row._parent = parent
		row._dt = row.dt or parent.dt or self.dt
		row._filters = self.parse_filter_code_for_row(row, parent)
		row._index = index
		return row

	def get_filters_context_for_row(
		self, row: "SummaryCardRow", parent: "SummaryCardRow | SummaryCard"
	):
		local_ctx = {
			"_row": row.as_dict(),
			"_parent": parent.as_dict(),
			"doctype": row._dt,
			"parent_filters": parent.get("_filters") or [],
		}
		return get_filters_global_context() | local_ctx

	def parse_filter_code_for_row(
		self, row: "SummaryCardRow", parent: "SummaryCardRow | SummaryCard"
	):
		code = row.filters_code
		if not code:
			return []

		match code.lower():
			case "draft":
				return [[row._dt, "docstatus", "=", 0]]
			case "submitted":
				return [[row._dt, "docstatus", "=", 1]]
			case "cancelled":
				return [[row._dt, "docstatus", "=", 2]]

		from frappe.utils.data import get_filter, make_filter_tuple

		ctx = self.get_filters_context_for_row(row, parent)
		filters = safe_block_eval(code, _locals=ctx)
		if not filters:
			return []

		if isinstance(filters, list):
			if not isinstance(filters[0], list):
				filters = [filters]

			def make_filt(filt):
				f = get_filter(row._dt, filt)
				return [f.doctype, f.fieldname, f.operator, f.value]

			filters = [make_filt(filt) for filt in filters]
		elif isinstance(filters, dict):
			filters = [make_filter_tuple(row._dt, key, value) for key, value in filters.items()]
		else:
			raise ValueError("Return value must be a list or dict (filters).")

		return filters

	def row_query(self, row: "SummaryCardRow"):
		if row.type == "Count":
			count = frappe.db.count(row._dt, filters=row._filters)
			return {"count": count}

	def row_format_badge(self, row: "SummaryCardRow", data: Any):
		if row.type == "Count":
			formatted_data = frappe.format_value(data["count"])
			fmt = (row.counter_format or "#").replace("#", "{0}", 1)
			return self._(fmt).format(formatted_data)
		return repr(data)

	def get_section_for_me(self):
		if not (self.show_assigned_to_me or self.show_liked_by_me):
			return

		items = []
		user_name = frappe.session.user
		if '"' in frappe.session.user:
			raise frappe.ValidationError(_("Invalid user name"))

		def get_for_me_item(type: str):
			match type:
				case "Assigned To Me":
					filters = [["_assign", "like", f'%"{user_name}"%']]
					icon = "assign"
					color = "var(--cyan)"
					label = _("Assigned To Me", context="Summary Card")
					fmt = _("{0} assigned")
				case "Liked By Me":
					filters = [["_liked_by", "like", f'%"{user_name}"%']]
					icon = "heart"
					color = "var(--pink)"
					label = _("Liked", context="Summary Card")
					fmt = _("{0} likes")
				case _:
					raise NotImplementedError

			count = frappe.db.count(self.dt, filters)
			if count:
				return {
					"type": type,
					"dt": self.dt,
					"label": label,
					"color": color,
					"icon": icon,
					"badge": fmt.format(str(count)),
					"filters": filters,
					"data": {"count": count},
				}

		if self.show_liked_by_me:
			if item := get_for_me_item("Liked By Me"):
				items.append(item)

		if self.show_assigned_to_me:
			if item := get_for_me_item("Assigned To Me"):
				items.append(item)

		if items:
			return {"label": "", "type": "Me", "items": items}

	def get_button_label_for_view(self, view):
		if self.button_label:
			return self._(self.button_label, context="Summary Card Button Label")

		text = f"View {view}"
		text = _(text)

		is_english = frappe.local.lang == "en"
		if (not is_english) and text == f"View {view}":
			# Text was not translated, use a generic label
			return _("View {0}").format(_(view))
		return text

	def handle_error(
		self, e, row_out: dict = None, row: "SummaryCardRow" = None, sections: list = None
	):
		if frappe.conf.developer_mode:
			error_text = _("Error in row {0}").format(repr(row._index) + ": " + row.label)
			error_text += (
				"\n"
				+ frappe.as_json(
					{
						**row.as_dict(),
						"_dt": row._dt,
						"_index": row._index,
						"_filters": row._filters,
					}
				)
				+ "\n\n"
			)
			error_text += repr(e)
			return {
				"error": {
					"message": error_text,
					"traceback": frappe.get_traceback(),
				}
			}
		else:
			sections[-1]["items"].append(
				{
					**row_out,
					"type": row.type,
					"label": _(row.label or ""),
					"dt": row._dt,
					"index": row._index,
					"filters": row._filters,
					"color": "var(--red)",
					"icon": "solid-warning",
					"data": {"count": 0},
					"badge": _("Error"),
					"error": repr(e),
				}
			)

	@frappe.whitelist()
	def get_data(self):
		sections = []

		if for_me := self.get_section_for_me():
			sections.append(for_me)

		# Does not start with a section break, add a default section
		if self.rows[0].type != "Section Break":
			sections.append({"label": "", "type": "Section Break", "items": []})

		for row in self.iterate_rows():
			row_out = {
				"type": row.type,
				"label": self._(row.label or ""),
				"dt": row._dt,
				"index": row._index,
				"filters": row._filters,
				"color": row.get("color", ""),
				"icon": row.get("icon", ""),
				"iconFirst": row.get("icon_first", row._dt != self.dt),
			}

			if row._dt != self.dt and not row_out["icon"]:
				row_out["icon"] = frappe.get_meta(row._dt).icon

			if row.type == "Section Break":
				row_out["items"] = []
				row_out["collapsible"] = row.collapsible
				sections.append(row_out)
				continue

			try:
				data = self.row_query(row)
			except Exception as e:
				if err := self.handle_error(e, row_out, row, sections):
					return err
				continue

			if row.type == "Count":
				row_out["data"] = data
				row_out["badge"] = self.row_format_badge(row, data)

			sections[-1]["items"].append(row_out)

		dt_meta = frappe.get_meta(self.dt)
		button_view = self.button_view or dt_meta.default_view or "List"
		primary_button = None
		if button_view != "No button":
			primary_button = {
				"view": button_view,
				"label": self.get_button_label_for_view(button_view),
			}

		return {
			"title": self._(self.label or self.dt),
			"dt": self.dt,
			"icon": dt_meta.icon,
			"sections": sections,
			"primary_button": primary_button,
		}

	def _(self, text: str, context: str = "Summary Card"):
		if self.get("do_not_translate", False):
			return text
		return _(text, context=context)


@frappe.whitelist()
def get_summary(summary_card_name: str):
	try:
		summary_card: SummaryCard = frappe.get_doc("Summary Card", summary_card_name)
		return summary_card.get_data()
	except Exception as e:
		if len(frappe.local.message_log) > 0:
			last_message = frappe.local.message_log[-1]
			frappe.clear_last_message()
		else:
			last_message = str(e)
		return {"error": last_message, "exc": e}
