frappe.ui.form.on("Web Form", {
	setup: function (frm) {
		frappe.meta.docfield_map["Web Form Field"].fieldtype.formatter = (value) => {
			const prefix = {
				"Page Break": "--red-600",
				"Section Break": "--blue-600",
				"Column Break": "--yellow-600",
			};
			const label = __(value, null, "DocField");
			if (prefix[value]) {
				return `<span class="bold" style="color: var(${prefix[value]})">${label}</span>`;
			}
			return label;
		};

		frappe.meta.docfield_map["Web Form Field"].fieldname.formatter = (value) => {
			if (!value) return;
			return (
				frappe.get_meta(frm.doc.doc_type)?.fields?.find((x) => x.fieldname === value)
					?.label ?? value
			);
		};

		frappe.meta.docfield_map["Web Form List Column"].fieldname.formatter = (value) => {
			return frappe.meta.docfield_map["Web Form Field"].fieldname.formatter(value);
		};

		frappe.model.DocTypeController.setup_docfield_configuration(
			frm,
			"Web Form Field",
			"web_form_fields"
		);
	},

	refresh: function (frm) {
		// show is-standard only if developer mode
		frm.get_field("is_standard").toggle(frappe.boot.developer_mode);

		if (frm.doc.is_standard && !frappe.boot.developer_mode) {
			frm.set_read_only();
			frm.disable_save();
		}
		render_list_settings_message(frm);

		frm.add_custom_button(__("Show List"), () => {
			frappe.router.set_route("List", frm.doc.doc_type);
		});

		frm.trigger("set_fields");
		frm.trigger("add_get_fields_button");
		frm.trigger("add_publish_button");
		frm.trigger("render_condition_table");
	},

	login_required: function (frm) {
		render_list_settings_message(frm);
	},

	anonymous: function (frm) {
		if (frm.doc.anonymous) {
			frm.set_value("login_required", 0);
		}
	},

	validate: function (frm) {
		if (!frm.doc.login_required) {
			frm.set_value("allow_multiple", 0);
			frm.set_value("allow_edit", 0);
			frm.set_value("show_list", 0);
		}

		!frm.doc.allow_multiple && frm.set_value("allow_delete", 0);
		frm.doc.allow_multiple && frm.set_value("show_list", 1);

		if (!frm.doc.web_form_fields) {
			frm.scroll_to_field("web_form_fields");
			frappe.throw(__("Atleast one field is required in Web Form Fields Table"));
		}

		let page_break_count = frm.doc.web_form_fields.filter(
			(f) => f.fieldtype == "Page Break"
		).length;

		if (page_break_count >= 10) {
			frappe.throw(__("There can be only 9 Page Break fields in a Web Form"));
		}
	},

	add_publish_button(frm) {
		frm.add_custom_button(
			frm.doc.published ? __("Unpublish", [], "Web Form") : __("Publish", [], "Web Form"),
			() => {
				frm.set_value("published", !frm.doc.published);
				frm.save();
			}
		)
			.removeClass("btn-default")
			.addClass(frm.doc.published ? "btn-danger" : "btn-default");
	},

	add_get_fields_button(frm) {
		frm.add_custom_button(__("Get Fields"), () => {
			let webform_fieldtypes = frappe.meta
				.get_field("Web Form Field", "fieldtype")
				.options.split("\n");

			let added_fields = (frm.doc.web_form_fields || []).map((d) => d.fieldname);

			get_fields_for_doctype(frm.doc.doc_type).then((fields) => {
				for (let df of fields) {
					let fieldtype = df.fieldtype;
					if (fieldtype == "Tab Break") {
						fieldtype = "Page Break";
					}
					if (
						webform_fieldtypes.includes(fieldtype) &&
						!added_fields.includes(df.fieldname) &&
						!df.hidden
					) {
						frm.add_child("web_form_fields", {
							fieldname: df.fieldname,
							label: df.label,
							fieldtype: fieldtype,
							options: df.options,
							reqd: df.reqd,
							default: df.default,
							read_only: df.read_only,
							depends_on: df.depends_on,
							mandatory_depends_on: df.mandatory_depends_on,
							read_only_depends_on: df.read_only_depends_on,
						});
					}
				}
				frm.refresh_field("web_form_fields");
				frm.scroll_to_field("web_form_fields");
			});
		});
	},

	set_fields(frm) {
		let doc = frm.doc;

		let update_options = (options) => {
			[frm.fields_dict.web_form_fields.grid, frm.fields_dict.list_columns.grid].forEach(
				(obj) => {
					obj.update_docfield_property("fieldname", "options", options);
				}
			);
		};

		if (!doc.doc_type) {
			update_options([]);
			frm.set_df_property("amount_field", "options", []);
			return;
		}

		update_options([`Fetching fields from ${doc.doc_type}...`]);

		get_fields_for_doctype(doc.doc_type).then((fields) => {
			let as_select_option = (df) => ({
				label: df.label,
				value: df.fieldname,
			});
			fields.push({ label: "Name", fieldname: "name" });
			update_options(fields.map(as_select_option));

			const amount_fields = fields
				.filter((df) => ["Currency", "Float"].includes(df.fieldtype))
				.map(as_select_option);
			if (amount_fields.length === 0) {
				amount_fields.push({
					label: __("No Currency/Float fields in {0}", [__(doc.doc_type)], "Web Form"),
					value: "",
					disabled: true,
				});
			}
			frm.set_df_property("amount_field", "options", amount_fields);

			const currency_fields = fields
				.filter((df) => df.fieldtype === "Link")
				.filter((df) => df.options === "Currency")
				.map(as_select_option);
			if (currency_fields.length === 0) {
				currency_fields.push({
					label: __("No Link to Currency fields in {0}", [__(doc.doc_type)], "Web Form"),
					value: "",
					disabled: true,
				});
			}
			frm.set_df_property("currency_field", "options", currency_fields);
		});
	},

	title: function (frm) {
		if (frm.doc.__islocal) {
			var page_name = frm.doc.title.toLowerCase().replace(/ /g, "-");
			frm.set_value("route", page_name);
		}
	},

	doc_type: function (frm) {
		frm.trigger("set_fields");
	},

	allow_multiple: function (frm) {
		frm.doc.allow_multiple && frm.set_value("show_list", 1);
	},

	before_save: function (frm) {
		let static_filters = JSON.parse(frm.doc.condition_json || "[]");
		frm.set_value("condition_json", JSON.stringify(static_filters));
		frm.trigger("render_condition_table");
	},

	render_condition_table: function (frm) {
		// frm.set_df_property("filters_section", "hidden", 0);
		let is_document_type = true;

		let wrapper = $(frm.get_field("condition_json").wrapper).empty();
		let table = $(`<table class="table table-bordered" style="cursor:pointer; margin:0px;">
			<thead>
				<tr>
					<th style="width: 20%">${__("Filter")}</th>
					<th style="width: 20%">${__("Condition")}</th>
					<th>${__("Value")}</th>
				</tr>
			</thead>
			<tbody></tbody>
		</table>`).appendTo(wrapper);
		$(`<p class="text-muted small">${__("Click table to edit")}</p>`).appendTo(wrapper);

		let filters = JSON.parse(frm.doc.condition_json || "[]");
		let filters_set = false;

		let fields = [];
		if (is_document_type) {
			fields = [
				{
					fieldtype: "HTML",
					fieldname: "filter_area",
				},
			];

			if (filters?.length) {
				filters.forEach((filter) => {
					const filter_row = $(`<tr>
							<td>${filter[1]}</td>
							<td>${filter[2] || ""}</td>
							<td>${filter[3]}</td>
						</tr>`);

					table.find("tbody").append(filter_row);
				});
				filters_set = true;
			}
		} else if (frm.filters.length) {
			fields = frm.filters.filter((f) => f.fieldname);
			fields.map((f) => {
				if (filters[f.fieldname]) {
					let condition = "=";
					const filter_row = $(`<tr>
							<td>${f.label}</td>
							<td>${condition}</td>
							<td>${filters[f.fieldname] || ""}</td>
						</tr>`);
					table.find("tbody").append(filter_row);
					if (!filters_set) filters_set = true;
				}
			});
		}

		if (!filters_set) {
			const filter_row = $(`<tr><td colspan="3" class="text-muted text-center">
				${__("Click to Set Filters")}</td></tr>`);
			table.find("tbody").append(filter_row);
		}

		table.on("click", () => {
			let dialog = new frappe.ui.Dialog({
				title: __("Set Filters"),
				fields: fields,
				primary_action: function () {
					let values = this.get_values();
					if (values) {
						this.hide();
						if (is_document_type) {
							let filters = frm.filter_group.get_filters();
							frm.set_value("condition_json", JSON.stringify(filters));
						} else {
							frm.set_value("condition_json", JSON.stringify(values));
						}
						frm.trigger("render_condition_table");
					}
				},
				primary_action_label: "Set",
			});

			if (is_document_type) {
				frm.filter_group = new frappe.ui.FilterGroup({
					parent: dialog.get_field("filter_area").$wrapper,
					doctype: frm.doc.doc_type,
					on_change: () => {},
				});
				filters && frm.filter_group.add_filters_to_filter_group(filters);
			}

			dialog.show();

			dialog.set_values(filters);
		});
	},
});

