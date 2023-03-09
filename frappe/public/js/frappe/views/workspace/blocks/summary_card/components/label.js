export class SCLabel {
	static render(props, container) {
		const { label } = props;

		const $label_wrapper = $(`<div class="sc-row__label">`);
		const $label = $(`<div class="sc-label">`).appendTo($label_wrapper);
		if (label) {
			$label.text(label);
		}
		if (container) {
			$label_wrapper.appendTo(container);
		}
		return $label_wrapper;
	}
}
