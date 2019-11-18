# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import requests
import googleapiclient.discovery
import google.oauth2.credentials

from frappe import _
from frappe.model.document import Document
from frappe.utils import get_request_site_address
from frappe.desk.calendar import get_rrule
from googleapiclient.errors import HttpError
from frappe.utils import add_days, get_datetime, get_weekdays, now_datetime, add_to_date, get_time_zone
from dateutil import parser
from datetime import datetime, timedelta
from six.moves.urllib.parse import quote
from frappe.integrations.doctype.google_settings.google_settings import get_auth_url

SCOPES = "https://www.googleapis.com/auth/calendar"

class GoogleCalendar(Document):

	def validate(self):
		google_settings = frappe.get_single("Google Settings")
		if not google_settings.enable:
			frappe.throw(_("Enable Google API in Google Settings."))

		if not google_settings.client_id or not google_settings.client_secret:
			frappe.throw(_("Enter Client Id and Client Secret in Google Settings."))

		return google_settings

	def get_access_token(self):
		google_settings = self.validate()

		if not self.refresh_token:
			button_label = frappe.bold(_("Allow Google Calendar Access"))
			raise frappe.ValidationError(_("Click on {0} to generate Refresh Token.").format(button_label))

		data = {
			"client_id": google_settings.client_id,
			"client_secret": google_settings.get_password(fieldname="client_secret", raise_exception=False),
			"refresh_token": self.refresh_token,
			"grant_type": "refresh_token",
			"scope": SCOPES
		}

		try:
			r = requests.post(get_auth_url(), data=data).json()
		except requests.exceptions.HTTPError:
			button_label = frappe.bold(_("Allow Google Calendar Access"))
			frappe.throw(_("Something went wrong during the token generation. Click on {0} to generate a new one.").format(button_label))

		return r.get("access_token")

@frappe.whitelist()
def authorize_access(g_calendar, reauthorize=None):
	"""
		If no Authorization code get it from Google and then request for Refresh Token.
		Google Calendar Name is set to flags to set_value after Authorization Code is obtained.
	"""
	google_settings = frappe.get_doc("Google Settings")
	google_calendar = frappe.get_doc("Google Calendar", g_calendar)

	redirect_uri = get_request_site_address(True) + "?cmd=frappe.integrations.doctype.google_calendar.google_calendar.google_callback"

	if not google_calendar.authorization_code or reauthorize:
		frappe.cache().hset("google_calendar", "google_calendar", google_calendar.name)
		return get_authentication_url(client_id=google_settings.client_id, redirect_uri=redirect_uri)
	else:
		try:
			data = {
				"code": google_calendar.get_password(fieldname="authorization_code", raise_exception=False),
				"client_id": google_settings.client_id,
				"client_secret": google_settings.get_password(fieldname="client_secret", raise_exception=False),
				"redirect_uri": redirect_uri,
				"grant_type": "authorization_code"
			}
			r = requests.post(get_auth_url(), data=data).json()

			if "refresh_token" in r:
				frappe.db.set_value("Google Calendar", google_calendar.name, "refresh_token", r.get("refresh_token"))
				frappe.db.set_value("Google Calendar", google_calendar.name, "next_sync_token", None)
				frappe.db.commit()

			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = "/desk#Form/{0}/{1}".format(quote("Google Calendar"), quote(google_calendar.name))

			frappe.msgprint(_("Google Calendar has been configured."))
		except Exception as e:
			frappe.throw(e)

def get_authentication_url(client_id=None, redirect_uri=None):
	return {
		"url": "https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&response_type=code&prompt=consent&client_id={}&include_granted_scopes=true&scope={}&redirect_uri={}".format(client_id, SCOPES, redirect_uri)
	}

@frappe.whitelist()
def google_callback(code=None):
	"""
		Authorization code is sent to callback as per the API configuration
	"""
	google_calendar = frappe.cache().hget("google_calendar", "google_calendar")
	frappe.db.set_value("Google Calendar", google_calendar, "authorization_code", code)
	frappe.db.commit()

	authorize_access(google_calendar)

@frappe.whitelist()
def sync(g_calendar=None):
	filters = {"enable": 1}

	if g_calendar:
		filters.update({"name": g_calendar})

	google_calendars = frappe.get_list("Google Calendar", filters=filters)

	for g in google_calendars:
		return sync_events_from_google_calendar(g.name)

