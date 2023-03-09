import { SCIcon } from "./icon";
import { SCLabel } from "./label";
import { SCButton } from "./primary_button";

export class SCHeader {
	static render({ children, actions }) {
		const $header = $(`<div class="sc-row sc-header">`);

		if (children) {
			$header.append(...children);
		}

		if (actions) {
			const $actions = $(`<div class="sc-header__actions">`);
			$actions.append(...actions);
			$header.append($actions);
		}

		return $header;
	}

	static render_for_card(summary_card_renderer) {
		return SCHeader.render({
			children: [
				SCIcon.render({ icon: "file" }),
				SCLabel.render({ label: summary_card_renderer.data.title }),
			],
			actions: [
				SCButton.render({
					icon: "view",
					label: summary_card_renderer.data.primary_button.label,
					className: "summary-card__primary-button",
					href: summary_card_renderer.get_primary_route(),
				}),
			],
		});
	}
}
