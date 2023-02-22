import FloatingButton from "./floating_button";

frappe.provide("frappe.back_button_specs");

frappe.ui.BackButton = class BackButton extends FloatingButton {
	constructor() {
		super("BackButton", "back-button");
		this._listen_btn_click();
		this._listen_url_change();
		this.update();
	}

	_listen_btn_click() {
		this.on("click", () => {
			const kind = this.get_kind_from_url();
			const spec = this.get_spec_for_name(kind);
			if (spec?.action) {
				spec.action();
			} else if (spec?.route) {
				window.history.go(spec.route);
			} else {
				if (window.history.length > 1) {
					window.history.back();
				}
			}
		});
	}

	_listen_url_change() {
		window.addEventListener("popstate", () => {
			this.update();
		});
	}

	update() {
		const kind = this.get_kind_from_url();
		let spec = this.get_spec_for_name(kind);

		if (typeof spec === "function") {
			spec = spec();
		}
		if (spec) {
			this.set(spec);
			this.show();
		} else {
			this.hide();
		}
	}

	get_kind_from_url() {
		// Get the "_back" URL param
		const url = new URL(window.location.href);
		const params = new URLSearchParams(url.search);
		return params.get("_back");
	}

	get_spec_for_name(name) {
		if (!name || !frappe.back_button_specs) return;
		return frappe.back_button_specs[name];
	}
};

export default frappe.ui.BackButton;
