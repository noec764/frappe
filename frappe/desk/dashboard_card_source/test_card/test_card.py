# Copyright (c) 2019, Dokos and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.utils import add_to_date, date_diff, getdate, nowdate, get_last_day
from frappe.core.page.dashboard.dashboard import cache_card_source, get_from_date_from_timespan
from frappe.desk.doctype.dashboard_chart.dashboard_chart import get_period_ending

from frappe.utils.nestedset import get_descendants_of

@frappe.whitelist()
@cache_card_source
def get(card_name, from_date=None, to_date=None):
	card = frappe.get_doc('Dashboard Card', card_name)
	timespan = card.timespan

	if not to_date:
		to_date = nowdate()
	if not from_date:
		from_date = get_from_date_from_timespan(to_date, timespan)

	return 500000000000000000


def get_activity_logs(from_date):
	return frappe.db.get_all('Activity Log', fields=['COUNT(name) as total'], filters=[dict(creation = ('>', from_date))])