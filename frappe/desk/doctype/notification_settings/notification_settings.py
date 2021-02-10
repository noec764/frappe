# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class NotificationSettings(Document):
	def on_update(self):
		from frappe.desk.notifications import clear_notification_config
		clear_notification_config(frappe.session.user)


def is_notifications_enabled(user):
	enabled = frappe.db.get_value('Notification Settings', user, 'enabled')
	if enabled is None:
		return True
	return enabled

def is_email_notifications_enabled(user):
	enabled = frappe.db.get_value('Notification Settings', user, 'enable_email_notifications')
	if enabled is None:
		return True
	return enabled

def is_email_notifications_enabled_for_type(user, notification_type):
	if not is_email_notifications_enabled(user):
		return False

	if notification_type == 'Alert':
		return False

	fieldname = 'enable_email_' + frappe.scrub(notification_type)
	enabled = frappe.db.get_value('Notification Settings', user, fieldname)
	if enabled is None:
		return True
	return enabled

def create_notification_settings(user):
	if not frappe.db.exists("Notification Settings", user):
		_doc = frappe.new_doc('Notification Settings')
		_doc.name = user
		_doc.insert(ignore_permissions=True)


@frappe.whitelist()
def get_subscribed_documents():
	if not frappe.session.user:
		return []

	try:
		if frappe.db.exists('Notification Settings', frappe.session.user):
			doc = frappe.get_doc('Notification Settings', frappe.session.user)
			return [item.document for item in doc.subscribed_documents]
	# Notification Settings is fetched even before sync doctype is called
	# but it will throw an ImportError, we can ignore it in migrate
	except ImportError:
		pass

	return []


def get_permission_query_conditions(user):
	if not user: user = frappe.session.user

	if user == 'Administrator':
		return

	roles = frappe.get_roles(user)
	if "System Manager" in roles:
		return '''(`tabNotification Settings`.name != 'Administrator')'''

	return '''(`tabNotification Settings`.name = '{user}')'''.format(user=user)

@frappe.whitelist()
def set_seen_value(value, user):
	frappe.db.set_value('Notification Settings', user, 'seen', value, update_modified=False)

@frappe.whitelist()
def get_calendar_options():
	return [x for x in frappe.get_hooks('calendars')]