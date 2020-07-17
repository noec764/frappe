// Copyright (c) 2020, Dokos SAS and Contributors
// See license.txt

import { Calendar } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import interactionPlugin from '@fullcalendar/interaction';

frappe.ready(function() {
	frappe.provide("frappe.events");
	frappe.events.EventsPortalView = new EventsPortalView({
		parent: document.getElementById("events-portal")
	});

});

class EventsPortalView {
	constructor(options) {
		Object.assign(this, options);
		this.show()
	}

	show() {
		frappe.require([
			'/assets/js/moment-bundle.min.js',
			'/assets/js/control.min.js'
		], () => {
			this.build_calendar()
			this.getTimeZone()
		});
	}

	build_calendar() {
		const calendarEl = $('<div>').appendTo(this.parent);
		this.fullcalendar = new Calendar(
			calendarEl[0],
			this.calendar_options()
		)
		this.fullcalendar.render();
	}

	calendar_options() {
		return {
			eventClassNames: "events-calendar",
			initialView: frappe.is_mobile() ? "listDay" : "dayGridMonth",
			headerToolbar: {
				left: frappe.is_mobile() ? 'today' : 'dayGridMonth,timeGridWeek',
				center: "prev,title,next",
				right: frappe.is_mobile() ? "" : "prev,next today",
			},
			weekends: true,
			buttonText: {
				today: __("Today"),
				dayGridMonth: __("Month"),
				timeGridWeek: __("Week")

			},
			plugins: [
				dayGridPlugin,
				timeGridPlugin,
				interactionPlugin,
				listPlugin
			],
			locale: frappe.boot.lang || 'en',
			timeZone: 'UTC',
			events: this.getEvents,
			eventClick: this.eventClick,
			selectable: true,
			allDayContent: __("All Day")
		}
	}

	getEvents(parameters, callback) {
		frappe.call({
			method: "frappe.desk.doctype.event.event.get_prepared_events",
			args: {
				start: moment(parameters.start).format("YYYY-MM-DD"),
				end: moment(parameters.end).format("YYYY-MM-DD"),
			}
		}).then(result => {
			callback(result.message)
		})
	}

	eventClick(event) {
		const dialog = new frappe.ui.Dialog ({
			size: 'large',
			title: __(event.event.title),
			fields: [{
				"fieldtype": "HTML",
				"fieldname": "event_description"
			}]
		});
		const description = event.event.extendedProps.description ? event.event.extendedProps.description : `<div>${__("No description")}</div>`
		dialog.fields_dict.event_description.$wrapper.html(description);
		dialog.show()
	}

	getTimeZone() {
		frappe.call("frappe.core.doctype.system_settings.system_settings.get_timezone")
		.then(r => {
			this.fullcalendar.setOption("timeZone", r.message);
		})
	}

}
