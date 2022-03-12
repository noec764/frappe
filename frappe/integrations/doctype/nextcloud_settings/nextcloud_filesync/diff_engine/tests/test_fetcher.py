from datetime import timedelta
import frappe  # type: ignore
from frappe.integrations.doctype.nextcloud_settings.nextcloud_filesync.diff_engine.utils_time import convert_local_time_to_utc

from ._tester import Tester, using_remote_files

class TestNCFetcher(Tester):
	@using_remote_files([
		'/fetch/',
		'/fetch/a/',
		'/fetch/a/b/',
		'/fetch/a/b/c',
	])
	def test_fetch_all(self):
		files = self.fetcher.fetch_all()
		self.assertEqual(
			len(files), # files + root (1)
			len(self._remote_files) + 1,
		)

		n = len(self.common.remote_prefix_to_remove)
		remote_file_paths = {f.path[n:].rstrip('/') + ('/' if f.is_dir() else '') for f in files}

		expect_file_paths = set(self._remote_files)
		expect_file_paths.add('/') # add root

		self.assertEqual(remote_file_paths, expect_file_paths)

	def test_fetch_since(self):
		now_dt = frappe.utils.now_datetime()
		before_now_dt = now_dt - timedelta(hours=1)

		s = convert_local_time_to_utc(now_dt).strftime('%FT%TZ')
		self.remote_mk_file(f'/file created after {s.replace(":",".")}')

		files = self.fetcher.fetch_since_utc(convert_local_time_to_utc(before_now_dt))
		self.assertEqual(len(files), 2) # root + the file


	def test_fetch_not_too_much(self):
		now_dt = frappe.utils.now_datetime()
		after_now_dt = now_dt + timedelta(hours=1)

		s = convert_local_time_to_utc(now_dt).strftime('%FT%TZ')
		self.remote_mk_file(f'/file created after {s.replace(":",".")}')

		files = self.fetcher.fetch_since_utc(convert_local_time_to_utc(after_now_dt))
		self.assertEqual(len(files), 1) # just the root, always included

	@using_remote_files([
		'/yes/',
		'/yes/yes/',

		'/.no/',
		'/.no/no/',
		'/yes/yes/.no',
		'/.no/no/.no',
	])
	def test_filter_works_dotfiles(self):
		all_files = self.fetcher.fetch_all()
		self.assertEqual(len(all_files), 2 + 1)  # filtered plus root
		self.assertTrue(all(
			('no' not in x.path)
			or (x.path == self.common.root)
			for x in all_files
		))
