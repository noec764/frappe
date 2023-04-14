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
			this.input.select();
			return false; // NOTE: maybe useless, cancel bubbling
		});

		// On blur, format the number again.
		this.input.addEventListener("blur", (e) => {
			if (this.change) {
				this.change(e);
			} else {
				this.set_input(this.value);
			}
		});
	}

	validate(value) {
		return this.parse(value);
	}

	/**
	 * @param {any} value
	 * @returns {number | null} The parsed numeric value, rounded if needed, or null if invalid.
	 */
	parse(value) {
		let parsed = this.eval_expression(value);

		parsed = Number.parseFloat(parsed);
		if (Number.isNaN(parsed)) {
			return null; // `value` is not a valid number or expression
		}

		// `parsed` is now a number.
		// Round to precision (0 for Int, ? for Float)
		parsed = flt(parsed, this.get_precision());

		return parsed;
	}

	/** @returns {string | number | null} */
	get_precision() {
		// round based on field precision or system's float precision, else don't round
		return this.df.precision || cint(frappe.boot.sysdefaults.float_precision, null);
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
};

frappe.ui.form.ControlPercent = frappe.ui.form.ControlFloat;
