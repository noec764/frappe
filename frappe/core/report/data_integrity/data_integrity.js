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
		if(!value){
			value = __("Error")
		}

		if (column.fieldname == "integrity") {

			if (isNaN(value)) value = '';
			return repl('<div class="text-center"><i class="fa %(icon)s" style="color: %(color)s;"></i></div>', {
				icon: (value==true) ? "fa-check": "fa-exclamation",
				color: (value==true) ? "green": "red"
			});

		}

		return value;
	}
}
