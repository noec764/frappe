# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

import frappe
import json
from frappe import _
from frappe.utils import get_datetime, get_weekdays, formatdate
from dateutil.rrule import rrulestr

RRULE_FREQUENCIES = {
	"RRULE:FREQ=DAILY": "Daily",
	"RRULE:FREQ=WEEKLY": "Weekly",
	"RRULE:FREQ=MONTHLY": "Monthly",
	"RRULE:FREQ=YEARLY": "Yearly"
}

RRULE_DAYS = {
	"MO": "monday",
	"TU": "tuesday",
	"WE": "wednesday",
	"TH": "thursday",
	"FR": "friday",
	"SA": "saturday",
	"SU": "sunday"
}

FRAMEWORK_FREQUENCIES = {v: '{};'.format(k) for k, v in RRULE_FREQUENCIES.items()}
FRAMEWORK_DAYS = {v: k for k, v in RRULE_DAYS.items()}

@frappe.whitelist()
def update_event(args, field_map):
	"""Updates Event (called via calendar) based on passed `field_map`"""
	args = frappe._dict(json.loads(args))
	field_map = frappe._dict(json.loads(field_map))
	w = frappe.get_doc(args.doctype, args.name)
	w.set(field_map.start, args[field_map.start])
	w.set(field_map.end, args.get(field_map.end))
	w.save()

def get_event_conditions(doctype, filters=None):
	"""Returns SQL conditions with user permissions and filters for event queries"""
	from frappe.desk.reportview import get_filters_cond
	if not frappe.has_permission(doctype):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)

	return get_filters_cond(doctype, filters, [], with_match_conditions = True)

@frappe.whitelist()
def get_events(doctype, start, end, field_map, filters=None, fields=None):

	field_map = frappe._dict(json.loads(field_map))

	doc_meta = frappe.get_meta(doctype)
	for d in doc_meta.fields:
		if d.fieldtype == "Color":
			field_map.update({
				"color": d.fieldname
			})

	if filters:
		filters = json.loads(filters or '')

	if not fields:
		fields = [field_map.start, field_map.end, field_map.title, 'name']

	if field_map.color:
		fields.append(field_map.color)

	if field_map.rrule:
		fields.append(field_map.rrule)

	start_date = "ifnull(%s, '0001-01-01 00:00:00')" % field_map.start
	end_date = "ifnull(%s, '2199-12-31 00:00:00')" % field_map.end

	recurring_filters = list(filters)

	filters += [
		[doctype, start_date, '<=', end],
		[doctype, end_date, '>=', start],
		[doctype, 'repeat_this_event', '!=', 1]
	]

	events = frappe.get_list(doctype, fields=fields, filters=filters)

	recurring_filters += [
		[doctype, 'repeat_this_event', '!=', 0],
		[doctype, "ifnull(repeat_till, '3000-01-01 00:00:00')", '>=', start],
	]
	recurring_events = frappe.get_list(doctype, fields=fields, filters=recurring_filters)

	result = events
	for e in recurring_events:
		result.append(e)
		if field_map.rrule and e[field_map.rrule]:
			rrule_r = list(rrulestr(e.get(field_map.rrule), dtstart=e.get(field_map.start), \
				cache=True).between(after=get_datetime(start), before=get_datetime(end)))
			for r in rrule_r:
				if r == e[field_map.start]:
					continue

				new_e = dict(e)
				new_e[field_map.start] = new_e[field_map.start].replace(year=r.year, month=r.month, day=r.day)
				days_diff = new_e[field_map.start] - e[field_map.start]
				new_e[field_map.end] = new_e[field_map.end] + days_diff
				result.append(new_e)

	return result

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
	rrule = get_rrule_frequency(doc.get("repeat_on"))
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

	if rrule.endswith(";"):
		rrule = rrule[:-1]

	return rrule


def get_rrule_frequency(repeat_on):
	"""
		Frequency can be one of the following: YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY, SECONDLY
	"""
	return FRAMEWORK_FREQUENCIES.get(repeat_on)

