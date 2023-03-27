// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

frappe.provide("frappe.ui");

frappe.ui.color = {
	get: function (color_name, shade) {
		if (color_name && shade) return this.get_color_shade(color_name, shade);
		if (color_name) return this.get_color_shade(color_name, "default");
		return frappe.ui.color_map;
	},
	get_color: function (color_name) {
		const color_names = Object.keys(frappe.ui.color_map);
		if (color_names.includes(color_name)) {
			return frappe.ui.color_map[color_name];
		} else {
			// eslint-disable-next-line
			console.warn(`'color_name' can be one of ${color_names} and not ${color_name}`);
		}
	},
	get_color_map() {
		const colors = [
			"red",
			"green",
			"blue",
			"dark-green",
			"yellow",
			"gray",
			"purple",
			"pink",
			"orange",
		];
		const shades = ["100", "300", "500", "700"];
		const style = getComputedStyle(document.body);
		let color_map = {};
		colors.forEach((color) => {
			color_map[color] = shades.map((shade) =>
				style.getPropertyValue(`--${color}-${shade}`).trim()
			);
		});
		return color_map;
	},
	get_color_shade: function (color_name, shade) {
		const shades = {
			default: 2,
			light: 1,
			"extra-light": 0,
			dark: 3,
		};

		if (Object.keys(shades).includes(shade)) {
			const color = this.get_color(color_name);
			return color ? color[shades[shade]] : color_name;
		} else {
			// eslint-disable-next-line
			console.warn(`'shade' can be one of ${Object.keys(shades)} and not ${shade}`);
		}
	},
	all: function () {
		return Object.values(frappe.ui.color_map).reduce((acc, curr) => acc.concat(curr), []);
	},
	names: function () {
		return Object.keys(frappe.ui.color_map);
	},
	is_standard: function (color_name) {
		if (!color_name) return false;
		if (color_name.startsWith("#")) {
			return this.all().includes(color_name);
		}
		return this.names().includes(color_name);
	},
	get_color_name: function (hex) {
		for (const key in frappe.ui.color_map) {
			const colors = frappe.ui.color_map[key];
			if (colors.includes(hex)) return key;
		}
	},
	get_contrast_color: function (hex) {
		if (!this.validate_hex(hex)) {
			return;
		}
		if (!this.is_standard(hex)) {
			const brightness = this.brightness(hex);
			if (brightness < 128) {
				return this.lighten(hex, 0.9);
			}
			return this.lighten(hex, -0.9);
		}

		const color_name = this.get_color_name(hex);
		const colors = this.get_color(color_name);
		const shade_value = colors.indexOf(hex);
		if (shade_value <= 1) {
			return this.get(color_name, "dark");
		}
		return this.get(color_name, "extra-light");
	},

	validate_hex: function (hex) {
		// https://stackoverflow.com/a/8027444/5353542
		return /(^#[0-9A-F]{6}$)|(^#[0-9A-F]{3}$)/i.test(hex);
	},

	lighten(color, percent) {
		const clamp = (value, min = 0, max = 255) => Math.max(min, Math.min(max, value));
		// https://stackoverflow.com/a/13542669/5353542
		color = this.normalize_hex(color);
		var f = parseInt(color, 16),
			t = percent < 0 ? 0 : 255,
			p = Math.abs(percent),
			R = f >> 16,
			G = (f >> 8) & 0x00ff,
			B = f & 0x0000ff;
		return (
			"#" +
			(
				0x1000000 +
				clamp(Math.round((t - R) * p) + R) * 0x10000 +
				clamp(Math.round((t - G) * p) + G) * 0x100 +
				clamp(Math.round((t - B) * p) + B)
			)
				.toString(16)
				.slice(1)
		);
	},

	hex_to_rgb(hex) {
		hex = this.normalize_hex(hex);
		const r = parseInt(hex.substring(0, 2), 16);
		const g = parseInt(hex.substring(2, 4), 16);
		const b = parseInt(hex.substring(4, 6), 16);
		return { r, g, b };
	},

	brightness(hex) {
		hex = this.normalize_hex(hex);
		const rgb = this.hex_to_rgb(hex);
		// https://www.w3.org/TR/AERT#color-contrast
		// 255 - brightest (#fff)
		// 0 - darkest (#000)
		return (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
	},

	normalize_hex(hex) {
		if (hex.startsWith("#")) {
			hex = hex.substring(1);
		}
		if (hex.length === 3) {
			hex = [0, 0, 1, 1, 2, 2].map((i) => hex[i]).join("");
		}
		return hex;
	},

	/**
	 * Parses a color string and returns a hex string or null.
	 * @param {string} color_string
	 * @returns {string|null}
	 * @example
	 * frappe.ui.color.parse_color("red"); // "#ff0000"
	 * frappe.ui.color.parse_color("#ff0000"); // "#ff0000"
	 * frappe.ui.color.parse_color("rgb(255, 0, 0)"); // "#ff0000"
	 * frappe.ui.color.parse_color("rgba(255, 0, 0, 0.5)"); // null
	 */
	parse_color(color_string) {
		if (typeof color_string !== "string") {
			return null;
		}

		// Use the browser's built-in parser to parse the color string
		const canvas = document.createElement("canvas");
		const context = canvas.getContext("2d");
		context.fillStyle = "rgba(0, 0, 0, 0)";
		context.fillStyle = color_string;

		// Invalid values are ignored. Colors with transparency are returned as rgba.
		// Other fully opaque colors are returned as hex strings.
		// https://html.spec.whatwg.org/multipage/canvas.html#serialisation-of-a-color
		if (context.fillStyle.startsWith("#")) {
			return context.fillStyle;
		}
		return null;
	},
};

frappe.ui.color_map = frappe.ui.color.get_color_map();
