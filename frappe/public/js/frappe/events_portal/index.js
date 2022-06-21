// Copyright (c) 2020, Dokos SAS and Contributors
// See license.txt

frappe.provide("frappe.events")

import { Calendar } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import interactionPlugin from '@fullcalendar/interaction';

//TODO: Adjust calendar start and end time to events + improve style

frappe.events.EventsPortalView = class EventsPortalView {
	constructor(options) {
		Object.assign(this, options);
		this.show()
	}

	show() {
		this.build_calendar()
	}

	set_option(option, value) {
		this.fullCalendar&&this.fullCalendar.setOption(option, value);
	}

	build_calendar() {
		const calendarEl = $('<div></div>').appendTo($(this.parent));
		this.fullcalendar = new Calendar(
			calendarEl[0],
			this.calendar_options()
		)
		this.fullcalendar.render();
	}

	calendar_options() {
		const me = this;
		return {
			eventClassNames: "events-calendar",
			contentHeight: "auto",
			initialView: frappe.is_mobile() ? "listDay" : "dayGridMonth",
			headerToolbar: {
				left: frappe.is_mobile() ? 'today' : 'dayGridMonth,timeGridWeek',
				center: "prev,title,next",
				right: frappe.is_mobile() ? "" : "today",
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
			locale: frappe.get_cookie('preferred_language') || frappe.boot.lang || 'en',
			timeZone: frappe.boot.timeZone || 'UTC',
			events: function(info, callback) {
				return me.getEvents(info, callback)
			},
			eventClick: this.eventClick,
			selectable: true,
			noEventsContent: __("No events to display"),
			allDayContent: function() {
				return __("All Day");
			},
			slotMinTime: '08:00:00',
			slotMaxTime: '20:00:00'
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
			this.prepared_events = result.message || [];

			this.set_min_max_times()

			callback(this.prepared_events)
		})
	}

	set_min_max_times() {
		let minTimes = this.prepared_events.map(event => moment(event.start).format("HH:mm:ss")).sort()
		minTimes.length && this.set_option("slotMinTime", minTimes[0])
		let maxTimes =  this.prepared_events.map(event => moment(event.end).format("HH:mm:ss")).sort().reverse()
		maxTimes.length && this.set_option("slotMaxTime", maxTimes[0])
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

		event.event.extendedProps.route&&dialog.set_primary_action(__("See details"), () => {
			window.location.href = event.event.extendedProps.route;
		})
		dialog.fields_dict.event_description.$wrapper.html(event_details(event));
		dialog.show()
	}
}


const event_details = (event) => {
	const image = event.event.extendedProps.image ? `<div style="background: url(${event.event.extendedProps.image}) center/contain no-repeat;min-width: 10%;"></div>` : ""
	const description = event.event.extendedProps.description ? event.event.extendedProps.description : `<div>${__("No description")}</div>`;
	return `
		<div class="calendar-event">
			<div class="card-body flex justify-content-start">
				${image}
				<div class=${event.event.extendedProps.image ? "pl-2" : ""}>
					<h5 class="card-title">${event.event.extendedProps.subject}</h5>
					${description}
				</div>
			</div>
		</div>
	`
}
