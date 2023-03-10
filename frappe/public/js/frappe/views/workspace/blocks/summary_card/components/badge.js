export class SCBadge {
	static render(props) {
		const { text = props.label, color } = props;

		const $badge = $(`<div class="sc-badge">`).text(text);

		if (color) {
			$badge.css("color", color);
		}

		return $badge;
	}
}
