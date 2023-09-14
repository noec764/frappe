# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import datetime
import json
from typing import Union

from googleapiclient.errors import HttpError

import frappe
from frappe import _
from frappe.desk.calendar import process_recurring_events
from frappe.desk.doctype.notification_settings.notification_settings import (
	is_email_notifications_enabled_for_type,
)
from frappe.desk.reportview import get_filters_cond
from frappe.integrations.doctype.google_calendar.google_calendar import (
	format_date_according_to_google_calendar,
	get_google_calendar_object,
	get_timezone_naive_datetime,
)
from frappe.utils import (
	add_days,
	cint,
	format_datetime,
	get_datetime,
	getdate,
	now_datetime,
	nowdate,
)
from frappe.utils.user import get_enabled_system_users
from frappe.website.utils import get_sidebar_items
from frappe.website.website_generator import WebsiteGenerator
from frappe.www.printview import get_html_and_style

weekdays = [
	"monday",
	"tuesday",
	"wednesday",
	"thursday",
	"friday",
	"saturday",
	"sunday",
]
communication_mapping = {
	"": "Event",
	"Event": "Event",
	"Meeting": "Meeting",
	"Call": "Phone",
	"Sent/Received Email": "Email",
	"Other": "Other",
}

FIELD_MAP = {
	"id": "name",
	"start": "starts_on",
	"end": "ends_on",
	"allDay": "all_day",
	"title": "subject",
}


