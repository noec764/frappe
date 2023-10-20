import { SCSection, SCHeader } from "./components";

const assert = (condition, message) => {
	if (!condition) {
		throw message || "Assertion failed";
	}
};

/**
 * @typedef {Object} Data
 * @property {string} error
 * @property {string} label
 * @property {string} dt
 * @property {string} icon
 * @property {Object[]} sections
 * @property {string} sections.label
 * @property {string} sections.type
 * @property {Object[]} sections.items
 * @property {string} sections.items.type
 * @property {string} sections.items.label
 * @property {string} sections.items.dt
 * @property {string} sections.items.color
 * @property {string} sections.items.icon
 * @property {string} sections.items.badge
 * @property {Object} primary_button
 * @property {string} primary_button.view
 * @property {string} primary_button.label
 * @property {string} primary_button.dt
 * @property {string} primary_button.doctype
 * @property {string} primary_button.query
 * @property {string} primary_button.filters
 */

export default class SummaryCardRenderer {
	constructor(opts) {
		Object.assign(this, opts);

		assert(this.wrapper instanceof HTMLElement, "Summary Card wrapper is not an HTMLElement");
		assert(this.$body instanceof jQuery, "Summary Card body is not a jQuery object");
		assert(this.$footer instanceof jQuery, "Summary Card footer is not a jQuery object");
		assert(this.$header instanceof jQuery, "Summary Card header is not a jQuery object");
		assert(this.set_name instanceof Function, "Summary Card set_name is not a function");
		assert(
			["string", "undefined"].includes(typeof this.summary_card_name),
			"Summary Card name is not a string | undefined"
		);

		this.setup();

		/**
		 * @type {Data}
		 */
		this.data = null;
	}

	async setup() {
		this.$body.empty();

		this.$freeze = $('<div class="summary-card__freeze">');
		this.$footer.append(this.$freeze);

		this.wrapper.setAttribute("summary_card_name", this.summary_card_name);
		this.render_loading_state();

		this.make();
	}

	async fetch_data() {
		return frappe.xcall("frappe.desk.doctype.summary_card.summary_card.get_summary", {
			summary_card_name: this.summary_card_name,
		});
	}

	make() {
		this.render();
	}

	get_config() {
		return {
			name: this.summary_card_name,
		};
	}

	set_actions() {
		if (this.in_customize_mode) return;
	}

	// Main render
	get_view() {
		return this.data.primary_button?.view || "List";
	}

	// set_route({ filters = null, name = this.data.dt, view = this.get_view(), ...extra } = {}) {
	// 	const route = frappe.utils.generate_route({
	// 		name: name,
	// 		type: "doctype",
	// 		doc_view: view,
	// 		...extra,
	// 	});
	// 	if (filters) {
	// 		filters = frappe.utils.get_filter_from_json(filters);
	// 		if (filters) {
	// 			frappe.route_options = filters;
	// 		}
	// 	}
	// 	frappe.set_route(route);
	// }

	get_route({ filters = null, name = this.data.dt, view = this.get_view(), ...extra } = {}) {
		const route = frappe.utils.generate_route({
			name: name,
			type: "doctype",
			doc_view: view,
			...extra,
		});
		const url = new URL(route, window.location.origin);
		if (filters && Array.isArray(filters) && filters.length) {
			if (!Array.isArray(filters[0])) {
				filters = [filters];
			}
			for (const filt of filters) {
				if (filt.length === 4) {
					const [dt, fieldname, op, value] = filt;
					if (dt !== name) {
						console.log("dt !== name"); // eslint-disable-line no-console
					}
					url.searchParams.append(fieldname, JSON.stringify([op, value]));
				} else if (filt.length === 3) {
					const [fieldname, op, value] = filt;
					url.searchParams.append(fieldname, JSON.stringify([op, value]));
				}
			}
		}
		return url.href;
	}

	get_primary_route() {
		if (!this.data.primary_button) {
			return null;
		}
		return frappe.utils.generate_route({
			name: this.data.dt,
			type: "doctype",
			doc_view: this.get_view(),
		});
	}

	_render_empty() {
		this.$header.empty();
		this.$body.empty();
		this.$freeze.empty();
	}

	render_loading_state() {
		this._render_empty();
		this.wrapper.setAttribute("data-state", "loading");
		this.render_skeleton();
	}

	render_no_data_state() {
		this._render_empty();
		this.wrapper.setAttribute("data-state", "no-data");
		this.$header.text(__("Summary Card"));

		const input = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Summary Card",
				fieldname: "summary_card_name",
				label: __("Pick an existing Summary Card"),
				default: "",
				change: () => {
					const value = input.get_value();
					if (value) {
						this.summary_card_name = value;
						this.set_name(value);
						this.render();
					}
				},
			},
			parent: this.$freeze,
		});
		input.refresh();
	}

	render_error_state(error) {
		this._render_empty();
		this.wrapper.setAttribute("data-state", "error");

		const msg = [__("Summary Card"), __("Error")].join(" &middot; ");
		this.$header.html(msg);

		console.error(error); // eslint-disable-line no-console
		try {
			error = JSON.parse(error);
		} catch (e) {
			// pass
		}
		this.$freeze.html(
			`<div style="user-select:text;white-space:pre-wrap;font-size:var(--text-xs);"></div>`
		);
		this.$freeze.find("div").text(error?.message || JSON.stringify(error, null, 2));
	}

	render_header() {
		const $new_header = SCHeader.render_for_card(this);
		$new_header.addClass(this.$header.attr("class"));
		this.$header.replaceWith($new_header);
		this.$header = $new_header;
	}

	render_skeleton() {
		const $spinner = this.$freeze;
		$spinner.append($("<div>").text(__("Loading...")));

		const $skel_header = SCHeader.render_skeleton(this);
		$skel_header.addClass(this.$header.attr("class"));
		this.$header.replaceWith($skel_header);
		this.$header = $skel_header;

		SCSection.render_skeleton("Lorem", 3).appendTo(this.$body);
		SCSection.render_skeleton("Lorem ipsum", 2).appendTo(this.$body);
	}

	async render() {
		this._render_empty();

		if (!this.summary_card_name) {
			this.render_no_data_state();
			return;
		}

		this.render_loading_state();

		this.data = await this.fetch_data();
		this.wrapper.sc_data = this.data;
		if (!this.data) {
			this.render_no_data_state();
			return;
		} else if (this.data.error) {
			this.render_error_state(this.data.error);
			return;
		}

		this.wrapper.setAttribute("data-state", "ok");
		this.wrapper.setAttribute("summary_card_name", this.summary_card_name);

		this.$header.empty();
		this.$freeze.empty();
		this.$body.empty();

		this.render_header();

		for (const section of this.data.sections) {
			const $section = SCSection.render(section, this);
			if ($section) {
				$section.appendTo(this.$body);
			}
		}
	}
}
