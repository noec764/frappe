export class SCArrow {
	static render(props) {
		const { icon, color } = props;

		const $arrow_wrapper = $(`<div class="sc-row__arrow">`);
		const $arrow = $(`<div class="sc-arrow">`).appendTo($arrow_wrapper);
		if (icon) {
			$arrow.html(frappe.utils.icon(icon, "md"));
		}
		if (color) {
			$arrow.css("color", color);
		}
		return $arrow_wrapper;
	}
}