class Event(WebsiteGenerator):
	def validate(self):
		if not self.starts_on:
			self.starts_on = now_datetime()

		# if start == end this scenario doesn't make sense i.e. it starts and ends at the same second!
		self.ends_on = None if self.starts_on == self.ends_on else self.ends_on

		if self.starts_on and self.ends_on:
			self.validate_from_to_dates("starts_on", "ends_on")

		if (
			self.rrule
			and "DAILY" in self.rrule
			and self.ends_on
			and getdate(self.starts_on) != getdate(self.ends_on)
		):
			frappe.throw(_("Daily Events should finish on the Same Day."))

		if self.sync_with_google_calendar and not self.google_calendar:
			frappe.throw(_("Select Google Calendar to which event should be synced."))

		self.set_route()

	def autoname(self):
		return

	def get_feed(self):
		return self.subject

	def set_route(self):
		if not self.route:
			self.route = f"events/{self.name}-{self.scrub(self.subject)[:30]}"
		self.route = self.route.lstrip("/")

	def before_save(self):
		if self.google_calendar and not self.google_calendar_id:
			self.google_calendar_id = frappe.db.get_value(
				"Google Calendar", self.google_calendar, "google_calendar_id"
			)

		if isinstance(self.rrule, list) and self.rrule > 1:
			self.rrule = self.rrule[0]

		self.make_participants_unique()

	def on_update(self):
		self.sync_communication()

	def after_insert(self):
		if self.google_calendar:
			calendar = frappe.db.get_value(
				"Google Calendar", self.google_calendar, ["reference_document", "user"], as_dict=True
			)
			if calendar.reference_document == "Event" and calendar.user != self.owner:
				self.db_set("owner", calendar.user)

	def on_trash(self):
		communications = frappe.get_all(
			"Communication", dict(reference_doctype=self.doctype, reference_name=self.name)
		)
		if communications:
			for communication in communications:
				frappe.delete_doc_if_exists("Communication", communication.name)

	def sync_communication(self):
		if self.event_participants:
			comms = set()
			for participant in self.event_participants:
				filters = [
					["Communication", "reference_doctype", "=", self.doctype],
					["Communication", "reference_name", "=", self.name],
					["Communication Link", "link_doctype", "=", "Contact"],
					["Communication Link", "link_name", "=", participant.contact],
				]
				comm_names = frappe.get_all("Communication", filters=filters, pluck="name")
				comms.update(comm_names)

			if comms:
				for comm in comms:
					communication = frappe.get_doc("Communication", comm)
					self.update_communication(self.event_participants, communication)
			else:
				self.create_communication(self.event_participants)

	def create_communication(self, participants):
		communication = frappe.new_doc("Communication")
		self.update_communication(participants, communication)
		self.communication = communication.name

	def update_communication(self, participants, communication):
		communication.communication_medium = "Event"
		communication.subject = self.subject
		communication.content = self.description if self.description else self.subject
		communication.communication_date = self.starts_on
		communication.sender = self.owner
		communication.sender_full_name = frappe.utils.get_fullname(self.owner)
		communication.reference_doctype = self.doctype
		communication.reference_name = self.name
		communication.communication_medium = (
			communication_mapping.get(self.event_category) if self.event_category else ""
		)
		communication.not_added_to_reference_timeline = 1
		communication.status = "Linked"

		current_links = set()
		for link in communication.timeline_links:
			current_links.add((link.link_doctype, link.link_name))

		future_links = set()
		for participant in participants:
			future_links.add(("Contact", participant.contact))
			contact = frappe.get_doc("Contact", participant.contact)
			for link in contact.links or []:
				if link.link_doctype and link.link_name:
					meta = frappe.get_meta(link.link_doctype)
					if hasattr(meta, "allow_events_in_timeline") and meta.allow_events_in_timeline == 1:
						future_links.add((link.link_doctype, link.link_name))

		added_links = future_links.difference(current_links)  # only in future
		removed_links = current_links.difference(future_links)  # only in current

		for link_doctype, link_name in added_links:
			communication.add_link(link_doctype, link_name)

		for link_doctype, link_name in removed_links:
			communication.remove_link(link_doctype, link_name)

		from frappe.utils import validate_email_address

		if validate_email_address(communication.sender):
			communication.save(ignore_permissions=True)

	def add_participant(self, contact):
		"""Add a single participant to event participants
		Args:
		        contact (string): Contact name
		"""
		self.append(
			"event_participants",
			{
				"contact": contact,
			},
		)

	def add_participants(self, participants):
		"""Add participant entry
		Args:
		        participants ([Array]): Array of contact names
		"""
		for participant in participants:
			self.add_participant(participant)

	def remove_participant(self, participant):
		participant_list = []
		for event_participant in self.event_participants:
			if event_participant != participant:
				participant_list.append(event_participant)

		self.event_participants = participant_list

	def make_participants_unique(self):
		seen_contacts = set()
		kept_participants = []

		for event_participant in self.event_participants or []:
			contact = event_participant.contact
			if contact not in seen_contacts:
				kept_participants.append(event_participant)
			seen_contacts.add(contact)

		self.event_participants = kept_participants

	def add_reference(self, reference_doctype, reference_name):
		self.append(
			"event_references",
			{"reference_doctype": reference_doctype, "reference_docname": reference_name},
		)

	def get_context(self, context):
		if not cint(self.published):
			self.show_permission_error()

		if self.visible_for != "All":
			if frappe.session.user == "Guest":
				self.show_permission_error()
			elif self.visible_for == "Role" and self.role not in frappe.get_roles(frappe.session.user):
				self.show_permission_error()

		is_guest = frappe.session.user == "Guest"

		context.no_cache = 1
		context.sidebar_items = get_sidebar_items(context.website_sidebar)
		context.show_sidebar = not is_guest
		context.show_close_button = not is_guest

		content = f'<p class="card-text">{self.description or ""}</p>'
		event_style = ""
		if self.portal_print_format:
			print_format_content = self.print_format_content()
			content = print_format_content.get("html")
			event_style = print_format_content.get("style")

		context.content = content
		context.event_style = event_style

		context.attachments = (
			frappe.get_all(
				"File",
				fields=["name", "file_name", "file_url"],
				filters={
					"attached_to_name": self.name,
					"attached_to_doctype": "Event",
					"is_private": 0,
				},
			)
			if self.display_public_files
			else []
		)

	def print_format_content(self):
		frappe.flags.ignore_print_permissions = True
		return get_html_and_style(self, print_format=self.portal_print_format)

	def show_permission_error(self):
		frappe.throw(_("This event is not publicly available"), frappe.PermissionError)


def get_list_context(context=None):
	context.update(
		{
			"title": _("Upcoming Events"),
			"no_cache": 1,
			"no_breadcrumbs": True,
			"show_sidebar": frappe.session.user != "Guest",
			"get_list": get_events_list,
			"row_template": "desk/doctype/event/templates/event_row.html",
			"header_action": frappe.render_template(
				"desk/doctype/event/templates/event_list_action.html", {}
			),
			"base_scripts": ["events-portal.bundle.js", "controls.bundle.js"],
		}
	)


def get_events_list(
	doctype, txt, filters, limit_start, limit_page_length=20, order_by="starts_on"
):
	return get_prepared_events(
		nowdate(),
		add_days(nowdate(), 365),
		limit_start,
		limit_page_length,
		merge_recurrences=True,
	)


