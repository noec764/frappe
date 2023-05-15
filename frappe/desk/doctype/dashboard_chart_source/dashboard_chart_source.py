# Copyright (c) 2021, Frappe Technologies and contributors
# License: MIT. See LICENSE

import os

import frappe
from frappe.model.document import Document
from frappe.modules import get_module_path, make_boilerplate, scrub
from frappe.modules.export_file import export_to_files


@frappe.whitelist()
def get_config(name):
	doc = frappe.get_doc("Dashboard Chart Source", name)
	with open(
		os.path.join(
			get_module_path(doc.module),
			"dashboard_chart_source",
			scrub(doc.name),
			scrub(doc.name) + ".js",
		),
	) as f:
		return f.read()


class DashboardChartSource(Document):
	def on_update(self):
		if frappe.conf.developer_mode and not frappe.flags.in_migrate:
			export_to_files(
				record_list=[[self.doctype, self.name]], record_module=self.module, create_init=True
			)
			make_boilerplate("controller.js", self, {"name": self.name}, "desk")
			make_boilerplate("controller.py", self, {"name": self.name}, "desk")
