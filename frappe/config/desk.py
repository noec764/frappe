from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Tools"),
			"icon": "octicon octicon-briefcase",
			"items": [
				{
					"type": "doctype",
					"name": "ToDo",
					"label": _("To Do"),
					"description": _("Documents assigned to you and by you."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Event",
					"label": _("Calendar"),
					"link": "List/Event/Calendar",
					"description": _("Event and other calendars."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Note",
					"description": _("Private and public Notes."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "File",
					"label": _("Files"),
				},
				{
					"type": "page",
					"label": _("Chat"),
					"name": "chat",
					"description": _("Chat messages and other notifications."),
					"data_doctype": "Communication"
				},
				{
					"type": "page",
					"label": _("Activity"),
					"name": "activity",
					"description": _("Activity log of all users."),
				},
			]
		},
		{
			'label': _('Email'),
			'items': [
				{
					"type": "doctype",
					"name": "Newsletter",
					"description": _("Newsletters to contacts, leads."),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Email Group",
					"description": _("Email Group List"),
				},
			]
		},
		{
			'label': _('Dashboard'),
			'items': [
				{
					"type": "doctype",
					"name": "Dashboard Chart",
					"description": _("Setup new dashboard charts")
				},
				{
					"type": "doctype",
					"name": "Dashboard Card",
					"description": _("Setup new dashboard cards"),
				},
				{
					"type": "doctype",
					"name": "Dashboard Calendar",
					"description": _("Setup new dashboard calendars"),
				}
			]
		}
	]