@frappe.whitelist()
def delete_communication(event, reference_doctype, reference_docname):
	deleted_participant = frappe.get_doc(reference_doctype, reference_docname)
	if isinstance(event, str):
		event = json.loads(event)

	filters = [
		["Communication", "reference_doctype", "=", event.get("doctype")],
		["Communication", "reference_name", "=", event.get("name")],
		["Communication Link", "link_doctype", "=", deleted_participant.reference_doctype],
		["Communication Link", "link_name", "=", deleted_participant.reference_docname],
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
	if not user:
		user = frappe.session.user

	return """(`tabEvent`.`event_type`='Public' or `tabEvent`.`owner`={user})""".format(
		user=frappe.db.escape(user),
	)


def has_permission(doc, user):
	if doc.event_type == "Public" or doc.owner == user:
		return True

	return False


def send_event_digest():
	today = nowdate()

	# select only those users that have event reminder email notifications enabled
	users = [
		user
		for user in get_enabled_system_users()
		if is_email_notifications_enabled_for_type(user.name, "Event Reminders")
	]

	for user in users:
		events = get_events(today, today, user.name, for_reminder=True)
		if events:
			frappe.set_user_lang(user.name, user.language)

			for e in events:
				e.starts_on = format_datetime(e.starts_on, "hh:mm a")
				if e.all_day:
					e.starts_on = _("All Day")

			frappe.sendmail(
				recipients=user.email,
				subject=frappe._("Upcoming Events for Today"),
				template="upcoming_events",
				args={
					"events": events,
				},
				header=[frappe._("Events in Today's Calendar"), "blue"],
			)


@frappe.whitelist()
def get_events(
	start: str | datetime.date,
	end: str | datetime.date,
	user=None,
	for_reminder=False,
	filters=None,
	field_map=None,
	limit_start=0,
	limit_page_length=None,
	additional_condition=None,
	ignore_permissions=False,
) -> list[frappe._dict]:
	if not user:
		user = frappe.session.user

	if isinstance(filters, str):
		filters = json.loads(filters)

	additional_fields = ""
	if field_map:
		additional_fields = ", " + ", ".join(
			[f"`tabEvent`.{f}" for f in frappe.parse_json(field_map).values()]
		)

	filter_condition = get_filters_cond("Event", filters, [], ignore_permissions=ignore_permissions)

	tables = ["`tabEvent`"]
	if "`tabEvent Participants`" in filter_condition:
		tables.append("`tabEvent Participants`")

	events = frappe.db.sql(
		"""
		SELECT `tabEvent`.name,
				`tabEvent`.subject,
				`tabEvent`.image,
				`tabEvent`.status,
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
				{additional_fields}
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
		{additional_condition}
		ORDER BY `tabEvent`.starts_on
		{limit_condition}""".format(
			additional_fields=additional_fields,
			tables=", ".join(tables),
			filter_condition=filter_condition,
			reminder_condition="AND coalesce(`tabEvent`.send_reminder, 0)=1" if for_reminder else "",
			limit_condition=f"LIMIT {limit_page_length} OFFSET {limit_start}" if limit_page_length else "",
			additional_condition=additional_condition or "",
		),
		{
			"start": start,
			"end": end,
			"user": user,
		},
		as_dict=1,
	)

	result = []
	for event in events:
		if event.get("repeat_this_event"):
			event_start = get_datetime(start).replace(hour=0, minute=0, second=0)
			event_end = get_datetime(end).replace(hour=23, minute=59, second=59)

			recurring_events = process_recurring_events(
				event, event_start, event_end, "starts_on", "ends_on", "rrule"
			)
			if recurring_events:
				result.extend(recurring_events)

			elif event.starts_on <= event_end and (not event.ends_on or event.ends_on >= event_start):
				result.append(event)

		else:
			result.append(event)

	return sorted(result, key=lambda d: d["starts_on"])


# Close events if ends_on or repeat_till is less than now_datetime
def set_status_of_events():
	events = frappe.get_list(
		"Event", filters={"status": "Open"}, fields=["name", "ends_on", "repeat_till"]
	)
	for event in events:
		if (event.ends_on and getdate(event.ends_on) < getdate(nowdate())) or (
			event.repeat_till and getdate(event.repeat_till) < getdate(nowdate())
		):

			frappe.db.set_value("Event", event.name, "status", "Closed")


def insert_event_to_calendar(account, event, recurrence=None):
	"""
	Inserts event in Frappe Calendar during Sync
	"""
	start = event.get("start")
	end = event.get("end")

	calendar_event = {
		"doctype": "Event",
		"subject": event.get("summary") or _("No Subject"),
		"description": event.get("description"),
		"sync_with_google_calendar": 1,
		"google_calendar": account.name,
		"google_calendar_id": account.google_calendar_id,
		"google_calendar_event_id": event.get("id"),
		"rrule": recurrence,
		"starts_on": get_datetime(start.get("date"))
		if start.get("date")
		else get_timezone_naive_datetime(start),
		"ends_on": get_datetime(end.get("date"))
		if end.get("date")
		else get_timezone_naive_datetime(end),
		"all_day": 1 if start.get("date") else 0,
		"repeat_this_event": 1 if recurrence else 0,
		"owner": account.user,
	}
	doc = frappe.get_doc(calendar_event)
	doc.flags.pulled_from_google_calendar = True
	doc.insert(ignore_permissions=True)


def update_event_in_calendar(account, event, recurrence=None):
	"""
	Updates Event in Frappe Calendar if any existing Google Calendar Event is updated
	"""
	start = event.get("start")
	end = event.get("end")

	calendar_event = frappe.get_doc("Event", {"google_calendar_event_id": event.get("id")})
	calendar_event.subject = event.get("summary") or _("No Subject")
	calendar_event.description = event.get("description")
	calendar_event.rrule = recurrence
	calendar_event.starts_on = (
		get_datetime(start.get("date")) if start.get("date") else get_timezone_naive_datetime(start)
	)
	calendar_event.ends_on = (
		get_datetime(end.get("date")) if end.get("date") else get_timezone_naive_datetime(end)
	)
	calendar_event.all_day = 1 if start.get("date") else 0
	calendar_event.repeat_this_event = 1 if recurrence else 0
	calendar_event.flags.pulled_from_google_calendar = True
	calendar_event.save(ignore_permissions=True)


def close_event_in_calendar(account, event):
	# If any synced Google Calendar Event is cancelled, then close the Event
	frappe.db.set_value(
		"Event",
		{
			"google_calendar_id": account.google_calendar_id,
			"google_calendar_event_id": event.get("id"),
		},
		"status",
		"Closed",
	)
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Event",
			"reference_name": frappe.db.get_value(
				"Event",
				{
					"google_calendar_id": account.google_calendar_id,
					"google_calendar_event_id": event.get("id"),
				},
				"name",
			),
			"content": " - Event deleted from Google Calendar.",
		}
	).insert(ignore_permissions=True)


