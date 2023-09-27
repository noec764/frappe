import Picker from "../../color_picker/color_picker";

const DEFAULT_SWATCHES = [
	// full palette
	"#940015",
	"#694000",
	"#2D5000",
	"#015050",
	"#2438AF",
	"#6E0DB3",
	"#911136",

	"#E13321",
	"#CE9514",
	"#248B20",
	"#04838F",
	"#0E6DFE",
	"#A14BD6",
	"#BC367E",

	"#FF897D",
	"#ECAD4B",
	"#5EC13A",
	"#40BCBB",
	"#63ADFF",
	"#D094FF",
	"#F28CBA",

	// gray scale
	"#181818",
	"#333333",
	"#555555",
	"#888888",
	"#AAAAAA",
	"#CCCCCC",
	"#EEEEEE",
];

frappe.ui.form.ControlColor = class ControlColor extends frappe.ui.form.ControlData {
	make_input() {
		this.df.placeholder = this.df.placeholder || __("Choose a color");
		super.make_input();

		/** Colors selected in the picker during this session */
		this.most_recent_colors = [];

		/** Colors used in similar documents */
		this.recent_colors = [];

		this.fetch_recent_colors();
		this.make_color_input();

		this.$input.on("blur", () => {
			if (!this.get_color()) {
				this.set_value("");
			}
		});
	}

	make_color_input() {
		let picker_wrapper = $("<div>");
		this.picker = new Picker({
			parent: picker_wrapper[0],
			color: this.get_color(),
			swatches: this.get_swatches(),
		});

		this.$wrapper
			.popover({
				trigger: "manual",
				offset: `${-this.$wrapper.width() / 4}, 5`,
				boundary: "viewport",
				placement: "bottom",
				template: `
				<div class="popover color-picker-popover">
					<div class="picker-arrow arrow"></div>
					<div class="popover-body popover-content"></div>
				</div>
			`,
				content: () => picker_wrapper,
				html: true,
			})
			.on("show.bs.popover", () => {
				setTimeout(() => {
					this.picker.refresh();
				}, 10);
			})
			.on("hidden.bs.popover", () => {
				$("body").off("click.color-popover");
				$(window).off("hashchange.color-popover");

				// Add to most recent colors
				const color = this.get_color()?.toUpperCase?.() ?? "";
				this.most_recent_colors = this.most_recent_colors || [];
				if (color && !this.most_recent_colors.includes(color)) {
					this.most_recent_colors.push(color);
				}
			});

		this.picker.on_change = (color) => {
			this.set_value(color);
		};

		if (!this.selected_color) {
			this.selected_color = $(`<div class="selected-color"></div>`);
			this.selected_color.insertAfter(this.$input);
		}

		this.$wrapper
			.find(".selected-color")
			.parent()
			.on("click", (e) => {
				this.$wrapper.popover("toggle");
				if (!this.get_color()) {
					this.$input.val("");
				}
				e.stopPropagation();
				$("body").on("click.color-popover", (ev) => {
					if (!$(ev.target).parents().is(".popover")) {
						this.$wrapper.popover("hide");
					}
				});
				$(window).on("hashchange.color-popover", () => {
					this.$wrapper.popover("hide");
				});
			});
	}

	refresh() {
		super.refresh();
		let color = this.get_color();
		this.refresh_swatches_debounced =
			this.refresh_swatches_debounced ||
			frappe.utils.throttle(() => this.refresh_swatches(), 50);
		this.refresh_swatches_debounced();
		if (this.picker && this.picker.color !== color) {
			this.picker.color = color;
			this.picker.refresh();
		}
	}

	set_formatted_input(value) {
		super.set_formatted_input(value);
		this.$input?.val(value);
		this.selected_color?.css({
			"background-color": value || "transparent",
		});
		this.selected_color?.toggleClass("no-value", !value);
	}

	parse(value) {
		if (typeof value !== "string") {
			return null;
		}
		if (value.includes("rgb") && !value.includes(")")) {
			return null;
		}
		return frappe.ui.color.parse_color(value);
	}

	get_color() {
		return this.parse(this.get_value());
	}

	async fetch_recent_colors() {
		if (this.df.parent && this.df.fieldname) {
			const colors = await frappe.ui.color.get_colors_used_in_documents?.({
				doctype: this.df.parent,
				fieldname: this.df.fieldname,
			});
			if (!Array.isArray(colors)) return;
			this.recent_colors = colors;
			this.refresh_swatches();
		}
	}

	get_swatches() {
		const current_color = this.get_color();
		const extra_swatches = [
			{
				label: __("Recent Colors"),
				colors: this.recent_colors,
				sorted: true,
			},
			{
				label: null,
				colors: this.most_recent_colors,
				include_current_color: true,
			},
			{
				label: __("Custom Colors"),
				colors: frappe.boot.custom_colors,
				sorted: true,
			},
		];

		const swatches = DEFAULT_SWATCHES.slice();

		for (const source of extra_swatches) {
			if (!Array.isArray(source.colors)) {
				continue;
			}

			const colors = source.colors
				.map((color) => color?.toUpperCase().trim())
				.filter((color) => color.startsWith("#") && !swatches.includes(color))
				.slice(0, 3 * 7);

			if (source.sorted) {
				colors.sort((a, b) => {
					const h1 = frappe.ui.color.hue(a);
					const h2 = frappe.ui.color.hue(b);
					return h1 - h2 || a > b || -1;
				});
			}

			if (
				source.include_current_color &&
				current_color &&
				!swatches.includes(current_color)
			) {
				colors.push(current_color);
			}

			if (!colors.length) {
				continue;
			}

			if (source.label) {
				swatches.push("divider:" + source.label);
			}
			swatches.push(...colors);
		}

		return swatches;
	}

	refresh_swatches() {
		this.picker?.set_swatches(this.get_swatches());
	}
};
