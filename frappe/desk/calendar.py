# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE


import json
from datetime import timedelta

from dateutil.rrule import rrulestr

import frappe
from frappe import _
from frappe.utils import formatdate, get_datetime, get_weekdays

RRULE_FREQUENCIES = {
	"RRULE:FREQ=DAILY": "Daily",
	"RRULE:FREQ=WEEKLY": "Weekly",
	"RRULE:FREQ=MONTHLY": "Monthly",
	"RRULE:FREQ=YEARLY": "Yearly",
}

RRULE_DAYS = {
	"MO": "monday",
	"TU": "tuesday",
	"WE": "wednesday",
	"TH": "thursday",
	"FR": "friday",
	"SA": "saturday",
	"SU": "sunday",
}

FRAMEWORK_FREQUENCIES = {v: f"{k};" for k, v in RRULE_FREQUENCIES.items()}
FRAMEWORK_DAYS = {v: k for k, v in RRULE_DAYS.items()}


@frappe.whitelist()
def update_event(args, field_map):
	"""Updates Event (called via calendar) based on passed `field_map`"""
	args = frappe._dict(json.loads(args))
	field_map = frappe._dict(json.loads(field_map))
	w = frappe.get_doc(args.doctype, args.name)
	w.set(field_map.start, get_datetime(args[field_map.start]))
	w.set(field_map.end, get_datetime(args.get(field_map.end)))

	if field_map.get("resourceId"):
		w.set(field_map.resourceId, args[field_map.resourceId])

	w.save()


def get_event_conditions(doctype, filters=None):
	"""Returns SQL conditions with user permissions and filters for event queries"""
	from frappe.desk.reportview import get_filters_cond

	if not frappe.has_permission(doctype):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	return get_filters_cond(doctype, filters, [], with_match_conditions=True)


@frappe.whitelist()
def get_events(doctype, start, end, field_map, filters=None, fields=None):
	field_map = frappe._dict(json.loads(field_map))
	fields = frappe.parse_json(fields)

	doc_meta = frappe.get_meta(doctype)
	for d in doc_meta.fields:
		if d.fieldtype == "Color":
			field_map.update({"color": d.fieldname})

	filters = json.loads(filters) if filters else []

	if not fields:
		fields = [field_map.start, field_map.end, field_map.title, "name"]

	for f in field_map.values():
		if f in frappe.model.default_fields or doc_meta.has_field(f):
			fields.append(f)

	start_date = "ifnull(%s, '0001-01-01 00:00:00')" % field_map.start
	end_date = "ifnull(%s, '2199-12-31 00:00:00')" % field_map.end

	recurring_filters = list(filters)

	filters += [[doctype, start_date, "<=", end], [doctype, end_date, ">=", start]]

	if doc_meta.has_field("repeat_this_event"):
		filters.append([doctype, "repeat_this_event", "!=", 1])

	fields = list({field for field in fields if field})
	events = frappe.get_list(doctype, fields=fields, filters=filters)

	if doc_meta.has_field("repeat_this_event") and doc_meta.has_field("repeat_till"):
		recurring_filters += [
			[doctype, "repeat_this_event", "!=", 0],
			[doctype, "ifnull(repeat_till, '3000-01-01 00:00:00')", ">=", start],
		]
		recurring_events = frappe.get_list(doctype, fields=fields, filters=recurring_filters)

		if recurring_events:
			for recurring_event in recurring_events:
				events.extend(
					process_recurring_events(
						recurring_event, start, end, field_map.start, field_map.end, field_map.rrule
					)
				)

	return events


def process_recurring_events(event, start, end, starts_on_field, ends_on_field, rrule_field):
	result = []
	if rrule_field and event.get(rrule_field):
		try:
			rrule_r = list(
				rrulestr(
					event.get(rrule_field),
					dtstart=event.get(starts_on_field),
					ignoretz=True,
					cache=False,
				).between(
					after=get_datetime(start) + timedelta(seconds=-1),
					before=get_datetime(end) + timedelta(seconds=1),
				)
			)

			for r in rrule_r:
				new_e = frappe._dict(event)
				new_e[starts_on_field] = new_e.get(starts_on_field).replace(
					year=r.year, month=r.month, day=r.day
				)
				days_diff = new_e.get(starts_on_field) - event.get(starts_on_field)
				new_e[ends_on_field] = (
					(get_datetime(event.get(ends_on_field)) + days_diff)
					if event.get(ends_on_field)
					else new_e.get(starts_on_field)
				)
				new_e["groupId"] = event.get("name")
				result.append(new_e)
		except Exception:
			print(frappe.get_traceback())
			return result

	return result


