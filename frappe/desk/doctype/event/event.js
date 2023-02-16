// Copyright (c) 2019, Dokos SAS and Contributors
// MIT License. See license.txt
frappe.provide("frappe.desk");

frappe.ui.form.on("Event", {
	setup() {
		frappe.realtime.off("event_synced");
		frappe.realtime.on("event_synced", (data) => {
			frappe.show_alert({ message: data.message, indicator: "green" });
		});
	},
	onload: function (frm) {
		frm.set_query("google_calendar", function () {
			return {
				filters: {
					user: ["in", [frappe.session.user, null]],
					reference_document: frm.doctype,
				},
			};
		});
	},
	refresh: function (frm) {
		frm.trigger("add_repeat_text");
	},
	repeat_this_event: function (frm) {
		if (frm.doc.repeat_this_event === 1) {
			new frappe.CalendarRecurrence({ frm: frm, show: true });
		}
	},
	add_repeat_text(frm) {
		if (frm.doc.rrule) {
			new frappe.CalendarRecurrence({ frm: frm, show: false });
		}
	},
	sync_with_google_calendar(frm) {
		frappe.db.get_value("Google Calendar", { user: frappe.session.user }, "name", (r) => {
			r && r.name && frm.set_value("google_calendar", r.name);
		});
	},
});

frappe.tour["Event"] = [
	{
		fieldname: "subject",
		title: __("Event subject"),
		description: __(
			"This is the topic/purpose of your event. This information allows you to know what your event is about."
		),
	},
	{
		fieldname: "starts_on",
		title: __("Starts on"),
		description: __("Choose the start date of the event. Select the day and time."),
	},
	{
		fieldname: "event_category",
		title: __("Event category"),
		description: __(
			"Define the type of event: a meeting, an event (e.g. trade show), a call, an email sent."
		),
	},
	{
		fieldname: "ends_on",
		title: __("Ends on"),
		description: __("Choose the end date of the event. Select the day and time."),
	},
	{
		fieldname: "event_type",
		title: __("Event type"),
		description: __(
			"Define if your event is private or public. If your event is cancelled you can indicate it here."
		),
	},
	{
		fieldname: "status",
		title: __("Status"),
		description: __(
			"Indicate the status of the event. The event can be 'Confirmed', 'Unconfirmed', 'Open', 'Cancelled', 'Closed'."
		),
	},
	{
		fieldname: "all_day",
		title: __("All day"),
		description: __("If the box is checked it means that the event takes place all day."),
	},
	{
		fieldname: "repeat_this_event",
		title: __("Repeat this event"),
		description: __(
			"If the box is checked, a pop-up will open asking you to choose the recurrence of the event. Specify the frequency, until when the event should be repeated and the frequency interval."
		),
	},
	{
		fieldname: "sync_with_google_calendar",
		title: __("Synchronize with Google Calendar"),
		description: __(
			"If the box is checked then the event will be synchronized to your Google calendar. Note: You will need to have your Google calendar settings set up correctly."
		),
	},
	{
		fieldname: "event_participants",
		title: __("Event particpants"),
		description: __("Select all participants who will be attending the event."),
	},
	{
		fieldname: "description",
		title: __("Description"),
		description: __(
			"In this section, fill in all the descriptive information about the event."
		),
	},
];
