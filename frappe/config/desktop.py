from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
	return [
		{
			"module_name": "Desk",
			"category": "Administration",
			"label": _("Tools"),
			"color": "#ffcb61",
			"reverse": 1,
			"icon": "fas fa-toolbox",
			"type": "module",
			"description": "Todos, notes, calendar and newsletter."
		},
		{
			"module_name": "Settings",
			"category": "Administration",
			"label": _("Settings"),
			"color": "#aec8ff",
			"reverse": 1,
			"icon": "fas fa-tools",
			"type": "module",
			"description": "Data import, printing, email and workflows."
		},
		{
			"module_name": "Automation",
			"category": "Administration",
			"label": _("Automation"),
			"color": "#bdc3c7",
			"reverse": 1,
			"icon": "fas fa-charging-station",
			"type": "module",
			"description": "Auto Repeat, Assignment Rule, Milestone Tracking and Event Streaming."
		},
		{
			"module_name": "Users",
			"category": "Administration",
			"label": _("Users and Permissions"),
			"color": "#00b076",
			"reverse": 1,
			"icon": "fas fa-users-cog",
			"type": "module",
			"description": "Setup roles and permissions for users on documents."
		},
		{
			"module_name": "Customization",
			"category": "Administration",
			"label": _("Customization"),
			"color": "#ff7c61",
			"reverse": 1,
			"icon": "fas fa-sliders-h",
			"type": "module",
			"description": "Customize forms, custom fields, scripts and translations."
		},
		{
			"module_name": "Integrations",
			"category": "Administration",
			"label": _("Integrations"),
			"color": "#35abb7",
			"icon": "fas fa-sync-alt",
			"type": "module",
			"description": "DropBox, Woocomerce, AWS, Shopify and GoCardless."
		},
		{
			"module_name": 'Contacts',
			"category": "Administration",
			"label": _("Contacts"),
			"type": 'module',
			"icon": "fas fa-address-book",
			"color": '#ffaedb',
			"description": "People Contacts and Address Book."
		},


		# Administration
		{
			"module_name": "Core",
			"category": "Administration",
			"_label": _("Developer"),
			"label": "Developer",
			"color": "#aec8ff",
			"icon": "fas fa-laptop-code",
			"type": "module",
			"system_manager": 1,
			"condition": getattr(frappe.local.conf, 'developer_mode', 0),
			"description": "Doctypes, dev tools and logs."
		},

		# Places
		{
			"module_name": "Website",
			"category": "Places",
			"label": _("Website"),
			"_label": _("Website"),
			"color": "#61ffcb",
			"icon": "fas fa-globe",
			"type": "module",
			"hidden": 1,
			"description": "Webpages, webforms, blogs and website theme."
		},
		{
			"module_name": 'dashboard',
			"category": "Places",
			"label": _('Dashboard'),
			"icon": "fas fa-chart-bar",
			"type": "link",
			"link": "#dashboard",
			"color": '#ff61e4',
			'idx': 10
		},
	]
