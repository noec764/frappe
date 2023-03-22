# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE


from frappe.model.dynamic_links import get_dynamic_link_map, legacy_get_dynamic_link_map
from frappe.tests.utils import FrappeTestCase


class TestDynamicLinkMap(FrappeTestCase):
	def test_get_dynamic_link_map_for_doctype(self):
		self.assertEqual(get_dynamic_link_map(), legacy_get_dynamic_link_map())
