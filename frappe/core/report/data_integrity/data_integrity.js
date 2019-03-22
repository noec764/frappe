// Copyright (c) 2019, Dokos and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Data Integrity"] = {
	"filters": [
		{
			"fieldname":"doctype",
			"label": __("DocType"),
			"fieldtype": "Link",
			"options": "DocType",
			"reqd": 1,
			"get_query": function () {
				return {
					"query": "frappe.core.report.data_integrity.data_integrity.query_doctypes"
				}
			}
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {

		if (column.fieldname == "integrity") {

			return repl('<div class="text-center"><i class="fa %(icon)s" style="color: %(color)s;"></i></div>', {
				icon: (value=="Yes") ? "fa-check": (value=="Out") ? "fa-bell" : "fa-exclamation",
				color: (value=="Yes") ? "green": (value=="Out") ? "orange" : "red"
			});

		}

		return value;
	}
}
