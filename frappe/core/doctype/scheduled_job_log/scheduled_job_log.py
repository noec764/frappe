# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies and contributors
# License: MIT. See LICENSE


import frappe
from frappe.model.document import Document
from frappe.utils import cint


class ScheduledJobLog(Document):
	pass


def flush():
	if cint(frappe.get_system_settings("restricted_jobs_logs")):
		frappe.db.sql(
			"""
			DELETE FROM `tabScheduled Job Log`
			WHERE datediff(curdate(), creation) > 30
		"""
		)
