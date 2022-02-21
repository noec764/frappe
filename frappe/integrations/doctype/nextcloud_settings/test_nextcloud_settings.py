# Copyright (c) 2022, Dokos SAS and Contributors
# See license.txt

import frappe
import unittest

from frappe.integrations.doctype.nextcloud_settings import get_nextcloud_settings

from .nextcloud_filesync.tests import *

class TestNextcloudSettings(unittest.TestCase):
	def setUp(self):
		if not get_nextcloud_settings().enabled:
			raise unittest.SkipTest("Nextcloud Integration is disabled")

	def test_canConnect(self):
		settings = get_nextcloud_settings()
		self.assertTrue(settings.enabled)

		cloud_client = settings.nc_connect()
		self.assertIsNotNone(cloud_client)