def get_google_calendar_object(g_calendar):
	"""
		Returns an object of Google Calendar along with Google Calendar doc.
	"""
	google_settings = frappe.get_doc("Google Settings")
	account = frappe.get_doc("Google Calendar", g_calendar)

	credentials_dict = {
		"token": account.get_access_token(),
		"refresh_token": account.refresh_token,
		"token_uri": get_auth_url(),
		"client_id": google_settings.client_id,
		"client_secret": google_settings.get_password(fieldname="client_secret", raise_exception=False),
		"scopes": "https://www.googleapis.com/auth/calendar/v3"
	}

	credentials = google.oauth2.credentials.Credentials(**credentials_dict)
	google_calendar = googleapiclient.discovery.build("calendar", "v3", credentials=credentials)

	check_google_calendar(account, google_calendar)

	account.load_from_db()
	return google_calendar, account

def check_google_calendar(account, google_calendar):
	"""
		Checks if Google Calendar is present with the specified name.
		If not, creates one.
	"""
	account.load_from_db()
	try:
		if account.google_calendar_id:
			google_calendar.calendars().get(calendarId=account.google_calendar_id).execute()
		else:
			# If no Calendar ID create a new Calendar
			calendar = {
				"summary": account.calendar_name,
				"timeZone": frappe.db.get_single_value("System Settings", "time_zone")
			}
			created_calendar = google_calendar.calendars().insert(body=calendar).execute()
			frappe.db.set_value("Google Calendar", account.name, "google_calendar_id", created_calendar.get("id"))
			frappe.db.commit()
	except HttpError as err:
		frappe.throw(_("Google Calendar - Could not create Calendar for {0}, error code {1}.").format(account.name, err.resp.status))

def sync_events_from_google_calendar(g_calendar, method=None, page_length=10):
	"""
		Syncs Events from Google Calendar in Framework Calendar.
		Google Calendar returns nextSyncToken when all the events in Google Calendar are fetched.
		nextSyncToken is returned at the very last page
		https://developers.google.com/calendar/v3/sync
	"""
	google_calendar, account = get_google_calendar_object(g_calendar)

	if not account.pull_from_google_calendar:
		return

	results = []
	nextPageToken = None
	while True:
		try:
			# API Response listed at EOF
			sync_token = account.next_sync_token or None
			events = google_calendar.events().list(calendarId=account.google_calendar_id, maxResults=page_length,
				singleEvents=False, showDeleted=True, syncToken=sync_token, pageToken=nextPageToken).execute()
		except HttpError as err:
			frappe.throw(_("Google Calendar - Could not fetch event from Google Calendar, error code {0}.").format(err.resp.status))

		for event in events.get("items", []):
			results.append(event)

		if not events.get("nextPageToken"):
			if events.get("nextSyncToken"):
				frappe.db.set_value("Google Calendar", account.name, "next_sync_token", events.get("nextSyncToken"))
				frappe.db.commit()
			break
		else:
			nextPageToken = events.get("nextPageToken")

	for idx, event in enumerate(results):
		frappe.publish_realtime("import_google_calendar", dict(progress=idx+1, total=len(results)), user=frappe.session.user)

		# If Google Calendar Event if confirmed, then create an Event
		if event.get("status") == "confirmed":
			recurrence = None
			if event.get("recurrence"):
				try:
					recurrence = event.get("recurrence")[0]
				except IndexError:
					pass

			if not frappe.db.exists(account.reference_document, {"google_calendar_event_id": event.get("id")}):
				call_calendar_hook("pull_insert", **{"account": account, "event": event, "recurrence": recurrence})
			else:
				call_calendar_hook("pull_update", **{"account": account, "event": event, "recurrence": recurrence})
		elif event.get("status") == "cancelled":
			call_calendar_hook("pull_delete", **{"account": account, "event": event})
		else:
			pass

	if not results:
		return _("No Google Calendar Event to sync.")
	elif len(results) == 1:
		return _("1 Google Calendar Event synced.")
	else:
		return _("{0} Google Calendar Events synced.").format(len(results))

