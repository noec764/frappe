// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt
frappe.provide("frappe.desk");

frappe.ui.form.on("Event", {
	setup() {
		frappe.realtime.on('event_synced', (data) => {
			frappe.show_alert({message: data.message, indicator: 'green'});
		})
	},
	onload: function(frm) {
		frm.set_query('reference_doctype', "event_participants", function() {
			return {
				"filters": {
					"issingle": 0,
				}
			};
		});
		frm.set_query('google_calendar', function() {
			return {
				filters: {
					"owner": frappe.session.user
				}
			};
		});
	},
	refresh: function(frm) {
		if(frm.doc.event_participants) {
			frm.doc.event_participants.forEach(value => {
				frm.add_custom_button(__(value.reference_docname), function() {
					frappe.set_route("Form", value.reference_doctype, value.reference_docname);
				}, __("Participants"));
			})
		}

		frm.page.set_inner_btn_group_as_primary(__("Add Participants"));

		frm.add_custom_button(__('Add Contacts'), function() {
			new frappe.desk.eventParticipants(frm, "Contact");
		}, __("Add Participants"));

		frm.trigger('add_repeat_text')
	},
	repeat_this_event: function(frm) {
		if(frm.doc.repeat_this_event === 1) {
			new frappe.CalendarRecurrence(frm, true);
		}
	},
	add_repeat_text(frm) {
		if (frm.doc.rrule) {
			new frappe.CalendarRecurrence(frm, false);
		}
	},
	sync_with_google_calendar(frm) {
		frappe.db.get_value("Google Calendar", {user: frappe.session.user}, "name", r => {
			r&&r.name&&frm.set_value("google_calendar", r.name)
		})
	}
});

frappe.ui.form.on("Event Participants", {
	event_participants_remove: function(frm, cdt, cdn) {
		if (frm.doc.event_participants.length){
			frappe.call({
				type: "POST",
				method: "frappe.desk.doctype.event.event.delete_communication",
				args: {
					"event": frm.doc,
					"reference_doctype": cdt,
					"reference_docname": cdn
				},
				freeze: true,
				callback: function(r) {
					if(r.exc) {
						frappe.show_alert({
							message: __("{0}", [r.exc]),
							indicator: 'orange'
						});
					}
				}
			});
		}
	}
});

frappe.desk.eventParticipants = class eventParticipants {
	constructor(frm, doctype) {
		this.frm = frm;
		this.doctype = doctype;
		this.make();
	}

	make() {
		let me = this;

		let table = me.frm.get_field("event_participants").grid;
		new frappe.ui.form.LinkSelector({
			doctype: me.doctype,
			dynamic_link_field: "reference_doctype",
			dynamic_link_reference: me.doctype,
			fieldname: "reference_docname",
			target: table,
			txt: ""
		});
	}
};
