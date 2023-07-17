import "./float";

frappe.ui.form.ControlInt = class ControlInt extends frappe.ui.form.ControlFloat {
	get_precision() {
		return 0; // Used for rounding and formatting
	}
};

frappe.ui.form.ControlLongInt = frappe.ui.form.ControlInt;
