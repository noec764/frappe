// Copyright (c) 2018, DOKOS and contributors
// For license information, please see license.txt

frappe.ui.form.on('GCalendar Account', {
	refresh: function(frm) {
		frm.trigger("set_rqd_fields");
	},
	new_calendar: function(frm) {
		frm.trigger("set_rqd_fields");
	},
	set_rqd_fields: function(frm) {
		frm.toggle_reqd("calendar_name", !frm.doc.new_calendar);
		frm.set_df_property("calendar_name", "read_only", frm.doc.new_calendar ? 0 : 1);

		frm.toggle_reqd("gcalendar_id", frm.doc.new_calendar);
		frm.set_df_property("gcalendar_id", "read_only", frm.doc.new_calendar ? 1 : 0);
	},
	allow_google_access: function(frm) {
		frappe.call({
			method: "frappe.integrations.doctype.gcalendar_settings.gcalendar_settings.google_callback",
			args: {
				'account': frm.doc.name
			},
			callback: function(r) {
				if(!r.exc) {
					frm.save();
					w = window.open(r.message.url);

					if(!w) {
						frappe.msgprint(__("Please enable pop-ups in your browser"))
					}				
				}
			}
		});
	}
});