def insert_event_in_google_calendar(doc, method=None):
	"""
	Insert Events in Google Calendar if sync_with_google_calendar is checked.
	"""
	if (
		not frappe.db.exists("Google Calendar", {"name": doc.google_calendar})
		or doc.flags.pulled_from_google_calendar
		or not doc.sync_with_google_calendar
	):
		return

	google_calendar, account = get_google_calendar_object(doc.google_calendar)

	if not account.push_to_google_calendar:
		return

	event = {
		"summary": doc.subject,
		"description": doc.description,
		"sync_with_google_calendar": 1,
		"recurrence": [doc.rrule] if doc.rrule else None,
	}
	event.update(
		format_date_according_to_google_calendar(
			doc.all_day, get_datetime(doc.starts_on), get_datetime(doc.ends_on)
		)
	)

	try:
		event = (
			google_calendar.events()
			.insert(
				calendarId=doc.google_calendar_id,
				body=event,
				sendUpdates="all",
			)
			.execute()
		)
		doc.db_set("google_calendar_event_id", event.get("id"), update_modified=False)
		frappe.publish_realtime(
			"event_synced",
			{"message": _("Event Synced with Google Calendar.")},
			user=frappe.session.user,
		)
	except HttpError as err:
		frappe.msgprint(f'{_("Google Error")}: {json.loads(err.content)["error"]["message"]}')
		frappe.throw(
			_("Google Calendar - Could not insert event in Google Calendar {0}, error code {1}.").format(
				account.name, err.resp.status
			)
		)


