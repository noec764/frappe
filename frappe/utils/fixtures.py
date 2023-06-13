# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import os

import frappe
from frappe.core.doctype.data_import.data_import import export_json, import_doc
from frappe.utils.deprecations import deprecation_warning


def sync_fixtures(app=None):
	"""Import, overwrite fixtures from `[app]/fixtures`"""
	if app:
		apps = [app]
	else:
		apps = frappe.get_installed_apps()

	frappe.flags.in_fixtures = True

	for app in apps:
		import_fixtures(app)
		import_custom_scripts(app)

	frappe.flags.in_fixtures = False


def import_fixtures(app):
	fixtures_path = frappe.get_app_path(app, "fixtures")
	if not os.path.exists(fixtures_path):
		return

	fixture_files = os.listdir(fixtures_path)

	for fname in fixture_files:
		if not fname.endswith(".json"):
			continue

		file_path = frappe.get_app_path(app, "fixtures", fname)
		try:
			import_doc(file_path)
		except (ImportError, frappe.DoesNotExistError) as e:
			# fixture syncing for missing doctypes
			print(f"Skipping fixture syncing from the file {fname}. Reason: {e}")


def import_custom_scripts(app):
	"""Import custom scripts from `[app]/fixtures/custom_scripts`"""
	if os.path.exists(frappe.get_app_path(app, "fixtures", "custom_scripts")):
		for fname in os.listdir(frappe.get_app_path(app, "fixtures", "custom_scripts")):
			scripts_folder = frappe.get_app_path(app, "fixtures", "custom_scripts")
			deprecation_warning(
				f"Importing client script {fname} from {scripts_folder} is deprecated and will be removed in version-15. Use client scripts as fixtures directly."
			)
			if fname.endswith(".js"):
				with open(frappe.get_app_path(app, "fixtures", "custom_scripts") + os.path.sep + fname) as f:
					doctype = fname.rsplit(".", 1)[0]
					script = f.read()
					if frappe.db.exists("Client Script", {"dt": doctype}):
						custom_script = frappe.get_doc("Client Script", {"dt": doctype})
						custom_script.script = script
						custom_script.save()
					else:
						frappe.get_doc({"doctype": "Client Script", "dt": doctype, "script": script}).insert()


def export_fixtures(app=None):
	"""Export fixtures as JSON to `[app]/fixtures`"""
	if app:
		apps = [app]
	else:
		apps = frappe.get_installed_apps()
	for app in apps:
		for fixture in frappe.get_hooks("fixtures", app_name=app):
			filters = None
			or_filters = None
			if isinstance(fixture, dict):
				filters = fixture.get("filters")
				or_filters = fixture.get("or_filters")
				fixture = fixture.get("doctype") or fixture.get("dt")
			print(f"Exporting {fixture} app {app} filters {(filters if filters else or_filters)}")
			if not os.path.exists(frappe.get_app_path(app, "fixtures")):
				os.mkdir(frappe.get_app_path(app, "fixtures"))

			export_json(
				fixture,
				frappe.get_app_path(app, "fixtures", frappe.scrub(fixture) + ".json"),
				filters=filters,
				or_filters=or_filters,
				order_by="idx asc, creation asc",
			)
