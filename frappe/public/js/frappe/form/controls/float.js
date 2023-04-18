frappe.ui.form.ControlFloat = class ControlFloat extends frappe.ui.form.ControlData {
	static trigger_change_on_input_event = false;

	/** NOTE: do not include the comma (,) as it is the sequence operator in JavaScript */
	static EXPR_REGEX = /^[0-9+\-/*()_\. ]+$/;

	make_input() {
		super.make_input();

		this.input.setAttribute("inputmode", "numeric");

		// On focus, convert the value to a valid JS float number, and select the input.
		this.input.addEventListener("focus", (e) => {
			this.input.value = this.value ?? "";
			this.input.dataset.isFormatted = "false";
			this.input.select();
			return false; // NOTE: maybe useless, cancel bubbling
		});

		// On blur, format the number again.
		this.input.addEventListener("focusout", (e) => {
			this.input.dataset.isFormatted = "true";
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

	get_input_value() {
		// If the input is not formatted, return the raw value.
		if (this.input.dataset.isFormatted === "false") {
			return this.input.value;
		}
		// If the input is formatted, return the stored value.
		return String(this.value);
	}

	set_formatted_input(value) {
		super.set_formatted_input(value);
		this.input.dataset.isFormatted = "true";
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
	format_for_input(value) {
		if (value == null) {
			return "";
		}

		return frappe.format(value, this.df, { inline: true }, this.get_doc());
	}

	eval_expression(value) {
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

		// Setup event listeners
		this.input.addEventListener("input", () => {
			this.slider_input.value = this.parse(this.input.value) ?? this.value;
		});
		this.slider_input.addEventListener("input", () => {
			this.set_value(this.slider_input.value);
		});

		// Setup styles
		this.input_area.style.display = "flex";
		this.input_area.style.alignItems = "center";
		this.input_area.style.gap = "0.5rem";
		this.input.style.flex = "1";
		this.slider_input.style.flex = "3";

		// Setup attributes
		this.slider_set_attributes();

		// Set initial value AFTER setting min/max/step
		this.slider_input.value = this.value;
	}

	slider_destroy() {
		this.input.classList.remove("input-xs");
		this.slider_input.remove();
		this.slider_input = null;
		this.input.style.flex = "";
		this.input_area.style.display = "";
	}

	slider_set_attributes() {
		if (typeof this.df.min === "number") {
			this.slider_input.setAttribute("min", this.df.min);
		} else {
			this.slider_input.setAttribute("min", 0);
		}

		if (typeof this.df.max === "number") {
			this.slider_input.setAttribute("max", this.df.max);
		} else {
			this.slider_input.setAttribute("max", 100);
		}

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
		if (step > 0) {
			this.slider_input.setAttribute("step", step);
		} else {
			this.slider_input.removeAttribute("step");
		}
	}

	slider_refresh() {
		if (this.df.with_slider) {
			if (this.slider_input) {
				this.slider_set_attributes();
			} else {
				this.slider_setup();
			}
		} else if (this.slider_input) {
			this.slider_destroy();
		}
	}
};

frappe.ui.form.ControlPercent = frappe.ui.form.ControlFloat;
