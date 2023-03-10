frappe.ui.form.ControlDynamicLink = class ControlDynamicLink extends frappe.ui.form.ControlLink {
	get_options() {
		let options = "";
		if (this.df.get_options) {
			options = this.df.get_options(this);
		} else if (this.docname == null && cur_dialog) {
			//for dialog box
			options = cur_dialog.get_value(this.df.options);
		} else if (cur_frm) {
			options = frappe.model.get_value(this.df.parent, this.docname, this.df.options);
		} else if (cur_list) {
			options = cur_list.get_filter_value(this.df.options);
		} else if (cur_page) {
			options = cur_page.page?.page?.get_form_values()?.[this.df.options];
			if (!options) {
				const selector = `input[data-fieldname="${this.df.options}"]`;
				const input = $(cur_page.page).find(selector);
				if (input) {
					options = input.val();
				}
			}
		}

		if (frappe.model.is_single(options)) {
			frappe.throw(__("{0} is not a valid DocType for Dynamic Link", [options.bold()]));
		}

		return options;
	}
};
