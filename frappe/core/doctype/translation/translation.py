# Copyright (c) 2021, Frappe Technologies and contributors
# License: MIT. See LICENSE


import frappe
from frappe.model.document import Document
from frappe.translate import MERGED_TRANSLATION_KEY, USER_TRANSLATION_KEY
from frappe.utils import is_html, strip_html_tags


class Translation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		context: DF.Data | None
		language: DF.Link
		source_text: DF.Code
		translated_text: DF.Code
	# end: auto-generated types

	def validate(self):
		if is_html(self.source_text):
			self.remove_html_from_source()

	def remove_html_from_source(self):
		self.source_text = strip_html_tags(self.source_text).strip()

	def on_update(self):
		clear_user_translation_cache(self.language)

	def after_delete(self):
		clear_user_translation_cache(self.language)


def clear_user_translation_cache(lang):
	frappe.cache.hdel(USER_TRANSLATION_KEY, lang)
	frappe.cache.hdel(MERGED_TRANSLATION_KEY, lang)
