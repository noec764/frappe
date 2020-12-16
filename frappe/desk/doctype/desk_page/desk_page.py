# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.data import validate_json_string
from frappe.modules.export_file import export_to_files
from frappe.model.document import Document

class DeskPage(Document):
	def validate(self):
		self.validate_cards_json()
		if (self.is_standard and not frappe.conf.developer_mode and not disable_saving_as_standard()):
			frappe.throw(_("You need to be in developer mode to edit this document"))

	def validate_cards_json(self):
		for card in self.cards:
			try:
				validate_json_string(card.links)
			except frappe.ValidationError:
				frappe.throw(_("Invalid JSON in card links for {0}").format(frappe.bold(card.label)))

	def on_update(self):
		if disable_saving_as_standard():
			return

		if frappe.conf.developer_mode and self.is_standard:
			export_to_files(record_list=[['Desk Page', self.name]], record_module=self.module)

	@staticmethod
	def get_module_page_map():
		filters = {
			'extends_another_page': 0,
			'for_user': '',
		}

		pages = frappe.get_all("Desk Page", fields=["name", "module", "restrict_to_domain"], filters=filters)

		# add settings page
		pages.append({'name': 'Settings', 'module': 'Settings', 'restrict_to_domain': None})

		pages_map = {}

		for page in pages:
			if page.module and page.module not in pages_map:
				pages_map[page.module] = page.name
			elif page.module and page.module in pages_map and (page.name == page.module or not page.restrict_to_domain):
				pages_map[page.module] = page.name

		return pages_map

def disable_saving_as_standard():
	return frappe.flags.in_install or \
			frappe.flags.in_patch or \
			frappe.flags.in_test or \
			frappe.flags.in_fixtures or \
			frappe.flags.in_migrate