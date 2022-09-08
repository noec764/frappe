frappe.ui.form.ControlDynamicLink = class ControlDynamicLink extends frappe.ui.form.ControlLink {
	get_options() {
		let options = "";
		if (this.df.get_options) {
			options = this.df.get_options(this);
		} else if ((this.docname == null || this.doc.__islocal) && cur_dialog) {
			//for dialog box
			options =
				cur_dialog.doc && this.df.options
					? cur_dialog.doc[this.df.options]
					: cur_dialog.get_value(this.df.options);
		} else if (this.df.parent) {
			options = frappe.model.get_value(this.df.parent, this.docname, this.df.options);
		} else if (cur_list || cur_page) {
			const page = cur_list.page || cur_page;
			options = page.fields_dict[this.df.options].value;
		}

		if (frappe.model.is_single(options)) {
			frappe.throw(__("{0} is not a valid DocType for Dynamic Link", [options.bold()]));
		}

		return options;
	}
};
