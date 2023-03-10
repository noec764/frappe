import { SCPill } from "./pill.js";
import { SCLabel } from "./label.js";
import { SCArrow } from "./arrow.js";
import { SCBadge } from "./badge.js";
import { SCIcon } from "./icon.js";

export class SCSection {
	static render(data, card_renderer) {
		if (!data.items?.length) {
			return;
		}
		switch (data.type) {
			case "Me":
				return SCSection.render_for_me(data, card_renderer);
			case "Section Break":
				return SCSection.render_collapsible(data, card_renderer);
			default:
				return SCSection.render_collapsible(data, card_renderer);
		}
	}

	static render_for_me(data, card_renderer) {
		const $section = $(`<div class="sc-foryou">`);

		const $row = $(`<div class="sc-row">`).appendTo($section);

		for (const row of data.items) {
			const type = row.type === "Liked By Me" ? "like" : "assign";
			const $pill = SCPill.render({
				label: row.badge,
				title: row.label,
				icon: row.icon,
				color: row.color,
				href: card_renderer.get_route({ filters: row.filters, view: "List" }),
				className: "sc-foryou-" + type,
				dataset: row.data,
			});
			$pill.appendTo($row);
		}

		return $section;
	}

	static render_collapsible(section, card_renderer) {
		if (!section.label) {
			return SCSection.render_no_label(section, card_renderer);
		}
		if (["0", "false"].includes("" + section.collapsible)) {
			return SCSection.render_non_collapsible(section, card_renderer);
		}

		const collapseId = "sc-section-" + Math.random().toString(36).substring(2);

		const $section = $(`<div class="sc-section">`);
		const $header = $(`<button class="sc-row sc-section__header">`).appendTo($section);

		$header.attr({
			role: "button",
			"aria-expanded": "true",
			"aria-label": __("Toggle Section") + ": " + section.label,
			"aria-controls": collapseId,
			"data-target": `#${collapseId}`,
			"data-toggle": "collapse",
		});

		SCArrow.render({ icon: "small-down" }).appendTo($header);
		SCLabel.render({ label: section.label }).appendTo($header);

		const $items = $(`<div class="sc-section__items">`).appendTo($section);
		$items.attr("id", collapseId).addClass("collapse show");

		for (const row of section.items) {
			SCSection.render_row(row, card_renderer).appendTo($items);
		}
		return $section;
	}

	static render_non_collapsible(section, card_renderer) {
		const $section = $(`<div class="sc-section">`);
		const $header = $(`<button class="sc-row sc-section__header">`).appendTo($section);

		if (section.icon) {
			SCIcon.render({ icon: section.icon }).appendTo($header);
		}
		SCLabel.render({ label: section.label }).appendTo($header);

		const $items = $(`<div class="sc-section__items">`).appendTo($section);
		for (const row of section.items) {
			SCSection.render_row(row, card_renderer).appendTo($items);
		}
		return $section;
	}

	static render_no_label(section, card_renderer) {
		const $section = $(`<div class="sc-section">`);
		const $items = $(`<div class="sc-section__items">`).appendTo($section);
		for (const row of section.items) {
			SCSection.render_row(row, card_renderer).appendTo($items);
		}
		return $section;
	}

	static render_row(row, card_renderer) {
		const href = card_renderer.get_route({ name: row.dt, filters: row.filters, view: "List" });

		let title = row.label || row.badge;
		if (row.badge?.length && row.label?.length) {
			title = __("{0}: {1}", [row.label, row.badge]);
		}

		const $row = $(`<a class="sc-row sc-link">`)
			.css("--sc-color", row.color)
			.attr("title", title)
			.attr("href", href);

		for (const key of Object.keys(row.data || {})) {
			$row.attr(`data-${key}`, row.data[key]);
		}

		if (row.badge) {
			SCBadge.render({ label: row.badge }).appendTo($row);
		}

		if (row.label) {
			SCLabel.render({ label: row.label }).appendTo($row);
		}

		let icon;
		if (row.icon) {
			icon = row.icon;
		} else if (row.dt !== card_renderer.data.dt) {
			icon = "arrow-up-right";
		} else {
			icon = "arrow-right";
		}

		if (row.dt !== card_renderer.data.dt) {
			$row.addClass("sc-icon-left");
		}

		if (icon) {
			SCIcon.render({ icon }).appendTo($row);
		}

		return $row;
	}

	static render_skeleton(text = "Lorem ipsum", length = 3) {
		const $section = $(`<div class="sc-section">`);
		const $header = $(`<button class="sc-row sc-section__header">`).appendTo($section);

		SCArrow.render({ icon: "small-down" }).appendTo($header);
		SCLabel.render({ label: text }).appendTo($header);

		const $items = $(`<div class="sc-section__items">`).appendTo($section);
		for (let i = 0; i < length; i++) {
			SCSection.render_skeleton_row().appendTo($items);
		}
		return $section;
	}

	static render_skeleton_row() {
		const $row = $(`<div class="sc-row sc-link">`);
		SCBadge.render({ label: "23" }).appendTo($row);
		SCLabel.render({ label: "Lorem ipsum" }).appendTo($row);
		SCIcon.render({ icon: "arrow-right" }).appendTo($row);
		return $row;
	}
}
