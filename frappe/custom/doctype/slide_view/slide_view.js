// Copyright (c) 2021, Dokos SAS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Slide View', {
	refresh: function(frm) {
		// frm.page.add_inner_button(__("Go to Slide Viewer"), () => {
		// 	frappe.set_route('slide-viewer', frm.doc.route)
		// });

		frm.page.set_secondary_action(__("Go to Slide Viewer"), () => {
			frappe.set_route('slide-viewer', frm.doc.route)
		}, 'view', __("Go to Slide Viewer"));

		// frm.page.add_action_item(__("Go to Slide Viewer"), () => {
		// 	frappe.set_route('slide-viewer', frm.doc.route)
		// }, false)

		// frm.page.add_menu_item(__("Go to Slide Viewer"), () => {
		// 	frappe.set_route('slide-viewer', frm.doc.route)
		// }, false, undefined)

		// if (frm.doc.route) {
		// 	frm.add_web_link(`/app/slide-viewer/${frm.doc.route}`, __("Go to Slide Viewer"));
		// }
	}
});