def get_repeat_on(start, end, recurrence=None):
	"""
		recurrence is in the form ['RRULE:FREQ=WEEKLY;BYDAY=MO,TU,TH']
		has the frequency and then the days on which the event recurs
		Both have been mapped in a dict for easier mapping.
	"""
	repeat_on = {
		"starts_on": get_datetime(start.get("date")) if start.get("date") else parser.parse(start.get("dateTime")).replace(tzinfo=None),
		"ends_on": get_datetime(end.get("date")) if end.get("date") else parser.parse(end.get("dateTime")).replace(tzinfo=None),
		"all_day": 1 if start.get("date") else 0,
		"repeat_this_event": 1 if recurrence else 0,
		"repeat_on": None,
		"repeat_till": None,
		"sunday": 0,
		"monday": 0,
		"tuesday": 0,
		"wednesday": 0,
		"thursday": 0,
		"friday": 0,
		"saturday": 0
	}

	# recurrence rule "RRULE:FREQ=WEEKLY;BYDAY=MO,TU,TH"
	if recurrence:
		# rrule_frequency = RRULE:FREQ=WEEKLY, byday = BYDAY=MO,TU,TH, until = 20191028
		rrule_frequency, until, byday = get_recurrence_parameters(recurrence)
		repeat_on["repeat_on"] = RRULE_FREQUENCIES.get(rrule_frequency)

		if repeat_on["repeat_on"] == "Daily":
			repeat_on["ends_on"] = None
			repeat_on["repeat_till"] = datetime.strptime(until, "%Y%m%d") if until else None

		if byday and repeat_on["repeat_on"] == "Weekly":
			repeat_on["repeat_till"] = datetime.strptime(until, "%Y%m%d") if until else None
			byday = byday.split("=")[1].split(",")
			for repeat_day in byday:
				repeat_on[RRULE_DAYS[repeat_day]] = 1

		if byday and repeat_on["repeat_on"] == "Monthly":
			byday = byday.split("=")[1]
			repeat_day_week_number, repeat_day_name = None, None

			for num in ["-2", "-1", "1", "2", "3", "4", "5"]:
				if num in byday:
					repeat_day_week_number = num
					break

			for day in ["MO","TU","WE","TH","FR","SA","SU"]:
				if day in byday:
					repeat_day_name = RRULE_DAYS.get(day)
					break

			# Only Set starts_on for the event to repeat monthly
			start_date = parse_rrule_recurrence_rule(int(repeat_day_week_number), repeat_day_name)
			repeat_on["starts_on"] = start_date
			repeat_on["ends_on"] = add_to_date(start_date, minutes=5)
			repeat_on["repeat_till"] = datetime.strptime(until, "%Y%m%d") if until else None

		if repeat_on["repeat_till"] == "Yearly":
			repeat_on["ends_on"] = None
			repeat_on["repeat_till"] = datetime.strptime(until, "%Y%m%d") if until else None

	return repeat_on

def parse_rrule_recurrence_rule(repeat_day_week_number, repeat_day_name):
	"""
		Returns (repeat_on) exact date for combination eg 4TH viz. 4th thursday of a month
	"""
	if repeat_day_week_number < 0:
		# Consider a month with 5 weeks and event is to be repeated in last week of every month, rrule considers
		# a month has 4 weeks and hence itll return -1 for a month with 5 weeks.
		repeat_day_week_number = 4

	weekdays = get_weekdays()
	current_date = now_datetime()
	isset_day_name, isset_day_number = False, False

	# Set the proper day ie if recurrence is 4TH, then align the day to Thursday
	while not isset_day_name:
		isset_day_name = True if weekdays[current_date.weekday()].lower() == repeat_day_name else False
		current_date = add_days(current_date, 1) if not isset_day_name else current_date

	# One the day is set to Thursday, now set the week number ie 4
	while not isset_day_number:
		week_number = get_week_number(current_date)
		isset_day_number = True if week_number == repeat_day_week_number else False
		# check if  current_date week number is greater or smaller than repeat_day week number
		weeks = 1 if week_number < repeat_day_week_number else -1
		current_date = add_to_date(current_date, weeks=weeks) if not isset_day_number else current_date

	return current_date

def get_week_number(dt):
	"""
		Returns the week number of the month for the specified date.
		https://stackoverflow.com/questions/3806473/python-week-number-of-the-month/16804556
	"""
	from math import ceil
	first_day = dt.replace(day=1)

	dom = dt.day
	adjusted_dom = dom + first_day.weekday()

	return int(ceil(adjusted_dom/7.0))

def get_recurrence_parameters(recurrence):
	recurrence = recurrence.split(";")
	frequency, until, byday = None, None, None

	for r in recurrence:
		if "FREQ" in r:
			frequency = r
		elif "UNTIL" in r:
			until = r
		elif "BYDAY" in r:
			byday = r
		else:
			pass

	return frequency, until, byday
