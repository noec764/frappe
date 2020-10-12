frappe.ready(function () {
	frappe.web_form.add_button_to_header('header_calendar_btn', this.button_label || __("Back to calendar"), "primary", () =>
		window.location.href = "/events"
	);
})