def update_event_in_google_calendar(doc, method=None):
	"""
	Updates Events in Google Calendar if any existing event is modified in Frappe Calendar
	"""
	# Workaround to avoid triggering updation when Event is being inserted since
	# creation and modified are same when inserting doc
	if (
		not frappe.db.exists("Google Calendar", {"name": doc.google_calendar})
		or doc.modified == doc.creation
		or not doc.sync_with_google_calendar
		or doc.flags.pulled_from_google_calendar
	):
		return

	if doc.sync_with_google_calendar and not doc.google_calendar_event_id:
		# If sync_with_google_calendar is checked later, then insert the event rather than updating it.
		insert_event_in_google_calendar(doc)
		return

	google_calendar, account = get_google_calendar_object(doc.google_calendar)

	if not account.push_to_google_calendar:
		return

	try:
		event = (
			google_calendar.events()
			.get(calendarId=doc.google_calendar_id, eventId=doc.google_calendar_event_id)
			.execute()
		)
		event["summary"] = doc.subject
		event["description"] = doc.description
		event["recurrence"] = [doc.rrule] if doc.rrule else None
		event["status"] = (
			"cancelled" if doc.event_type == "Cancelled" or doc.status == "Closed" else event.get("status")
		)
		event.update(
			format_date_according_to_google_calendar(
				doc.all_day, get_datetime(doc.starts_on), get_datetime(doc.ends_on)
			)
		)

		google_calendar.events().update(
			calendarId=doc.google_calendar_id,
			eventId=doc.google_calendar_event_id,
			body=event,
			sendUpdates="all",
		).execute()
		frappe.publish_realtime(
			"event_synced",
			{"message": _("Event Synced with Google Calendar.")},
			user=frappe.session.user,
		)
	except HttpError as err:
		frappe.msgprint(f'{_("Google Error")}: {json.loads(err.content)["error"]["message"]}')
		frappe.throw(
			_("Google Calendar - Could not update Event {0} in Google Calendar, error code {1}.").format(
				doc.name, err.resp.status
			)
		)


def delete_event_in_google_calendar(doc, method=None):
	"""
	Delete Events from Google Calendar if Frappe Event is deleted.
	"""

	if (
		not frappe.db.exists("Google Calendar", {"name": doc.google_calendar})
		or doc.flags.pulled_from_google_calendar
		or not doc.google_calendar_event_id
	):
		return

	google_calendar, account = get_google_calendar_object(doc.google_calendar)

	if not account.push_to_google_calendar:
		return

	try:
		event = (
			google_calendar.events()
			.get(calendarId=doc.google_calendar_id, eventId=doc.google_calendar_event_id)
			.execute()
		)
		event["recurrence"] = None
		event["status"] = "cancelled"

		google_calendar.events().update(
			calendarId=doc.google_calendar_id, eventId=doc.google_calendar_event_id, body=event
		).execute()
	except HttpError as err:
		frappe.msgprint(f'{_("Google Error")}: {json.loads(err.content)["error"]["message"]}')
		frappe.msgprint(
			_("Google Calendar - Could not delete Event {0} from Google Calendar, error code {1}.").format(
				doc.name, err.resp.status
			)
		)


@frappe.whitelist(allow_guest=True)
def get_prepared_events(
	start, end, limit_start=None, limit_page_length=None, merge_recurrences=False
):
	roles = frappe.get_roles(frappe.session.user)
	roles_string = ", ".join(['"%s"'] * len(roles)) % tuple(roles)
	events = get_events(
		start,
		end,
		filters={"published": 1},
		additional_condition=f" AND (`tabEvent`.visible_for='All' OR (`tabEvent`.visible_for='Role' AND `tabEvent`.role in ({roles_string})))",
		field_map={
			"route": "route",
			"published": "published",
			"image": "image",
			"visible_for": "visible_for",
			"role": "role",
		},
		limit_start=limit_start,
		limit_page_length=limit_page_length,
		ignore_permissions=True,
	)

	result = []
	for event in events:
		for field in FIELD_MAP:
			event.update({field: event.get(FIELD_MAP[field])})

		if (
			merge_recurrences
			and event.get("repeat_this_event")
			and any(r["name"] == event.get("name") for r in result)
		):
			existing_event = next(r for r in result if r["name"] == event.get("name"))
			if "recurrences" in existing_event:
				existing_event["recurrences"].append(event)
			else:
				existing_event["recurrences"] = [event]
		else:
			result.append(frappe._dict(event))

	return result
