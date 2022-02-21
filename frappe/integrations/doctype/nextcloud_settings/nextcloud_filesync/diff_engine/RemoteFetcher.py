from datetime import datetime
from operator import attrgetter
from typing import List

from owncloud import HTTPResponseError, FileInfo  # type: ignore

from .Common import Common


class RemoteFetcher:
	def __init__(self, common: Common):
		super().__init__()
		self.common = common

		self.cloud_client = common.cloud_client
		self.cloud_settings = common.cloud_settings
		self.logger = common.logger
		self._FILE_ID = common._FILE_ID
		self._QUERY_PROPS = common._QUERY_PROPS
		self.root = common.root

		self.last_update = None

	def _filter(self, files: List[FileInfo]) -> List[FileInfo]:
		def f(file: FileInfo) -> bool:
			path = file.path
			return all((
				path.startswith(self.common.root),
				'/.' not in path[len(self.common.root)-1:],
			))
		return list(filter(f, files))

	def fetch_root(self) -> FileInfo:
		p = self.root.strip('/')
		props = self._QUERY_PROPS
		try:
			return self.cloud_client.file_info(p, properties=props)
		except HTTPResponseError as e:
			if e.status_code == 404:
				self.cloud_client.mkdir_p(p)
				msg = f'initializing empty root directory on remote ({p})'
				self.logger(msg)

				f = self.cloud_client.file_info(p, properties=props)
				if f:
					self.logger('-> ok')
					return f

				self.logger('-> failed to create root directory ({p})')
				raise Exception('failed to create root directory')
			else:
				raise
		except Exception as e:
			raise Exception(['failed to fetch root directory', e])

	def fetch_all(self):
		root = self.fetch_root()

		files: List[FileInfo] = self.cloud_client.list(
			self.root.strip('/'),
			depth='infinity',
			properties=self._QUERY_PROPS,
		) or []

		files = self._filter(files)

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

		root = self.fetch_root()

		files: List[FileInfo] = self.cloud_client.list_updated_since(
			last_update,
			path=self.root.strip('/')
		) or []

		files = self._filter(files)

		# insert in first position, even if there is a subsequent sorting
		files.insert(0, root)
		return files


# def main():
# 	from .DiffEngine import DiffEngine
# 	from frappe.integrations.doctype.nextcloud_settings import get_nextcloud_settings_and_client  # type: ignore

# 	def logger(*args, **kwargs):
# 		print('\x1b[35;1m×\x1b[m', *args, **kwargs)

# 	common = Common(*get_nextcloud_settings_and_client(), logger)
# 	fetcher = RemoteFetcher(common)
# 	convert = fetcher.common.convert_remote_file_to_entry

# 	files = fetcher.fetch_all()
# 	files.sort(key=attrgetter('path'))
# 	files = list(map(convert, files))
# 	for f in files:
# 		print(f.last_updated, f)
# 	else:
# 		print('no files found')

# 	print('\x1b[32;2m' + '- '*20 + '\x1b[m')

# 	fetcher.last_update = '2021-12-15 18:00:00'
# 	print(f"Query is:\nUPDATED SINCE\n   {fetcher.last_update}")
# 	files = fetcher.fetch_since_last_update()
# 	files.sort(key=attrgetter('path'))
# 	files = list(map(convert, files))
# 	for f in files:
# 		print(' ·', f.last_updated, f.path)
# 	else:
# 		print('no files found')

# 	print()

# 	most_recent_changed_file = max(files, key=attrgetter('last_updated'))
# 	print(f'last change: {most_recent_changed_file.last_updated}')

# 	differ = DiffEngine(common)
# 	actions = differ.diff_from_remote(files)
# 	for action in actions:
# 		print(' •', action)
