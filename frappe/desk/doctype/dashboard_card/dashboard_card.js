// Copyright (c) 2019, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.provide('frappe.dashboards.card_sources');

frappe.ui.form.on('Dashboard Card', {
	source(frm) {
		frm.trigger("setup_card");
	},
	setup_card(frm) {
		if (frm.doc.card_type==='Preregistered' && frm.doc.source) {
			frappe.xcall('frappe.desk.doctype.dashboard_card_source.dashboard_card_source.get_config', {name: frm.doc.source})
				.then(config => {
					frappe.dom.eval(config);
					frm.set_value("icon", frappe.dashboards.card_sources[frm.doc.source].icon);
					frm.set_value("color", frappe.dashboards.card_sources[frm.doc.source].color);
					frm.set_value("timespan", frappe.dashboards.card_sources[frm.doc.source].timespan);
				});
		}
	}
});
