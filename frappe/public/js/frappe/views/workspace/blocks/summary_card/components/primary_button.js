export class SCButton {
	static render({ label, href, icon, className }, container) {
		const btn_type = href ? "a" : "button";

		const $btn = $(`<${btn_type} class="btn btn-xs sc-button ${className}">`);

		if (icon) {
			$btn.html(frappe.utils.icon("view", "sm"));
		}

		$btn.append($(`<span>`).text(label));

		if (href) {
			$btn.attr("href", href);
		}

		if (container) {
			$btn.appendTo(container);
		}

		return $btn;
	}
}
