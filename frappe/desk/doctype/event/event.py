# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from six.moves import range
from six import string_types
import frappe
import json

from frappe.utils import (getdate, cint, add_months, date_diff, add_days,
	nowdate, get_datetime_str, cstr, get_datetime, now_datetime, format_datetime)
from frappe import _
from frappe.model.document import Document
from frappe.utils.user import get_enabled_system_users
from frappe.desk.reportview import get_filters_cond
from frappe.desk.calendar import process_recurring_events

weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
communication_mapping = {"": "Event", "Event": "Event", "Meeting": "Meeting", "Call": "Phone", "Sent/Received Email": "Email", "Other": "Other"}

class Event(Document):
	def validate(self):
		if not self.starts_on:
			self.starts_on = now_datetime()

		# if start == end this scenario doesn't make sense i.e. it starts and ends at the same second!
		self.ends_on = None if self.starts_on == self.ends_on else self.ends_on

		if self.starts_on and self.ends_on:
			self.validate_from_to_dates("starts_on", "ends_on")

		# TODO: New check based on rrule
		#if self.repeat_on == "Daily" and self.ends_on and getdate(self.starts_on) != getdate(self.ends_on):
		#	frappe.throw(_("Daily Events should finish on the Same Day."))

		if self.sync_with_google_calendar and not self.google_calendar:
			frappe.throw(_("Select Google Calendar to which event should be synced."))

	def on_update(self):
		self.sync_communication()

	def on_trash(self):
		communications = frappe.get_all("Communication", dict(reference_doctype=self.doctype, reference_name=self.name))
		if communications:
			for communication in communications:
				frappe.delete_doc_if_exists("Communication", communication.name)

	def sync_communication(self):
		if self.event_participants:
			for participant in self.event_participants:
				filters = [
					["Communication", "reference_doctype", "=", self.doctype],
					["Communication", "reference_name", "=", self.name],
					["Communication Link", "link_doctype", "=", participant.reference_doctype],
					["Communication Link", "link_name", "=", participant.reference_docname]
				]
				comms = frappe.get_all("Communication", filters=filters, fields=["name"])

				if comms:
					for comm in comms:
						communication = frappe.get_doc("Communication", comm.name)
						self.update_communication(participant, communication)
				else:
					meta = frappe.get_meta(participant.reference_doctype)
					if hasattr(meta, "allow_events_in_timeline") and meta.allow_events_in_timeline==1:
						self.create_communication(participant)

	def create_communication(self, participant):
		communication = frappe.new_doc("Communication")
		self.update_communication(participant, communication)
		self.communication = communication.name

	def update_communication(self, participant, communication):
		communication.communication_medium = "Event"
		communication.subject = self.subject
		communication.content = self.description if self.description else self.subject
		communication.communication_date = self.starts_on
		communication.reference_doctype = self.doctype
		communication.reference_name = self.name
		communication.communication_medium = communication_mapping.get(self.event_category) if self.event_category else ""
		communication.status = "Linked"
		communication.add_link(participant.reference_doctype, participant.reference_docname)
		communication.save(ignore_permissions=True)

@frappe.whitelist()
def delete_communication(event, reference_doctype, reference_docname):
	deleted_participant = frappe.get_doc(reference_doctype, reference_docname)
	if isinstance(event, string_types):
		event = json.loads(event)

	filters = [
		["Communication", "reference_doctype", "=", event.get("doctype")],
		["Communication", "reference_name", "=", event.get("name")],
		["Communication Link", "link_doctype", "=", deleted_participant.reference_doctype],
		["Communication Link", "link_name", "=", deleted_participant.reference_docname]
	]

	comms = frappe.get_list("Communication", filters=filters, fields=["name"])

	if comms:
		deletion = []
		for comm in comms:
			delete = frappe.get_doc("Communication", comm.name).delete()
			deletion.append(delete)

		return deletion

	return {}


def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	return """(`tabEvent`.`event_type`='Public' or `tabEvent`.`owner`=%(user)s)""" % {
			"user": frappe.db.escape(user),
		}

def has_permission(doc, user):
	if doc.event_type=="Public" or doc.owner==user:
		return True

	return False