def call_calendar_hook(hook, **kwargs):
	reference_document = kwargs.get("account", {}).get("reference_document")
	if reference_document:
		hook_method = frappe.get_hooks("gcalendar_integrations").get(reference_document, {}).get(hook, [])[-1]
		if hook_method:
			method = frappe.get_attr(hook_method)
			frappe.call(method, **kwargs)

def insert_event_to_calendar(account, event, recurrence=None):
	"""
		Inserts event in Frappe Calendar during Sync
	"""
	calendar_event = {
		"doctype": "Event",
		"subject": event.get("summary"),
		"description": event.get("description"),
		"sync_with_google_calendar": 1,
		"google_calendar": account.name,
		"google_calendar_id": account.google_calendar_id,
		"google_calendar_event_id": event.get("id"),
		"pulled_from_google_calendar": 1,
		"rrule": recurrence
	}
	frappe.get_doc(calendar_event).insert(ignore_permissions=True)

def update_event_in_calendar(account, event, recurrence=None):
	"""
		Updates Event in Frappe Calendar if any existing Google Calendar Event is updated
	"""
	calendar_event = frappe.get_doc("Event", {"google_calendar_event_id": event.get("id")})
	calendar_event.subject = event.get("summary")
	calendar_event.description = event.get("description")
	calendar_event.rrule = recurrence
	calendar_event.save(ignore_permissions=True)

def close_event_in_calendar(account, event):
	# If any synced Google Calendar Event is cancelled, then close the Event
	frappe.db.set_value("Event", {"google_calendar_id": account.google_calendar_id, "google_calendar_event_id": event.get("id")}, "status", "Closed")
	frappe.get_doc({
		"doctype": "Comment",
		"comment_type": "Info",
		"reference_doctype": "Event",
		"reference_name": frappe.db.get_value("Event", {"google_calendar_id": account.google_calendar_id, "google_calendar_event_id": event.get("id")}, "name"),
		"content": " - Event deleted from Google Calendar.",
	}).insert(ignore_permissions=True)

def insert_event_in_google_calendar(doc, method=None):
	"""
		Insert Events in Google Calendar if sync_with_google_calendar is checked.
	"""
	if not frappe.db.exists("Google Calendar", {"name": doc.google_calendar}) or doc.pulled_from_google_calendar \
		or not doc.sync_with_google_calendar:
		return

	google_calendar, account = get_google_calendar_object(doc.google_calendar)

	if not account.push_to_google_calendar:
		return

	event = {
		"summary": doc.subject,
		"description": doc.description,
		"sync_with_google_calendar": 1
	}
	event.update(format_date_according_to_google_calendar(doc.all_day, get_datetime(doc.starts_on), get_datetime(doc.ends_on)))

	if doc.repeat_on:
		event.update({"recurrence": [get_rrule(doc)]})

	try:
		event = google_calendar.events().insert(calendarId=doc.google_calendar_id, body=event).execute()
		frappe.db.set_value("Event", doc.name, "google_calendar_event_id", event.get("id"), update_modified=False)
		frappe.msgprint(_("Event Synced with Google Calendar."))
	except HttpError as err:
		frappe.throw(_("Google Calendar - Could not insert event in Google Calendar {0}, error code {1}.").format(account.name, err.resp.status))

def update_event_in_google_calendar(doc, method=None):
	"""
		Updates Events in Google Calendar if any existing event is modified in Frappe Calendar
	"""
	# Workaround to avoid triggering updation when Event is being inserted since
	# creation and modified are same when inserting doc
	if not frappe.db.exists("Google Calendar", {"name": doc.google_calendar}) or doc.modified == doc.creation \
		or not doc.sync_with_google_calendar:
		return

	if doc.sync_with_google_calendar and not doc.google_calendar_event_id:
		# If sync_with_google_calendar is checked later, then insert the event rather than updating it.
		insert_event_in_google_calendar(doc)
		return

	google_calendar, account = get_google_calendar_object(doc.google_calendar)

	if not account.push_to_google_calendar:
		return

	try:
		event = google_calendar.events().get(calendarId=doc.google_calendar_id, eventId=doc.google_calendar_event_id).execute()
		event["summary"] = doc.subject
		event["description"] = doc.description
		event["recurrence"] = [get_rrule(doc)]
		event["status"] = "cancelled" if doc.event_type == "Cancelled" or doc.status == "Closed" else event.get("status")
		event.update(format_date_according_to_google_calendar(doc.all_day, get_datetime(doc.starts_on), get_datetime(doc.ends_on)))

		google_calendar.events().update(calendarId=doc.google_calendar_id, eventId=doc.google_calendar_event_id, body=event).execute()
		frappe.msgprint(_("Event Synced with Google Calendar."))
	except HttpError as err:
		frappe.throw(_("Google Calendar - Could not update Event {0} in Google Calendar, error code {1}.").format(doc.name, err.resp.status))

