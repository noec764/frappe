export class SCBadge {
	static render(props) {
		const { text = props.label, color } = props;

		const $badge_wrapper = $(`<div class="sc-badge__wrapper">`);
		const $badge = $(`<div class="sc-badge">`).text(text).appendTo($badge_wrapper);

		if (color) {
			$badge.css("color", color);
		}

		return $badge_wrapper;
	}
}
