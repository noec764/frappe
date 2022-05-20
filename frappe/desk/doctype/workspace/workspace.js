// Copyright (c) 2020, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Workspace', {
	setup: function() {
		frappe.meta.get_field('Workspace Link', 'only_for').no_default = true;
	},

	refresh: function(frm) {
		frm.enable_save();
		frm.set_df_property('is_standard', 'read_only', !frappe.boot.developer_mode);
		if (frm.doc.for_user || (frm.doc.public && !frm.has_perm('write') &&
			!frappe.user.has_role('Workspace Manager'))) {
			frm.trigger('disable_form');
		}
	},

	disable_form: function(frm) {
		frm.fields
			.filter(field => field.has_input)
			.forEach(field => {
				frm.set_df_property(field.df.fieldname, "read_only", "1");
			});
		frm.disable_save();
	},

	icon: function(frm) {
		frm.get_field("icon_display").$wrapper.html(
			`<div class="my-2 text-center">${frappe.utils.icon(frm.doc.icon, "sm")}</div>`
		)
	}
});
