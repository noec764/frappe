frappe.ui.form.ControlFloat = class ControlFloat extends frappe.ui.form.ControlData {
	static trigger_change_on_input_event = false;

	/** NOTE: do not include the comma (,) as it is the sequence operator in JavaScript */
	static EXPR_REGEX = /^[\d+\-\/*\.\(\)\s_]+$/;

	make_input() {
		super.make_input();

		this.apply_configuration();

		this.input.setAttribute("inputmode", "numeric");

		this._set_placeholder();

		// On focus, convert the value to a valid JS float number, and select the input.
		this.input.addEventListener("focus", (e) => {
			this.input.value = this.value ?? "";
			this._set_is_formatted(false);
			this.input.select();
			return false; // NOTE: maybe useless, cancel bubbling
		});

		// On blur, format the number again.
		this.input.addEventListener("focusout", (e) => {
			this._set_is_formatted(true);
			this.set_input(this.value);

			if (this.change) {
				this.change(e);
			}
		});

		// The `change` event is also triggered when the user presses Enter.
		this.input.addEventListener("change", (e) => {
			// Blur the input because the user is done editing it.
			this.input.blur();
		});
	}

	_set_placeholder() {
		const placeholder = this._get_placeholder();
		if (placeholder) {
			this.input.setAttribute("placeholder", placeholder);
		} else {
			this.input.removeAttribute("placeholder");
		}
	}

	_get_placeholder() {
		if (this.df.placeholder) {
			return this.df.placeholder;
		}

		if (typeof this.df.min === "number") {
			return __("{0}: {1}", [__("Minimum"), this.format_for_input(this.df.min)]);
		} else if (typeof this.df.max === "number") {
			return __("{0}: {1}", [__("Maximum"), this.format_for_input(this.df.max)]);
		}

		const standard_types = ["Currency", "Int", "Float", "Percent"];
		if (standard_types.some((type) => this.df.fieldtype.includes(type))) {
			return this.format_for_input(0, { always_show_decimals: true });
			// return __(this.df.fieldtype);
		}
	}

	get_input_value() {
		// If the input is not formatted, return the raw value.
		if (this.input?.dataset.isFormatted === "false") {
			return this.input.value;
		}
		// If the input is formatted, return the stored value.
		return String(this.value);
	}

	set_formatted_input(value) {
		super.set_formatted_input(value);
		this._set_is_formatted(true);
	}

	set_disp_area(value) {
		if (this.slider_disp_bar && this.slider_disp_val) {
			this.slider_disp_bar.value = value;
			this.slider_disp_val.innerText = this.format_for_input(value);
		} else {
			super.set_disp_area(value);
		}
	}

	/** @param {boolean} is_formatted */
	_set_is_formatted(is_formatted) {
		if (!this.input) return;
		// if (is_formatted) {
		// 	this.input.removeAttribute("pattern");
		// } else {
		// 	this.input.pattern = this.constructor.EXPR_REGEX.source.slice(1, -1);
		// }
		this.input.dataset.isFormatted = is_formatted ? "true" : "false";
	}

	apply_configuration() {
		const config = this.get_configuration();
		this.df.min = config.min;
		this.df.max = config.max;
		this.df.step = config.step;
		this.df.with_slider = config.with_slider;
	}

	validate(value) {
		return this.parse(value);
	}

	/**
	 * @param {any} value
	 * @returns {number | null} The parsed numeric value, rounded and clamped if needed, or null if invalid.
	 */
	parse(value) {
		let parsed = this.eval_expression(value);

		parsed = Number.parseFloat(parsed);
		if (Number.isNaN(parsed)) {
			if (typeof this.df.min === "number") {
				return this.df.min;
			}
			return null; // `value` is not a valid number or expression
		}

		// `parsed` is now a number.
		parsed = this._clamp(parsed);

		// Round to precision (0 for Int, ? for Float)
		parsed = flt(parsed, this.get_precision());

		return parsed;
	}

	/** @returns {string | number | null} */
	get_precision() {
		// round based on field precision or system's float precision, else don't round
		return this.df.precision || cint(frappe.boot.sysdefaults.float_precision, null);
	}

	_clamp(value) {
		const { min, max, non_negative } = this.df ?? {};
		if (non_negative && value < 0) {
			return 0;
		}
		if (typeof min === "number" && value < min) {
			return min;
		}
		if (typeof max === "number" && value > max) {
			return max;
		}
		return value;
	}

	/** @param {number | null} value */
	format_for_input(value, opts = {}) {
		if (value == null) {
			return "";
		}

		return frappe.format(value, this.df, { inline: true, ...opts }, this.get_doc());
	}

	eval_expression(value) {
		if (typeof value === "string") {
			value = value.replace(/[_\s\u066c]/g, ""); // remove thousands separators
			value = value.replace(/[,\u066b]/g, "."); // replace decimal separators with dots
		}
		if (typeof value === "string" && value.match(this.constructor.EXPR_REGEX)) {
			try {
				// If it is a string containing operators
				return eval(value);
			} catch (e) {
				// When the expression is invalid, return null instead of
				// returning the expression itself so that parseFloat doesn't
				// try to extract a number from the beginning of the string.
				return null;
			}
		}
		return value;
	}

	// Slider
	set_input(value) {
		super.set_input(value);
		if (this.slider_input) {
			this.slider_input.value = value;
		}
	}

	refresh_input() {
		super.refresh_input();
		this.slider_refresh();
	}

	slider_setup() {
		this.slider_input = $(`<input type="range" />`).insertBefore(this.input)[0];

		// Setup styles
		this.input_area.classList.add("control-with-slider");

		// Setup attributes
		this.slider_set_attributes();

		// Setup event listeners
		this.input.addEventListener("input", () => {
			this.slider_input.value = this.parse(this.input.value) ?? this.value;
		});
		this.slider_input.addEventListener("input", () => {
			this.set_value(this.slider_input.value);
		});

		// Set initial value AFTER setting min/max/step
		this.slider_input.value = this.value;
	}

	slider_readonly_setup() {
		if (this.disp_area) {
			this.disp_area.classList.remove("like-disabled-input");
			this.disp_area.innerHTML = "<meter></meter><div></div>";
			this.slider_disp_val = this.disp_area.querySelector("div");
			this.slider_disp_val.classList.add("like-disabled-input");
			this.slider_disp_bar = this.disp_area.querySelector("meter");
		}
	}

	slider_destroy() {
		this.slider_input.remove();
		this.slider_input = null;
		this.input_area.classList.remove("control-with-slider");
	}

	slider_readonly_destroy() {
		this.disp_area?.classList.remove("control-with-slider");
		this.slider_disp_val?.remove();
		this.slider_disp_val = null;
		this.slider_disp_bar?.remove();
		this.slider_disp_bar = null;
	}

	slider_set_attributes(slider_input = this.slider_input) {
		if (typeof this.df.min === "number") {
			slider_input.setAttribute("min", this.df.min);
		} else {
			slider_input.setAttribute("min", 0);
		}

		if (typeof this.df.max === "number") {
			slider_input.setAttribute("max", this.df.max);
		} else {
			slider_input.setAttribute("max", 100);
		}

		const step = this._get_slider_step_size_from_precision();
		if (step > 0) {
			slider_input.setAttribute("step", step);
		} else {
			slider_input.removeAttribute("step");
		}
	}

	slider_readonly_refresh() {
		if (this.disp_area && this.slider_disp_val && this.slider_disp_bar) {
			this.disp_area.classList.add("control-with-slider");
			this.slider_set_attributes(this.slider_disp_bar);
			this.slider_disp_bar.style.height = "1.41em";
		}
	}

	_get_slider_step_size_from_precision() {
		let step = 0;
		const precision = cint(this.get_precision(), null);
		if (typeof precision === "number" && precision >= 0) {
			// 1/10^x gives nicer values than 10^-x
			step = 1 / Math.pow(10, precision);
		}
		if (this.df.fieldtype?.matches?.(/Int$/)) {
			step = 1;
		}
		if (typeof this.df.step === "number") {
			step = this.df.step;
		}
		return step;
	}

	slider_refresh() {
		if (this.df.with_slider) {
			if (this.slider_input) {
				this.slider_set_attributes();
				this.slider_readonly_refresh();
			} else {
				this.slider_setup();
				this.slider_readonly_setup();
			}
		} else {
			if (this.slider_input) {
				this.slider_destroy();
			}
			if (this.disp_area) {
				this.slider_readonly_destroy();
			}
		}
	}
};

frappe.ui.form.ControlPercent = frappe.ui.form.ControlFloat;
