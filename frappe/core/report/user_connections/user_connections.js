// Copyright (c) 2023, Dokos SAS and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["User Connections"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
	],
};
