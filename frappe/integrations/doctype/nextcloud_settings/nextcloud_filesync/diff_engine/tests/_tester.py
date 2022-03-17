from typing import List
import unittest

import frappe  # type: ignore

from ..DiffEngine import DiffEngine
from ..ActionRunner import ActionRunner_NexcloudFrappe
from ..Common import Common
from ..RemoteFetcher import RemoteFetcher
from ..utils import get_home_folder_name, set_flag, FLAG_NEXTCLOUD_IGNORE

def using_local_files(local_files: List[dict]):
	def decorate(func):
		def wrapper(self: NextcloudTester, *args, **kwargs):
			# print('🚧 setting up local files…')
			self._local_files = []

			for d in local_files:
				try:
					# # home might not be 'Home'…
					# if 'folder' in d:
					# 	if d['folder'] == 'Home':
					# 		d['folder'] = self.home
					# 	elif d['folder'].startswith('Home/'):
					# 		d['folder'] = d['folder'].replace('Home/', self.home + '/', 1)

					doc = frappe.get_doc('File', d)
					set_flag(doc)
					if doc.is_folder:
						doc.folder_delete_children(flags={FLAG_NEXTCLOUD_IGNORE: True})
					doc.delete()
				except:
					pass

				d["doctype"] = "File"
				doc = frappe.get_doc(d)
				set_flag(doc)
				doc.insert()
				if 'file_name' in d:
					doc.db_set('file_name', d['file_name'])
				self._local_files.append(doc)

			# print('\x1b[F\x1b[2K✅ setting up local files… done')

			res = func(self, *args, **kwargs)

			for doc in self._local_files:
				set_flag(doc)
				if doc.is_folder:
					doc.folder_delete_children(flags={FLAG_NEXTCLOUD_IGNORE: True})
				doc.delete()

			self._local_files = []

			return res
		return wrapper
	return decorate


def using_remote_files(remote_files: List[str]):
	def decorate(func):
		def wrapper(self: NextcloudTester, *args, **kwargs):
			# print('🚧 setting up remote files…')
			self._remote_files = []

			for p in remote_files:
				self.remote_delete(p)
				if p.endswith('/'):
					self.remote_mk_dir(p)
				else:
					self.remote_mk_file(p)

			# print('\x1b[F\x1b[2K✅ setting up remote files… done')

			res = func(self, *args, **kwargs)

			for f in reversed(self._remote_files):
				self.remote_delete(f)

			self._remote_files = []

			return res
		return wrapper
	return decorate


def _slugify(s: str) -> str:
	import re
	return re.sub('[^a-zA-Z0-9_-]', '', s)

class NextcloudTester(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
			cls.home = get_home_folder_name()
			cls._prev_flag_value = frappe.flags.nextcloud_disable_filesync_hooks
			frappe.flags.nextcloud_disable_filesync_hooks = 1
			return super().setUpClass()

	@classmethod
	def tearDownClass(cls) -> None:
			frappe.flags.nextcloud_disable_filesync_hooks = cls._prev_flag_value
			return super().tearDownClass()

	def logger(self, *args,  **kwargs):
		print(*args, **kwargs)

	def setUp(self):
		import os
		should_test = os.getenv('CI_NEXTCLOUD_TESTS')
		if not should_test:
			msg = 'Nextcloud Integration testing is disabled by default.\nTo enable it, either set the CI_NEXTCLOUD_TESTS environment variable to `1` to run all the tests, or set it to `skip` to skip the tests.'
			if should_test == 'skip':
				raise unittest.SkipTest(msg)
			elif should_test in ('0', 'no'):
				pass
			else:
				self.fail(msg)

		if not frappe.get_single('Nextcloud Settings').enabled:
			raise unittest.SkipTest("Nextcloud Integration is disabled")

		frappe.db.rollback()
		frappe.db.begin()

		root_dir = '@test-' + _slugify(f'{self.__class__.__name__}-{self._testMethodName}')
		self.common = Common.Test(logger=self.logger, test_root_dir_name=root_dir)
		self.differ = DiffEngine(self.common)
		self.runner = ActionRunner_NexcloudFrappe(self.common)
		self.fetcher = RemoteFetcher(self.common)

		self._local_files = []
		self._remote_files = []

		self.remote_mk_dir('/')

	def tearDown(self):
		self.remote_delete('/')

		self.common = None
		self.differ = None
		self.runner = None
		self.fetcher = None

		frappe.db.rollback()

	def remote_mk_dir(self, p):
		if p != '/':
			self._remote_files.append(p)
		p = self.common.root.rstrip('/') + '/' + p.lstrip('/')
		self.common.cloud_client.mkdir_p(p)

	def remote_mk_file(self, p, c=b'1234'):
		self._remote_files.append(p)
		p = self.common.root.rstrip('/') + '/' + p.lstrip('/')
		self.common.cloud_client.put_file_contents(p, c)

	def remote_delete(self, p):
		try:
			for i, x in list(reversed(list(enumerate(self._remote_files)))):
				if x == p or x.startswith(p + '/'):
					self._remote_files.pop(i)
		except Exception as e:
			print(e)
			pass

		p = self.common.root.rstrip('/') + '/' + p.lstrip('/')
		try:
			self.common.cloud_client.delete(p)
		except Exception as e:
			return

	def remote_mv(self, a: str, b: str):
		root = '/' + self.common.root.strip('/') + '/'
		a = root + a.lstrip('/')
		b = root + b.lstrip('/')

		res = self.common.cloud_client.move(a, b)

		for i, x in enumerate(self._remote_files):
			if x == a or x.startswith(a + '/'):
				self._remote_files[i] = x.replace(a, b, 1)

		assert res == True

	def local_dir_was_renamed(self, old_name, new_name):
		for i, x in enumerate(self._local_files):
			n = x.name
			if n == old_name or n.startswith(old_name + '/'):
				self._local_files[i].name = n.replace(old_name, new_name, 1)
				self._local_files[i].reload()

	def join(self, remote_path: str, local_path: str = None):
		if local_path is None:
			local_path = remote_path
		l = self.differ.get_local_entry_by_path(local_path)
		r = self.differ.get_remote_entry_by_path(remote_path)
		assert l  # for mypy
		assert r  # for mypy
		# print('r.last_updated', r.last_updated)
		frappe.db.set_value('File', l._frappe_name, {
			# NOTE: l._frappe_name might not be synced with the actual name
			'content_hash': r.etag,
			'nextcloud_id': r.nextcloud_id,
			'nextcloud_parent_id': r.parent_id,
		}, modified=r.last_updated)

		for f in self._local_files:
			if f.name == l._frappe_name:
				f.reload()

		return r.nextcloud_id