def delete_event_from_google_calendar(doc, method=None):
	"""
		Delete Events from Google Calendar if Frappe Event is deleted.
	"""

	if not frappe.db.exists("Google Calendar", {"name": doc.google_calendar}):
		return

	google_calendar, account = get_google_calendar_object(doc.google_calendar)

	if not account.push_to_google_calendar:
		return

	try:
		event = google_calendar.events().get(calendarId=doc.google_calendar_id, eventId=doc.google_calendar_event_id).execute()
		event["recurrence"] = None
		event["status"] = "cancelled"

		google_calendar.events().update(calendarId=doc.google_calendar_id, eventId=doc.google_calendar_event_id, body=event).execute()
	except HttpError as err:
		frappe.msgprint(_("Google Calendar - Could not delete Event {0} from Google Calendar, error code {1}.").format(doc.name, err.resp.status))

def format_date_according_to_google_calendar(all_day, starts_on, ends_on=None):
	if not ends_on:
		ends_on = starts_on + timedelta(minutes=10)

	date_format = {
		"start": {
			"dateTime": starts_on.isoformat(),
			"timeZone": get_time_zone(),
			},
		"end": {
			"dateTime": ends_on.isoformat(),
			"timeZone": get_time_zone(),
		}
	}

	if all_day:
		# If all_day event, Google Calendar takes date as a parameter and not dateTime
		date_format["start"].pop("dateTime")
		date_format["end"].pop("dateTime")

		date_format["start"].update({"date": starts_on.date().isoformat()})
		date_format["end"].update({"date": ends_on.date().isoformat()})

	return date_format

"""API Response
	{
		'kind': 'calendar#events',
		'etag': '"etag"',
		'summary': 'Test Calendar',
		'updated': '2019-07-25T06:09:34.681Z',
		'timeZone': 'Asia/Kolkata',
		'accessRole': 'owner',
		'defaultReminders': [],
		'nextSyncToken': 'token',
		'items': [
			{
				'kind': 'calendar#event',
				'etag': '"etag"',
				'id': 'id',
				'status': 'confirmed' or 'cancelled',
				'htmlLink': 'link',
				'created': '2019-07-25T06:08:21.000Z',
				'updated': '2019-07-25T06:09:34.681Z',
				'summary': 'asdf',
				'creator': {
					'email': 'email'
				},
				'organizer': {
					'email': 'email',
					'displayName': 'Test Calendar',
					'self': True
				},
				'start': {
					'dateTime': '2019-07-27T12:00:00+05:30', (if all day event the its 'date' instead of 'dateTime')
					'timeZone': 'Asia/Kolkata'
				},
				'end': {
					'dateTime': '2019-07-27T13:00:00+05:30', (if all day event the its 'date' instead of 'dateTime')
					'timeZone': 'Asia/Kolkata'
				},
				'recurrence': *recurrence,
				'iCalUID': 'uid',
				'sequence': 1,
				'reminders': {
					'useDefault': True
				}
			}
		]
	}
	*recurrence
		- Daily Event: ['RRULE:FREQ=DAILY']
		- Weekly Event: ['RRULE:FREQ=WEEKLY;BYDAY=MO,TU,TH']
		- Monthly Event: ['RRULE:FREQ=MONTHLY;BYDAY=4TH']
			- BYDAY: -2, -1, 1, 2, 3, 4 with weekdays (-2 edge case for April 2017 had 6 weeks in a month)
		- Yearly Event: ['RRULE:FREQ=YEARLY;']
		- Custom Event: ['RRULE:FREQ=WEEKLY;WKST=SU;UNTIL=20191028;BYDAY=MO,WE']"""
