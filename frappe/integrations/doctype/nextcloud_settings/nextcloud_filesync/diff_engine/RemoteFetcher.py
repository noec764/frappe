from datetime import datetime
from typing import List

from owncloud import HTTPResponseError, FileInfo

from frappe.integrations.doctype.nextcloud_settings.exceptions import NextcloudSyncCannotCreateRoot, NextcloudSyncCannotFetchRoot, NextcloudSyncMissingRoot

from .Common import Common

class RemoteFetcher:
	def __init__(self, common: Common):
		super().__init__()

		self.filter = common._filter
		self.properties = common._QUERY_PROPS
		self.client = common.cloud_client
		self.root = common.root
		self.log = common.logger

		self.last_update = None

	def create_root(self) -> FileInfo:
		p = self.root
		self.client.mkdir_p(p)
		msg = f'initializing empty root directory on remote ({p})'
		self.log(msg)

		f = self.client.file_info(p, properties=self.properties)
		if f:
			self.log('-> ok')
			return f

		self.log('-> failed to create root directory ({p})')
		raise NextcloudSyncCannotCreateRoot()

	def fetch_root(self, create_if_missing=False) -> FileInfo:
		p = self.root
		try:
			return self.client.file_info(p, properties=self.properties)
		except HTTPResponseError as e:
			if e.status_code == 404:
				if create_if_missing:
					return self.create_root()
				else:
					raise NextcloudSyncMissingRoot()
			else:
				raise
		except Exception as e:
			raise NextcloudSyncCannotFetchRoot()

	def fetch_all(self):
		root = self.fetch_root(create_if_missing=True)

		files: List[FileInfo] = self.client.list(
			self.root,
			depth='infinity',
			properties=self.properties,
		) or []

		files = self.filter(files)

		# insert in first position, even if there is a subsequent sorting
		files.insert(0, root)
		return files

	def fetch_since_utc(self, _last_update: datetime = None):
		"""Make sure that the _last_update parameter is in UTC"""
		return self.fetch_since_last_update(_last_update)

	def fetch_since_last_update(self, _last_update: datetime = None):
		last_update = _last_update or self.last_update
		if last_update is None:
			return self.fetch_all()

		root = self.fetch_root(create_if_missing=True)

		files: List[FileInfo] = self.client.list_updated_since(
			last_update,
			path=self.root
		) or []

		files = self.filter(files)

		# insert in first position, even if there is a subsequent sorting
		files.insert(0, root)
		return files
