import frappe  # type: ignore

from ._tester import NextcloudTester, using_local_files, using_remote_files


FILENAME_TEST_timezone = '__test Time Zone is converted to UTC.txt'


class TestNCOther(NextcloudTester):
	@using_remote_files(['/' + FILENAME_TEST_timezone])
	@using_local_files([
		dict(file_name=FILENAME_TEST_timezone, folder='Home', content=b'x')
	])
	def test_timezone_is_utc(self):
		r = self.differ.get_remote_entry_by_path('/' + FILENAME_TEST_timezone)
		l = self.differ.get_local_entry_by_path('/' + FILENAME_TEST_timezone)

		# allow for a few seconds difference
		allowed_delta = 60
		delta = (r.last_updated - l.last_updated).total_seconds()
		self.assertAlmostEqual(delta, 0, delta=allowed_delta)
