import Picker from "../../color_picker/color_picker";

frappe.ui.form.ControlColor = class ControlColor extends frappe.ui.form.ControlData {
	make_input() {
		this.df.placeholder = this.df.placeholder || __("Choose a color");
		super.make_input();
		this.make_color_input();
	}

	make_color_input() {
		let picker_wrapper = $("<div>");
		this.picker = new Picker({
			parent: picker_wrapper[0],
			color: this.get_color(),
			swatches: [
				// accessible palette
				"#CB2929",
				"#ECAD4B",
				"#29CD42",
				"#449CF0",
				"#4463F0",
				"#761ACB",
				"#ED6396",

				// gray scale
				"#111111",
				"#333333",
				"#555555",
				"#666666",
				"#AAAAAA",
				"#CCCCCC",
				"#EEEEEE",

				"divider",

				// full palette
				"#940015",
				"#694000",
				"#2d5000",
				"#015050",
				"#272dc5",
				"#6e0db3",
				"#911136",

				"#de3921",
				"#d69915",
				"#248b20",
				"#04838c",
				"#4463f0",
				"#a14bd6",
				"#bc367e",

				"#ff897d",
				"#ecc500",
				"#5ec13a",
				"#00bfca",
				"#46b4ff",
				"#d094ff",
				"#f28cba",
			],
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

	get_color() {
		return this.validate(this.get_value());
	}

	validate(value) {
		if (value === "") {
			return "";
		}
		var is_valid = /^#[0-9A-F]{6}$/i.test(value);
		if (is_valid) {
			return value;
		}
		return null;
	}
};