def send_event_digest():
	today = nowdate()
	for user in get_enabled_system_users():
		events = get_events(today, today, user.name, for_reminder=True)
		if events:
			frappe.set_user_lang(user.name, user.language)

			for e in events:
				e.starts_on = format_datetime(e.starts_on, 'hh:mm a')
				if e.all_day:
					e.starts_on = "All Day"

			frappe.sendmail(
				recipients=user.email,
				subject=frappe._("Upcoming Events for Today"),
				template="upcoming_events",
				args={
					'events': events,
				},
				header=[frappe._("Events in Today's Calendar"), 'blue']
			)

@frappe.whitelist()
def get_events(start, end, user=None, for_reminder=False, filters=None):
	if not user:
		user = frappe.session.user

	if isinstance(filters, string_types):
		filters = json.loads(filters)

	filter_condition = get_filters_cond('Event', filters, [])

	tables = ["`tabEvent`"]
	if "`tabEvent Participants`" in filter_condition:
		tables.append("`tabEvent Participants`")

	events = frappe.db.sql("""
		SELECT `tabEvent`.name,
				`tabEvent`.subject,
				`tabEvent`.description,
				`tabEvent`.color,
				`tabEvent`.starts_on,
				`tabEvent`.ends_on,
				`tabEvent`.owner,
				`tabEvent`.all_day,
				`tabEvent`.event_type,
				`tabEvent`.repeat_this_event,
				`tabEvent`.rrule,
				`tabEvent`.repeat_till
		FROM {tables}
		WHERE (
				(
					(date(`tabEvent`.starts_on) BETWEEN date(%(start)s) AND date(%(end)s))
					OR (date(`tabEvent`.ends_on) BETWEEN date(%(start)s) AND date(%(end)s))
					OR (
						date(`tabEvent`.starts_on) <= date(%(start)s)
						AND date(`tabEvent`.ends_on) >= date(%(end)s)
					)
				)
				OR (
					date(`tabEvent`.starts_on) <= date(%(start)s)
					AND `tabEvent`.repeat_this_event=1
					AND coalesce(`tabEvent`.repeat_till, '3000-01-01') > date(%(start)s)
				)
			)
		{reminder_condition}
		{filter_condition}
		AND (
				`tabEvent`.event_type='Public'
				OR `tabEvent`.owner=%(user)s
				OR EXISTS(
					SELECT `tabDocShare`.name
					FROM `tabDocShare`
					WHERE `tabDocShare`.share_doctype='Event'
						AND `tabDocShare`.share_name=`tabEvent`.name
						AND `tabDocShare`.user=%(user)s
				)
			)
		AND `tabEvent`.status='Open'
		ORDER BY `tabEvent`.starts_on""".format(
			tables=", ".join(tables),
			filter_condition=filter_condition,
			reminder_condition="AND coalesce(`tabEvent`.send_reminder, 0)=1" if for_reminder else ""
		), {
			"start": start,
			"end": end,
			"user": user,
		}, as_dict=1)

	# process recurring events
	result = list(events)
	for event in events:
		if event.get("repeat_this_event"):
			result.extend(process_recurring_events(event, start, end, "starts_on", "ends_on", "rrule"))

	return result

def delete_events(ref_type, ref_name, delete_event=False):
	participations = frappe.get_all("Event Participants", filters={"reference_doctype": ref_type, "reference_docname": ref_name,
		"parenttype": "Event"}, fields=["parent", "name"])

	if participations:
		for participation in participations:
			if delete_event:
				frappe.delete_doc("Event", participation.parent, for_reload=True)
			else:
				total_participants = frappe.get_all("Event Participants", filters={"parenttype": "Event", "parent": participation.parent})

				if len(total_participants) <= 1:
					frappe.db.sql("DELETE FROM `tabEvent` WHERE `name` = %(name)s", {'name': participation.parent})

				frappe.db.sql("DELETE FROM `tabEvent Participants ` WHERE `name` = %(name)s", {'name': participation.name})

# Close events if ends_on or repeat_till is less than now_datetime
def set_status_of_events():
	events = frappe.get_list("Event", filters={"status": "Open"}, fields=["name", "ends_on", "repeat_till"])
	for event in events:
		if (event.ends_on and getdate(event.ends_on) < getdate(nowdate())) \
			or (event.repeat_till and getdate(event.repeat_till) < getdate(nowdate())):

			frappe.db.set_value("Event", event.name, "status", "Closed")