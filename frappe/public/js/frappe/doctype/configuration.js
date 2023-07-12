export function setup_docfield_configuration(frm, field_dt = null, table_fieldname = "fields") {
	const heuristics = {
		is_number: (df) =>
			["Int", "Float", "Currency", "Percent"].some((type) => df.fieldtype.includes(type)),
		is_date: (df) => df.fieldtype === "Date",
	};

	const get_config_fields = (df) => {
		const config_fields = [];

		if (heuristics.is_number(df)) {
			config_fields.push(
				{ fieldtype: "Section Break" },
				{
					fieldtype: df.fieldtype,
					label: __("Minimum Value"),
					fieldname: "min",
				},
				{ fieldtype: "Column Break" },
				{
					fieldtype: df.fieldtype,
					label: __("Maximum Value"),
					fieldname: "max",
				},
				{ fieldtype: "Section Break" },
				{
					fieldtype: "Check",
					label: __("With Slider"),
					fieldname: "with_slider",
				},
				{ fieldtype: "Column Break" },
				{
					depends_on: "eval:doc.with_slider",
					fieldtype: df.fieldtype,
					label: __("Step Size"),
					fieldname: "step",
				}
			);
		}

		return config_fields;
	};

	const parse_validate_configuration = (config) => {
		let parsed = {};
		let errors = [];
		try {
			if (config) {
				// not null, undefined, empty string
				parsed = JSON.parse(config);
			}
		} catch (e) {
			errors.push(__("Invalid JSON"));
			errors.push(e.message);
		}
		return { errors, parsed };
	};

	const make_configuration_dialog = (frm, df, values) => {
		const fields = get_config_fields(df);
		const dialog = new frappe.ui.Dialog({
			title: __("Configure {0}", [__(df.label || df.fieldname, null, frm.doc.name)]),
			fields,
		});
		dialog.set_values(values);

		dialog.set_primary_action(__("Save"), () => {
			const new_config = dialog.get_values();
			df.configuration = JSON.stringify(new_config);
			frm.refresh();
			frm.dirty();
			dialog.hide();
		});

		return dialog;
	};

	// "DocField", "Customize Form Field", "Web Form Field"
	field_dt = field_dt || (frm.doctype === "DocType" ? "DocField" : `${frm.doctype} Field`);

	frappe.ui.form.on(field_dt, {
		form_render: (frm, cdt, cdn) => {
			const row_frm = frm.get_field(table_fieldname).grid.open_grid_row;
			const $btn = row_frm.fields_dict.configuration_button?.$input;
			if (!$btn) return;

			const df = frappe.get_doc(cdt, cdn);
			const fields = get_config_fields(df);

			$btn.removeClass("btn-default");
			$btn.addClass("btn-primary-light");
			$btn.toggleClass("hidden", !fields.length);
		},

		configuration_button: (frm, cdt, cdn) => {
			const df = frappe.get_doc(cdt, cdn);

			const { errors, parsed } = parse_validate_configuration(df.configuration);
			if (errors.length) {
				frappe.msgprint(errors.join("\n"));
				return;
			}

			const dialog = make_configuration_dialog(frm, df, parsed);
			dialog.show();
		},
	});
}
