export class SCLabel {
	static render(props) {
		const { label, href } = props;

		const type = href ? "a" : "div";

		const $label = $(`<${type} class="sc-label">`);
		$label.text(label);
		if (href) {
			$label.attr("href", href);
		}

		return $label;
	}
}
