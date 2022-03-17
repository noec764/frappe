import frappe  # type: ignore

from ._tester import NextcloudTester, using_local_files, using_remote_files


class TestNCDiffing(NextcloudTester):
	@using_remote_files([
		'/SR1/',
		'/SR1/a/',
		'/SR1/x/',
		'/SR1/x/file.moved',
		'/SR1/x/file.stay',
	])
	@using_local_files([
		dict(file_name='SR1', folder='Home', is_folder=1),
		dict(file_name='a', folder='Home/SR1', is_folder=1),
		dict(file_name='x', folder='Home/SR1', is_folder=1),
		dict(file_name='file.moved', folder='Home/SR1/x', content='z'),
		dict(file_name='file.stay', folder='Home/SR1/x', content='z'),
	])
	def test_simple_rename_and_move(self):
		# Setup initial state
		id0 = self.join('/SR1')
		id1 = self.join('/SR1/a')
		id2 = self.join('/SR1/x')
		id3 = self.join('/SR1/x/file.moved')
		id4 = self.join('/SR1/x/file.stay')

		self.remote_mv('/SR1/a/', '/SR1/a2/')
		self.remote_mv('/SR1/x/', '/SR1/x2/')

		self.remote_mv('/SR1/x2/file.moved', '/SR1/a2/file.moved')

		actions = self.differ.diff_from_remote([
			self.differ.get_remote_entry_by_path('/SR1'),
		])

		self.runner.run_actions(actions)

		for f in self._local_files:
			self.assertIsNotNone(f.nextcloud_id)
			f = frappe.get_doc('File', {'nextcloud_id': f.nextcloud_id})

			if f.is_folder:
				self.assertEqual(f.name, f'{f.folder}/{f.file_name}'.strip('/'))

			self.assertIn((f.folder, f.file_name, int(f.nextcloud_id)), (
				('Home', 'SR1', int(id0)),
				('Home/SR1', 'a2', int(id1)),
				('Home/SR1', 'x2', int(id2)),
				('Home/SR1/a2', 'file.moved', int(id3)),
				('Home/SR1/x2', 'file.stay', int(id4)),
			))

	@using_remote_files([
		'/simple_cross_rename/',
		'/simple_cross_rename/a/',
		'/simple_cross_rename/x/',
	])
	@using_local_files([
		dict(file_name='simple_cross_rename', folder='Home', is_folder=1),
		dict(file_name='a', folder='Home/simple_cross_rename', is_folder=1),
		dict(file_name='x', folder='Home/simple_cross_rename', is_folder=1),
	])
	def test_simple_cross_rename(self):
		id0 = self.join('/simple_cross_rename')
		id1 = self.join('/simple_cross_rename/a')
		id2 = self.join('/simple_cross_rename/x')

		self.remote_mv('/simple_cross_rename/a/', '/simple_cross_rename/tmp/')
		self.remote_mv('/simple_cross_rename/x/', '/simple_cross_rename/a/')
		self.remote_mv('/simple_cross_rename/tmp/', '/simple_cross_rename/x/')

		actions = self.differ.diff_from_remote([self.differ.get_remote_entry_by_path('/simple_cross_rename')])
		self.runner.run_actions(actions)

		for f in self._local_files:
			self.assertIsNotNone(f.nextcloud_id)
			f = frappe.get_doc('File', {'nextcloud_id': f.nextcloud_id})
			if f.is_folder:
				self.assertEqual(f.name, f'{f.folder}/{f.file_name}'.strip('/'))
			self.assertIn((f.folder, f.file_name, int(f.nextcloud_id)), (
				('Home', 'simple_cross_rename', int(id0)),
				('Home/simple_cross_rename', 'x', int(id1)),
				('Home/simple_cross_rename', 'a', int(id2)),
			))

	@using_remote_files([
		'/XR2/',
		'/XR2/a/',
		'/XR2/x/',
		'/XR2/x/file.moved',
		'/XR2/x/file.stay',
	])
	@using_local_files([
		dict(file_name='XR2', folder='Home', is_folder=1),
		dict(file_name='a', folder='Home/XR2', is_folder=1),
		dict(file_name='x', folder='Home/XR2', is_folder=1),
		dict(file_name='file.moved', folder='Home/XR2/x', content='z'),
		dict(file_name='file.stay', folder='Home/XR2/x', content='z'),
	])
	def test_cross_rename_and_move(self):
		# Setup initial state
		id0 = self.join('/XR2')
		id1 = self.join('/XR2/a')
		id2 = self.join('/XR2/x')
		id3 = self.join('/XR2/x/file.moved')
		id4 = self.join('/XR2/x/file.stay')

		# state: a/, x/, x/file.moved

		self.remote_mv('/XR2/a/', '/XR2/tmp/')  # state: tmp/, x/, x/file.moved, x/file.stay
		self.remote_mv('/XR2/x/', '/XR2/a/')    # state: tmp/, a/, a/file.moved, a/file.stay
		self.remote_mv('/XR2/tmp/', '/XR2/x/')  # state: x/,   a/, a/file.moved, a/file.stay

		self.remote_mv('/XR2/a/file.moved', '/XR2/x/file.moved')
		# state: a/, x/, x/file.moved, a/file.stay
		# file.moved was moved from the x->a folder to the a->x folder
		# file.stay stayed in the x->a folder

		actions = self.differ.diff_from_remote([
			self.differ.get_remote_entry_by_path('/XR2'),
		])

		self.runner.run_actions(actions)

		for f in self._local_files:
			self.assertIsNotNone(f.nextcloud_id)
			f = frappe.get_doc('File', {'nextcloud_id': f.nextcloud_id})

			if f.is_folder:
				self.assertEqual(f.name, f'{f.folder}/{f.file_name}'.strip('/'))

			self.assertIn((f.folder, f.file_name, int(f.nextcloud_id)), (
				('Home', 'XR2', int(id0)),
				('Home/XR2', 'x', int(id1)),
				('Home/XR2', 'a', int(id2)),
				('Home/XR2/x', 'file.moved', int(id3)),
				('Home/XR2/a', 'file.stay', int(id4)),
			))


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
	def test_cross_rename(self):
		# Setup initial state
		self.join('/cross_rename')

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

		self.runner.run_actions(actions)

		# import pdb; pdb.set_trace()

		for f in self._local_files:
			self.assertIsNotNone(f.nextcloud_id)

			if f.file_name == 'deleted':
				self.assertRaises(
					frappe.DoesNotExistError,
					frappe.get_doc, 'File', {'nextcloud_id': f.nextcloud_id})
				continue

			# reload the doc
			f = frappe.get_doc('File', {'nextcloud_id': f.nextcloud_id})
			f.reload()

			if f.is_folder:
				self.assertEqual(
					f.name, f'{f.folder}/{f.file_name}'.strip('/'))
			else:
				self.assertIn(f.folder, (
					'Home/cross_rename',
					'Home/cross_rename/x',
					'Home/cross_rename/x/b',
					'Home/cross_rename/a',
					'Home/cross_rename/a/y'))

	@using_remote_files([
		'/multi_renames/',
		'/multi_renames/a/',
		'/multi_renames/a/b/',
		'/multi_renames/a/b/c/',
		'/multi_renames/a/b/c/f',
	])
	@using_local_files([
		dict(file_name='multi_renames', folder='Home', is_folder=1),
		dict(file_name='a', folder='Home/multi_renames', is_folder=1),
		dict(file_name='b', folder='Home/multi_renames/a', is_folder=1),
		dict(file_name='c', folder='Home/multi_renames/a/b', is_folder=1),
		dict(file_name='f', folder='Home/multi_renames/a/b/c', content='x'),
	])
	def test_multi_renames(self):
		# Setup initial state
		for f in self._remote_files:
			self.join(f.rstrip('/'))

		# Update state
		self.remote_mv('/multi_renames/a/b/c/f', '/multi_renames/a/b/c/g')
		self.remote_mv('/multi_renames/a/b/c/', '/multi_renames/a/b/z/')
		self.remote_mv('/multi_renames/a/', '/multi_renames/x/')

		actions = self.differ.diff_from_remote([
			self.differ.get_remote_entry_by_path('/multi_renames'),
		])

		self.runner.run_actions(actions)

		for f in self._local_files:
			self.assertIsNotNone(f.nextcloud_id)

			# reload the doc
			f = frappe.get_doc('File', {'nextcloud_id': f.nextcloud_id})

			if f.is_folder:
				self.assertEqual(f.name, f'{f.folder}/{f.file_name}'.strip('/'))

			self.assertIn(
				(f.folder, f.file_name), (
				('Home', 'multi_renames'),
				('Home/multi_renames', 'x'),
				('Home/multi_renames/x', 'b'),
				('Home/multi_renames/x/b', 'z'),
				('Home/multi_renames/x/b/z', 'g'),
			))

	@using_remote_files([
		'/XR3/',
		'/XR3/a/',
		'/XR3/a/x',
		'/XR3/b/',
		'/XR3/b/y',
	])
	@using_local_files([
		dict(file_name='XR3', folder='Home', is_folder=1),
		dict(file_name='a', folder='Home/XR3', is_folder=1),
		dict(file_name='x', folder='Home/XR3/a', content="x"),
		dict(file_name='b', folder='Home/XR3', is_folder=1),
		dict(file_name='y', folder='Home/XR3/b', content="y"),
	])
	def stest_complex_cross_rename1(self):
		idRoot = self.join('/XR3')
		idA = self.join('/XR3/a')
		idB = self.join('/XR3/b')
		idAX = self.join('/XR3/a/x')
		idBY = self.join('/XR3/b/y')

		# cross-rename a->b, b->a
		self.remote_mv('/XR3/a/', '/XR3/tmp/')
		self.remote_mv('/XR3/b/', '/XR3/a/')
		self.remote_mv('/XR3/tmp/', '/XR3/b/')

		# added rename for confusion
		# change filename: b/x [initially a/x] -> b/y
		self.remote_mv('/XR3/b/x', '/XR3/b/y')

		# added rename for confusion
		# change filename: a/y [initially b/y] -> a/x
		self.remote_mv('/XR3/a/y', '/XR3/a/x')

		actions = self.differ.diff_from_remote([
			self.differ.get_remote_entry_by_path('/XR3')
		])
		self.runner.run_actions(actions)

		for f in self._local_files:
			self.assertIsNotNone(f.nextcloud_id)
			f = frappe.get_doc('File', {'nextcloud_id': f.nextcloud_id})
			if f.is_folder:
				self.assertEqual(f.name, f'{f.folder}/{f.file_name}'.strip('/'))

			if f.file_name == 'XR3':
				self.assertEqual(f.folder, 'Home')
				self.assertEqual(int(f.nextcloud_id), int(idRoot))
				continue

			tup = (f.folder, f.file_name, int(f.nextcloud_id), int(f.nextcloud_parent_id))
			self.assertIn(tup, (
				('Home/XR3', 'b', int(idA), int(idRoot)),
				('Home/XR3', 'a', int(idB), int(idRoot)),
				('Home/XR3/b', 'y', int(idAX), int(idA)),
				('Home/XR3/a', 'x', int(idBY), int(idB)),
			))

	@using_remote_files([
		'/XR3/',
		'/XR3/a/',
		'/XR3/a/x',
		'/XR3/b/',
		'/XR3/b/y',
	])
	@using_local_files([
		dict(file_name='XR3', folder='Home', is_folder=1),
		dict(file_name='a', folder='Home/XR3', is_folder=1),
		dict(file_name='x', folder='Home/XR3/a', content="x"),
		dict(file_name='b', folder='Home/XR3', is_folder=1),
		dict(file_name='y', folder='Home/XR3/b', content="y"),
	])
	def test_complex_cross_rename2(self):
		idRoot = self.join('/XR3')
		idA = self.join('/XR3/a')
		idB = self.join('/XR3/b')
		idAX = self.join('/XR3/a/x')
		idBY = self.join('/XR3/b/y')

		# print('IDS:')
		# print('-', 'root', idRoot)
		# print('-', 'a/', idA)
		# print('-', 'b/', idB)
		# print('-', 'a/x', idAX)
		# print('-', 'b/y', idBY)

		# cross-rename a->b, b->a
		self.remote_mv('/XR3/a/', '/XR3/tmp/')
		self.remote_mv('/XR3/b/', '/XR3/a/')
		self.remote_mv('/XR3/tmp/', '/XR3/b/')

		# added move for confusion
		# move the file "back": b/x [initially a/x] -> a/x
		self.remote_mv('/XR3/b/x', '/XR3/a/x')

		# added move for confusion
		# move the file "back": a/y [initially b/y] -> b/y
		self.remote_mv('/XR3/a/y', '/XR3/b/y')

		actions = self.differ.diff_from_remote([
			self.differ.get_remote_entry_by_path('/XR3')
		])
		self.runner.run_actions(actions)

		for f in self._local_files:
			self.assertIsNotNone(f.nextcloud_id)
			f = frappe.get_doc('File', {'nextcloud_id': f.nextcloud_id})
			if f.is_folder:
				self.assertEqual(f.name, f'{f.folder}/{f.file_name}'.strip('/'))

			if f.file_name == 'XR3':
				self.assertEqual(f.folder, 'Home')
				self.assertEqual(int(f.nextcloud_id), int(idRoot))
				continue

			tup = (f.folder, f.file_name, int(f.nextcloud_id), int(f.nextcloud_parent_id))

			self.assertIn(tup, (
				('Home/XR3', 'b', int(idA), int(idRoot)),
				('Home/XR3', 'a', int(idB), int(idRoot)),
				('Home/XR3/a', 'x', int(idAX), int(idB)),
				('Home/XR3/b', 'y', int(idBY), int(idA)),
			))
