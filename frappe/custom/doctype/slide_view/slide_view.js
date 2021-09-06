// Copyright (c) 2021, Dokos SAS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Slide View', {
	refresh: function(frm) {
		frm.trigger('_update_doc_settings_warning')

		if (!frm.doc.__islocal) {
			frm.trigger('_update_secondary_action')
		}
	},

	/** Secondary action is removed when form is changed */
	_update_secondary_action: function(frm) {
		const label = __('Open {0}', [__('Slide View')])
		frm.page.set_secondary_action(label, (x) => {
			frappe.set_route('slide-viewer', frm.doc.route)
		}, 'view', label);
	},

	_update_doc_settings_warning: function(frm) {
		const error_text_doc_settings = frm.get_field('html_invalid_doc_settings');
		if (error_text_doc_settings) {
			const el = error_text_doc_settings.disp_area
			el.innerHTML = frappe.utils.icon('solid-warning') + "&nbsp;" + __("Please note that you will not be able to create or modify any document with this slide view.", null, "Slide View");
			el.style.color = 'var(--red)';
		}
	},

	can_create_doc: function(frm) {
		frm.trigger('_update_doc_settings_warning')
	},

	can_edit_doc: function(frm) {
		frm.trigger('_update_doc_settings_warning')
	},
});
