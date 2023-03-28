export class SCIcon {
	static render(props) {
		const { icon, color, size = "md" } = props;

		const $icon_wrapper = $(`<div class="sc-row__icon">`);
		const $icon = $(`<div class="sc-icon">`).appendTo($icon_wrapper);
		if (icon) {
			$icon.html(frappe.utils.icon(icon, size));
		}
		if (color) {
			$icon.css("color", color);
		}
		return $icon_wrapper;
	}
}
