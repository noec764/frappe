import frappe


def execute():
	events = frappe.get_all(
		"Event", filters={"google_calendar": ("is", "set")}, fields=["owner", "name", "google_calendar"]
	)
	google_calendars = {
		c.name: c.user for c in frappe.get_all("Google Calendar", fields=["name", "user"])
	}
	for event in events:
		if event.owner != google_calendars.get(event.google_calendar):
			frappe.db.set_value(
				"Event",
				event.name,
				"owner",
				google_calendars.get(event.google_calendar),
				update_modified=False,
			)
