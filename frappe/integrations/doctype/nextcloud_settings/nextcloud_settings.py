# Copyright (c) 2022, Dokos SAS and contributors
# For license information, please see license.txt

import os
from datetime import datetime

import frappe
from frappe.model.document import Document
from frappe.utils.data import cint

from owncloud import HTTPResponseError

from .client import NextcloudIntegrationClient
from .exceptions import NextcloudExceptionInvalidCredentials, NextcloudExceptionServerIsDown

if any((os.getenv('CI'), frappe.conf.developer_mode, frappe.conf.allow_tests)):
	# Do not check certificates when in developer mode or while testing
	os.environ['NEXTCLOUD_DONT_VERIFY_CERTS'] = '1'
	# os.environ['CI_NEXTCLOUD_DISABLE'] = '1'

if os.getenv('NEXTCLOUD_FORCE_VERIFY_CERTS'):
	os.environ['NEXTCLOUD_DONT_VERIFY_CERTS'] = ''

class NextcloudSettings(Document):
	enabled: bool = False
	cloud_url: str = ''
	username: str = ''
	# password: str = ''

	enable_sync: bool = False
	# enable_backups: bool = False
	# enable_calendar: bool = False

	path_to_files_folder: str = ''

	# TODO: store sync_datetime for each of the 3 modules + configurable interval
	last_filesync_dt: str = None

	# TODO: remove these properties (conflict override)
	next_filesync_ignore_id_conflicts: bool = False
	filesync_override_conflict_strategy: str = ''

	def _get_credentials(self):
		password: str = self.get_password(fieldname='password', raise_exception=False)
		username: str = self.username
		return username, password

	def _get_cloud_base_url(self):
		from urllib.parse import urlsplit, urlunsplit
		o = urlsplit(self.cloud_url)
		clean_url = urlunsplit((o.scheme, o.netloc, '', '', ''))
		return clean_url.strip('/')

	def nc_connect(self, **kwargs):
		if not self.nc_ping_server():
			raise NextcloudExceptionServerIsDown

		username, password = self._get_credentials()
		cloud_url = self._get_cloud_base_url() + '/'

		verify_certs = not cint(os.environ.get('NEXTCLOUD_DONT_VERIFY_CERTS', False))
		client = NextcloudIntegrationClient(cloud_url, verify_certs=verify_certs, **kwargs)
		try:
			client.login(username, password)
			client.list('/', depth=0, properties=[])  # query to check that credentials are valid
			# https://github.com/nextcloud/server/issues/13561
		except HTTPResponseError as e:
			if e.status_code == 401:
				# unauthorized access (probably invalid credentials)
				raise NextcloudExceptionInvalidCredentials
			else:
				raise
		except Exception as e:
			raise

		return client

	def nc_ping_server(self, n_tries = 2, t_timeout = 5):
		from urllib.parse import urlsplit
		url = self._get_cloud_base_url().strip('/')
		o = urlsplit(url)
		default_port = {'http': 80, 'https': 443}
		port = o.port or default_port.get(o.scheme, 80)
		host = o.hostname

		if not host:
			raise ValueError(frappe._('Invalid URL'))

		import socket
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(t_timeout)

		for _ in range(n_tries):
			res = sock.connect_ex((host, port))
			if res == 0:
				return True
		return False

	def get_path_to_files_folder(self):
		return self.path_to_files_folder

	def get_last_filesync_dt(self):
		return frappe.utils.get_datetime(self.last_filesync_dt)

	def set_last_filesync_dt(self, dt_local: datetime):
		self.db_set('last_filesync_dt', dt_local, update_modified=False)