frappe.ui.form.on("Web Form List Column", {
	fieldname: function (frm, doctype, name) {
		let doc = frappe.get_doc(doctype, name);
		if (doc.fieldname == "name") {
			doc.fieldtype = "Data";
			doc.label = "Name";
		} else {
			let df = frappe.meta.get_docfield(frm.doc.doc_type, doc.fieldname);
			if (!df) return;
			doc.fieldtype = df.fieldtype;
			doc.label = df.label;
		}
		frm.refresh_field("list_columns");
	},
});

frappe.ui.form.on("Web Form Field", {
	fieldtype: function (frm, doctype, name) {
		let doc = frappe.get_doc(doctype, name);

		if (doc.fieldtype == "Page Break") {
			let page_break_count = frm.doc.web_form_fields.filter(
				(f) => f.fieldtype == "Page Break"
			).length;
			page_break_count >= 10 &&
				frappe.throw(__("There can be only 9 Page Break fields in a Web Form"));
		}

		if (["Section Break", "Column Break", "Page Break"].includes(doc.fieldtype)) {
			doc.fieldname = "";
			doc.label = "";
			doc.options = "";
			frm.refresh_field("web_form_fields");
		}
	},
	fieldname: function (frm, doctype, name) {
		let doc = frappe.get_doc(doctype, name);
		let df = frappe.meta.get_docfield(frm.doc.doc_type, doc.fieldname);
		if (!df) return;

		doc.label = df.label;
		doc.fieldtype = df.fieldtype;
		doc.options = df.options;
		doc.reqd = df.reqd;
		doc.default = df.default;
		doc.read_only = df.read_only;
		doc.depends_on = df.depends_on;
		doc.mandatory_depends_on = df.mandatory_depends_on;
		doc.read_only_depends_on = df.read_only_depends_on;

		frm.refresh_field("web_form_fields");
	},
});

