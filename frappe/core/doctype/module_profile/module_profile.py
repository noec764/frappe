# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class ModuleProfile(Document):
	def onload(self):
		workspaces = frappe.get_all("Workspace", pluck="module", filters={"for_user": ""}, distinct=1)
		all_modules = [{"name": m, "label": _(m)} for m in workspaces if m is not None]
		all_modules.sort(key=lambda x: x["label"])
		self.set_onload("all_modules", all_modules)
