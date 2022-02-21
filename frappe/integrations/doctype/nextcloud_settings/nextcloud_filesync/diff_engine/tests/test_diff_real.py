import frappe  # type: ignore

from ._tester import Tester, using_local_files, using_remote_files


class TestNCDiffing(Tester):
	@using_remote_files([
		'/cross_rename/',

		# a -> x
		'/cross_rename/a/',
		'/cross_rename/a/b/',
		'/cross_rename/a/b/c',
		'/cross_rename/a/b/created',

		# x -> a
		'/cross_rename/x/',
		'/cross_rename/x/y/',
		'/cross_rename/x/y/z',
		'/cross_rename/x/y/deleted',
	])
	@using_local_files([
		dict(file_name='cross_rename', folder='Home', is_folder=1),

		dict(file_name='a', folder='Home/cross_rename', is_folder=1),
		dict(file_name='b', folder='Home/cross_rename/a', is_folder=1),
		dict(file_name='c', folder='Home/cross_rename/a/b', content='x'),
		# dict(file_name='created', folder='Home/cross_rename/a/b', content='d'),

		dict(file_name='x', folder='Home/cross_rename', is_folder=1),
		dict(file_name='y', folder='Home/cross_rename/x', is_folder=1),
		dict(file_name='z', folder='Home/cross_rename/x/y', content='y'),
		dict(file_name='deleted', folder='Home/cross_rename/x/y', content='z'),
	])
	def test_1(self):
		# Setup initial state
		self.join('/cross_rename/a')
		self.join('/cross_rename/a/b')
		self.join('/cross_rename/a/b/c')
		# join('/cross_rename/a/b/created')

		self.join('/cross_rename/x')
		self.join('/cross_rename/x/y')
		self.join('/cross_rename/x/y/z')
		self.join('/cross_rename/x/y/deleted')

		# Update state
		self.remote_delete('/cross_rename/x/y/deleted')
		self.remote_mk_file('/cross_rename/a/b/created', b'z')

		self.remote_mv('/cross_rename/a/', '/cross_rename/tmp/')
		self.remote_mv('/cross_rename/x/', '/cross_rename/a/')
		self.remote_mv('/cross_rename/tmp/', '/cross_rename/x/')

		actions = self.differ.diff_from_remote([
			self.differ.get_remote_entry_by_path('/cross_rename'),
		])

		# def it_log(it):
		# 	for action in it:
		# 		print(action)
		# 		yield action

		self.runner.run_actions(actions)

		for f in self._local_files:
			if f.nextcloud_id and f.is_folder:
				# reload the doc
				f = frappe.get_doc('File', {'nextcloud_id': f.nextcloud_id})
				if f.is_folder:
					self.assertEqual(
						f.name, f'{f.folder}/{f.file_name}'.strip('/'))
				# print(f)
				# self.assertEqual(f.name, f'{f.folder}/{f.file_name}'.strip('/'))