function get_fields_for_doctype(doctype) {
	return new Promise((resolve) => frappe.model.with_doctype(doctype, resolve)).then(() => {
		return frappe.meta.get_docfields(doctype).filter((df) => {
			return (
				(frappe.model.is_value_type(df.fieldtype) &&
					!["lft", "rgt"].includes(df.fieldname)) ||
				["Table", "Table Multiselect"].includes(df.fieldtype) ||
				frappe.model.layout_fields.includes(df.fieldtype)
			);
		});
	});
}

function render_list_settings_message(frm) {
	// render list setting message
	if (frm.fields_dict["list_setting_message"] && !frm.doc.login_required) {
		const login_required_label = frappe
			.get_meta("Web Form")
			.fields.find((x) => x.fieldname === "login_required").label;
		const go_to_login_required_field = `
			<a class="pointer" title="${__("Go to Login Required field")}" href="#">${__(
			login_required_label
		)}</a>
		`;
		let message = __(
			"Login is required to see web form list view. Enable {0} to see list settings",
			[go_to_login_required_field]
		);
		$(frm.fields_dict["list_setting_message"].wrapper)
			.html($(`<div class="form-message blue">${message}</div>`))
			.find("a")
			.on("click", () => frm.scroll_to_field("login_required"));
	} else {
		$(frm.fields_dict["list_setting_message"].wrapper).empty();
	}
}
