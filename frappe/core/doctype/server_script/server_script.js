// Copyright (c) 2019, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Server Script', {
	refresh: function(frm) {
		if (frm.doc.script_type != 'Scheduler Event') {
			frm.dashboard.hide();
		}

		if (!frm.is_new()) {
			frm.add_custom_button(__('Compare Versions'), () => {
				new frappe.ui.DiffView("Server Script", "script", frm.doc.name);
			});
		}

		frm.call('get_autocompletion_items')
			.then(r => r.message)
			.then(items => {
				frm.set_df_property('script', 'autocompletions', items);
			});
	}
});
