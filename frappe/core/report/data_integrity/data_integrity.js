// Copyright (c) 2019, Dokos and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Data Integrity"] = {
	filters: [
		{
			fieldname: "doctype",
			label: __("DocType"),
			fieldtype: "Link",
			options: "DocType",
			reqd: 1,
			get_query: function () {
				return {
					query: "frappe.core.report.data_integrity.data_integrity.query_doctypes",
				};
			},
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		const icon_map = {
			success: "fa-check",
			warning: "fa-bell",
			error: "fa-exclamation",
		};
		const color_map = {
			success: "var(--alert-text-success)",
			warning: "var(--alert-text-warning)",
			error: "var(--alert-text-danger)",
		};
		const class_map = {
			warning: "alert-warning",
			error: "alert-danger",
		};
		const formatted_value = default_formatter(value, row, column, data);
		if (column.fieldname == "comments") {
			const icon = icon_map[data.icon] || "fa-question";
			const color = color_map[data.icon] || "grey";
			const c = class_map[data.icon] || "";
			return `<div class="text-left ${c}">
						<i class="fa ${icon}" style="color: ${color};"></i>
						${formatted_value}
					</div>`;
		}
		return formatted_value;
	},
};
