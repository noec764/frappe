// Copyright (c) 2021, Dokos SAS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cover Page', {
	refresh: function(frm) {
		frm.get_field('cover_page').df.options = {
			restrictions: {
				allowed_file_types: ['application/pdf']
			}
		};
	}
});
