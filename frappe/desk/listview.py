# Copyright (c) 2019, Dokos and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import json

@frappe.whitelist()
def get_user_assignments_and_count(doctype, current_filters):

	subquery_condition = ''
	if current_filters:
		# get the subquery
		subquery = frappe.get_all(doctype,
			filters=current_filters, return_query = True)
		subquery_condition = ' and `tabToDo`.reference_name in ({subquery})'.format(subquery = subquery)

	todo_list = frappe.db.sql("""select `tabToDo`.owner as name, count(*) as count
		from
			`tabToDo`, `tabUser`
		where
			`tabToDo`.status='Open' and
			`tabToDo`.owner = `tabUser`.name and
			`tabUser`.user_type = 'System User' 
			{subquery_condition}
		group by
			`tabToDo`.owner
		order by
			count desc
		limit 50""".format(subquery_condition = subquery_condition), as_dict=True)

	return todo_list

@frappe.whitelist()
def get_group_by_count(doctype, current_filters, field):
	current_filters = frappe.parse_json(current_filters)
	subquery_condition = ''

	subquery = frappe.get_all(doctype, filters=current_filters, return_query = True)
	if field == 'assigned_to':
		subquery_condition = ' and `tabToDo`.reference_name in ({subquery})'.format(subquery = subquery)
		return frappe.db.sql("""select `tabToDo`.owner as name, count(*) as count
			from
				`tabToDo`, `tabUser`
			where
				`tabToDo`.status='Open' and
				`tabToDo`.owner = `tabUser`.name and
				`tabUser`.user_type = 'System User'
				{subquery_condition}
			group by
				`tabToDo`.owner
			order by
				count desc
			limit 50""".format(subquery_condition = subquery_condition), as_dict=True)
	else :
		return frappe.db.get_list(doctype,
			filters=current_filters,
			group_by=field,
			fields=['count(*) as count', '`{}` as name'.format(field)],
			order_by='count desc',
			limit=50,
		)