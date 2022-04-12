# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies and contributors
# License: MIT. See LICENSE


import frappe
from frappe.model.document import Document
from frappe.translate import clear_cache
from frappe.utils import is_html, strip_html_tags


class Translation(Document):
	def validate(self):
		if is_html(self.source_text):
			self.remove_html_from_source()

	def remove_html_from_source(self):
		self.source_text = strip_html_tags(self.source_text).strip()

	def on_update(self):
		clear_user_translation_cache(self.language)

	def on_trash(self):
		clear_user_translation_cache(self.language)


def clear_user_translation_cache(lang):
	frappe.cache().hdel("lang_user_translations", lang)
