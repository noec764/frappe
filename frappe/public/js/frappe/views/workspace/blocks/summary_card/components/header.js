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
		const sc = summary_card_renderer.data;
		const primary_route = summary_card_renderer.get_primary_route();
		return SCHeader.render({
			children: [
				SCIcon.render({ icon: sc.icon || "file", size: "md" }),
				SCLabel.render({ label: sc.title, href: primary_route }),
			],
			actions: [
				SCButton.render({
					icon: sc.primary_button.icon || "view",
					label: sc.primary_button.label,
					className: "summary-card__primary-button",
					href: primary_route,
				}),
			],
		});
	}

	static render_skeleton() {
		return SCHeader.render({
			children: [
				SCIcon.render({ icon: "file", size: "md" }), // icon
				SCLabel.render({ label: "Lorem ipsum" }),
			],
			actions: [
				SCButton.render({
					icon: "view",
					label: "Lorem",
					className: "summary-card__primary-button",
				}),
			],
		});
	}
}
