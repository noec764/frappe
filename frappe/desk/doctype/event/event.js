// Copyright (c) 2019, Dokos SAS and Contributors
// MIT License. See license.txt
frappe.provide("frappe.desk");

frappe.ui.form.on("Event", {
	setup() {
		frappe.realtime.on('event_synced', (data) => {
			frappe.show_alert({message: data.message, indicator: 'green'});
		})
	},
	onload: function(frm) {
		frm.set_query('google_calendar', function() {
			return {
				filters: {
					"user": ['in', [frappe.session.user, null]],
					"reference_document": frm.doctype
				}
			};
		});
	},
	refresh: function(frm) {
		frm.trigger('add_repeat_text')
		frm.trigger('add_item_booking_details')
	},
	repeat_this_event: function(frm) {
		if(frm.doc.repeat_this_event === 1) {
			new frappe.CalendarRecurrence({frm: frm, show: true});
		}
	},
	add_repeat_text(frm) {
		if (frm.doc.rrule) {
			new frappe.CalendarRecurrence({frm: frm, show: false});
		}
	},
	sync_with_google_calendar(frm) {
		frappe.db.get_value("Google Calendar", {user: frappe.session.user}, "name", r => {
			r&&r.name&&frm.set_value("google_calendar", r.name)
		})
	},
	add_item_booking_details(frm) {
		frappe.model.with_doctype("Item Booking", () => {
			frappe.db.get_list('Item Booking', {filters: {event: frm.doc.name}, fields: ["name", "item_name", "color", "starts_on", "status"]}).then(data => {
				if (data.length) {
					const item_booking_section = data.map(d => {
						const $card = $(`
							<div class="item-booking-card" style="background-color: ${d.color || "var(--primary)"}">
								<div class="flex align-items-center">
									<div class="left-title" style="color: ${frappe.ui.color.get_contrast_color(d.color)}">${frappe.datetime.obj_to_user(d.starts_on).replace(new RegExp('[^\.]?' + moment(d.starts_on).format('YYYY') + '.?'), '')}</div>
									<div class="right-body">
										<div class="text-muted">${d.item_name}</div>
										<div class="text-color small">${__(d.status)}</div>
									</div>
								</div>
							</div>
						`)
	
						$card.on("click", () => {
							frappe.set_route("Form", "Item Booking", d.name)
						})
	
						return $card
					})
	
					frm.dashboard.add_section(item_booking_section).removeClass("form-dashboard-section")
				}
			})
		})
	}
});
