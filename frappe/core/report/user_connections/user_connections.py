# Copyright (c) 2023, Dokos SAS and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Date


def execute(filters=None):
	data, user_types = get_data(filters)
	return get_columns(user_types), data, None, get_chart(data, user_types)


def get_data(filters):
	activity_log = frappe.qb.DocType("Activity Log")
	user = frappe.qb.DocType("User")

	query = (
		frappe.qb.from_(activity_log)
		.select(
			Date(activity_log.communication_date).as_("date"),
			user.user_type,
			Count(activity_log.name).as_("connections"),
		)
		.left_join(user)
		.on(user.name == activity_log.user)
		.where((activity_log.operation == "Login") & (activity_log.status == "Success"))
		.groupby(user.user_type)
		.groupby(Date(activity_log.communication_date))
		.orderby(Date(activity_log.communication_date), order=frappe.qb.desc)
	)

	if filters.get("from_date"):
		query = query.where(Date(activity_log.communication_date) >= filters.get("from_date"))

	result = query.run(as_dict=True, debug=True)

	user_types = set()
	rows_by_date = defaultdict(dict)
	output = []
	for res in result:
		rows_by_date[res.get("date")][frappe.scrub(res.get("user_type"))] = res.get("connections")
		user_types.add(res.get("user_type"))

	for d in rows_by_date:
		new_row = {
			"date": d,
		}
		new_row.update(rows_by_date[d])

		output.append(new_row)

	return output, user_types


def get_columns(user_types):
	columns = [{"fieldtype": "Data", "fieldname": "date", "label": _("Date"), "width": 150}]

	for user_type in user_types:
		columns.append(
			{"fieldtype": "Data", "fieldname": frappe.scrub(user_type), "label": _(user_type), "width": 200}
		)

	return columns


def get_chart(data, user_types):
	labels = [d.get("date") for d in data]
	chart = {
		"data": {
			"labels": labels,
			"datasets": [],
		},
		"type": "bar",
		"colors": [
			"#00bdff",
			"#1b3bff",
			"#8F00FF",
			"#ff0011",
			"#ff7300",
			"#ffd600",
			"#00c30e",
			"#65ff00",
			"#d200ff",
			"#FF00FF",
			"#7d7d7d",
			"#5d5d5d",
		],
	}

	for user_type in user_types:
		chart["data"]["datasets"].append(
			{
				"name": _(user_type),
				"values": [d.get(frappe.scrub(user_type), 0) for d in data],
				"chartType": "bar",
			}
		)

	return chart