# Keep for legacy
def get_rrule(doc):
	"""
	Transforms the following object into a RRULE:
	{
	        "starts_on",
	        "ends_on",
	        "all_day",
	        "repeat_this_event",
	        "repeat_on",
	        "repeat_till",
	        "sunday",
	        "monday",
	        "tuesday",
	        "wednesday",
	        "thursday",
	        "friday",
	        "saturday"
	}
	"""
	rrule = get_rrule_frequency(doc.get("repeat_on")) or ""
	weekdays = get_weekdays()

	if doc.get("repeat_on") == "Weekly":
		byday = [FRAMEWORK_DAYS.get(day.lower()) for day in weekdays if doc.get(day.lower())]
		rrule += "BYDAY={};".format(",".join(byday))

	elif doc.get("repeat_on") == "Monthly":
		week_number = str(get_week_number(get_datetime(doc.get("starts_on"))))
		week_day = weekdays[get_datetime(doc.get("starts_on")).weekday()].lower()
		rrule += "BYDAY=" + week_number + FRAMEWORK_DAYS.get(week_day) + ";"

	if doc.get("interval"):
		rrule += "INTERVAL={};".format(doc.get("interval"))

	if doc.get("repeat_till"):
		rrule += "UNTIL={}".format(formatdate(doc.get("repeat_till"), "YYYYMMdd"))

	if rrule and rrule.endswith(";"):
		rrule = rrule[:-1]

	return rrule


def get_rrule_frequency(repeat_on):
	"""
	Frequency can be one of the following: YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY, SECONDLY
	"""
	return FRAMEWORK_FREQUENCIES.get(repeat_on)


def get_week_number(dt):
	"""
	Returns the week number of the month for the specified date.
	https://stackoverflow.com/questions/3806473/python-week-number-of-the-month/16804556
	"""
	from math import ceil

	first_day = dt.replace(day=1)

	dom = dt.day
	adjusted_dom = dom + first_day.weekday()

	return int(ceil(adjusted_dom / 7.0))


@frappe.whitelist()
def get_resource_ids(doctype: str, resource: str):
	if not doctype or not resource:
		return []

	# Parse the given resource string to find the field and optional child_field.
	# e.g. "name", "employee", "assigned_to.employee"
	splits = resource.split(".")
	if len(splits) == 1:
		fieldname, child_field = resource, resource
	elif len(splits) == 2:
		fieldname, child_field = splits
	else:
		raise ValueError("resource")

	field = frappe.get_meta(doctype).get_field(fieldname)
	base_doctype = doctype
	rsrc_doctype = doctype

	if field.fieldtype == "Select":
		return [
			{"id": option, "title": _(option) or _("No value")} for option in field.options.split("\n")
		]

	if field.fieldtype == "Link":
		rsrc_doctype = field.options

	if field.fieldtype == "Table" or field.fieldtype == "Table MultiSelect":
		dt_table = frappe.get_meta(field.options)
		base_doctype = field.options
		rsrc_doctype = dt_table.get_field(child_field).options

	B = frappe.qb.DocType(base_doctype)
	qb_id = B[child_field].as_("id")
	query = frappe.qb.from_(B).select(qb_id).distinct()

	if rsrc_doctype:
		title_field = frappe.get_meta(rsrc_doctype).get_title_field()
		R = frappe.qb.DocType(rsrc_doctype)
		query = query.from_(R).select(R[title_field].as_("title")).where(R.name == qb_id).distinct()

	resources = query.run(as_dict=True)
	return resources


@frappe.whitelist()
def get_resources_for_doctype(doctype):
	meta = frappe.get_meta(doctype)

	excluded_fields = ["amended_from"]

	select_and_link_fields = [
		{"id": f.fieldname, "title": f.label}
		for f in meta.fields
		if f.fieldtype in ["Select", "Link"] and not f.hidden and f.fieldname not in excluded_fields
	]

	return select_and_link_fields
