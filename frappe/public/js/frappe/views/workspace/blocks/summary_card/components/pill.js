export class SCPill {
	static render(props, container) {
		const { label, title, href, icon, color, className, dataset } = props;
		if (!label) console.error("Label is required for Pill");
		if (!icon) console.error("Icon is required for Pill");

		const $pill = $(`<a class="sc-link-pill ${className}">`)
			.html(frappe.utils.icon(icon, "sm"))
			.css("color", color)
			.attr("href", href)
			.attr("title", title)
			.append($(`<span>`).text(label));

		if (container) {
			$pill.appendTo(container);
		}

		if (dataset) {
			for (const key of Object.keys(dataset)) {
				$pill.attr(`data-${key}`, dataset[key]);
			}
		}

		return $pill;
	}
}
