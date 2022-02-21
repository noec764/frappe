import frappe  # type: ignore

from ..Action import Action
from ..Entry import EntryLocal

from ._tester import Tester, using_local_files, using_remote_files


class TestNCActions(Tester):
	@using_remote_files([
		'/create',
	])
	def test_create(self):
		r = self.differ.get_remote_entry_by_path('/create')
		a = Action('local.create', None, r)

		args = ('File', {'file_name': 'create', 'folder': 'Home'})
		self.assertRaises(frappe.DoesNotExistError, frappe.get_doc, *args)

		self.runner.run_actions([a])

		list1 = frappe.get_list(*args)
		self.assertEqual(len(list1), 1)

		doc = frappe.get_doc(*args)
		self.assertEqual(doc.file_name, args[1]['file_name'])
		self.assertEqual(doc.folder, args[1]['folder'])
		self.assertEqual(str(doc.content_hash), str(r.etag))
		self.assertEqual(str(doc.modified), str(r.last_updated))
		self.assertEqual(str(doc.nextcloud_id), str(r.nextcloud_id))
		self.assertEqual(str(doc.nextcloud_parent_id), str(r.parent_id))

	@using_remote_files([
		'/join.remote',
	])
	@using_local_files([
		dict(file_name='join.f', folder='Home', content='x'),
	])
	def test_join(self):
		r = self.differ.get_remote_entry_by_path('/join.remote')
		l = self.differ.get_local_entry_by_path('/join.f')
		a = Action('local.join', l, r)

		self.runner.run_actions([a])

		doc = frappe.get_doc('File', l._frappe_name)
		self.assertEqual(doc.file_name, 'join.remote')
		self.assertEqual(doc.folder, 'Home')
		self.assertEqual(str(doc.content_hash), str(r.etag))
		self.assertEqual(str(doc.modified), str(r.last_updated))
		self.assertEqual(str(doc.nextcloud_id), str(r.nextcloud_id))
		self.assertEqual(str(doc.nextcloud_parent_id), str(r.parent_id))

	@using_remote_files([
		'/mv_file/',
		'/mv_file/new_name',
	])
	@using_local_files([
		dict(file_name='mv_file', folder='Home', is_folder=1),
		dict(file_name='old_name', folder='Home/mv_file', content='x'),
	])
	def test_file_mv(self):
		d = self.differ.get_local_entry_by_path('/mv_file')
		l = self.differ.get_local_entry_by_path('/mv_file/old_name')
		r = self.differ.get_remote_entry_by_path('/mv_file/new_name')
		a = Action('local.file.moveRename', l, r)

		self.assertIsNotNone(d)
		self.assertIsNotNone(l)
		self.assertIsNotNone(r)
		self.assertIsNotNone(a)

		self.runner.run_actions([a])

		doc = frappe.get_doc('File', l._frappe_name)
		self.assertEqual(doc.file_name, 'new_name')
		self.assertEqual(doc.folder, 'Home/mv_file')
		self.assertEqual(str(doc.modified), str(r.last_updated))
		# self.assertEqual(str(doc.content_hash), str(r.etag))
		# self.assertEqual(str(doc.nextcloud_id), str(r.nextcloud_id))
		# self.assertEqual(str(doc.nextcloud_parent_id), str(r.parent_id))

	@using_remote_files([
		'/mv_dir.RENAMED/',
		'/mv_dir.RENAMED/child',
		'/mv_dir.RENAMED/child_dir/',
		'/mv_dir.RENAMED/child_dir/deep_file',
		'/mv_dirzz/',
		'/mv_dirzz/UNTOUCHED',
	])
	@using_local_files([
		dict(file_name='mv_dir', folder='Home', is_folder=1),
		dict(file_name='child', folder='Home/mv_dir', content='x'),
		dict(file_name='child_dir', folder='Home/mv_dir', is_folder=1),
		dict(file_name='deep_file', folder='Home/mv_dir/child_dir', content='y'),
		dict(file_name='mv_dirzz', folder='Home', is_folder=1),
		dict(file_name='UNTOUCHED', folder='Home/mv_dirzz', content='z'),
	])
	def test_dir_mv(self):
		l = self.differ.get_local_entry_by_path('/mv_dir')
		r = self.differ.get_remote_entry_by_path('/mv_dir.RENAMED')
		a = Action('local.dir.moveRenamePlusChildren', l, r)

		self.assertIsNotNone(l)
		self.assertIsNotNone(r)
		self.assertIsNotNone(a)

		self.assertIsNotNone(self.differ.get_local_entry_by_path(
			'/mv_dir/child'))
		self.assertIsNone(self.differ.get_local_entry_by_path(
			'/mv_dir.RENAMED/child'))

		self.runner.run_actions([a])

		self.assertRaises(frappe.DoesNotExistError,
						  frappe.get_doc, 'File', l._frappe_name)

		doc = frappe.get_doc('File', 'Home/mv_dir.RENAMED')
		self.assertIsNotNone(doc)
		self.assertEqual(doc.file_name, 'mv_dir.RENAMED')
		self.assertEqual(doc.folder, 'Home')
		self.assertEqual(str(doc.modified), str(r.last_updated))

		local_child = self.differ.get_local_entry_by_path(
			'/mv_dir.RENAMED/child')
		self.assertIsNotNone(local_child)

		child = frappe.get_doc('File', local_child._frappe_name)

		self.assertEqual(child.file_name, 'child')
		self.assertEqual(child.folder, 'Home/mv_dir.RENAMED')

		should_exist = self._remote_files
		for path in should_exist:
			ce = self.differ.get_local_entry_by_path(path)
			if ce is None:
				print("SHOULD EXIST", path, ce)
			self.assertIsNotNone(ce)
			c = frappe.get_doc('File', ce._frappe_name)
			s = path.strip('/').rsplit('/', 1)
			if len(s) == 2:
				s = 'Home/' + s[0], s[1]
			elif len(s) == 1:
				s = 'Home', s[0]
			else:
				s = None, path.strip('/')

			self.assertEqual(c.folder, s[0])
			self.assertEqual(c.file_name, s[1])

			self.local_dir_was_renamed('Home/mv_dir', 'Home/mv_dir.RENAMED')

	@using_remote_files([
		'/cross_rename/',

		# a -> x
		'/cross_rename/a/',
		'/cross_rename/a/b/',
		'/cross_rename/a/b/c',

		# x -> a
		'/cross_rename/x/',
		'/cross_rename/x/y/',
		'/cross_rename/x/y/z',
	])
	@using_local_files([
		dict(file_name='cross_rename', folder='Home', is_folder=1),

		dict(file_name='a', folder='Home/cross_rename', is_folder=1),
		dict(file_name='b', folder='Home/cross_rename/a', is_folder=1),
		dict(file_name='c', folder='Home/cross_rename/a/b', content='x'),

		dict(file_name='x', folder='Home/cross_rename', is_folder=1),
		dict(file_name='y', folder='Home/cross_rename/x', is_folder=1),
		dict(file_name='z', folder='Home/cross_rename/x/y', content='y'),
	])
	def test_dir_cross_rename(self):
		# def show_state(msg=''):
		#     if msg:
		#         print()
		#         print(msg)
		#     all_files = frappe.get_list('File', filters={
		#         'folder': ('like', 'Home/cross_rename%'),
		#     }, fields=['name', 'file_name', 'folder', 'nextcloud_id'])
		#     all_files.sort(key=lambda x: x['nextcloud_id'] or -1)
		#     for f in all_files:
		#         print(f['nextcloud_id'], ' | ', f['name'], ': ',
		#               f['folder'], '/', f['file_name'], sep='')

		def join(path: str):
			l = self.differ.get_local_entry_by_path(path)
			r = self.differ.get_remote_entry_by_path(path)
			# print(path, l, r)
			assert l  # for mypy
			assert r  # for mypy
			frappe.db.set_value('File', l._frappe_name, {
				'content_hash': r.etag,
				'nextcloud_id': r.nextcloud_id,
				'nextcloud_parent_id': r.parent_id,
			}, modified=r.last_updated)

		local_1_old = self.differ.get_local_entry_by_path('/cross_rename/a')
		local_2_old = self.differ.get_local_entry_by_path('/cross_rename/x')

		remote_1_old = self.differ.get_remote_entry_by_path('/cross_rename/a')
		remote_2_old = self.differ.get_remote_entry_by_path('/cross_rename/x')

		self.assertIsNotNone(local_1_old)
		self.assertIsNotNone(local_2_old)

		self.assertIsNotNone(remote_1_old)
		self.assertIsNotNone(remote_2_old)

		# Join files
		join('/cross_rename/a')
		join('/cross_rename/a/b')
		join('/cross_rename/a/b/c')

		join('/cross_rename/x')
		join('/cross_rename/x/y')
		join('/cross_rename/x/y/z')

		local_1_old = self.differ.get_local_entry_by_path('/cross_rename/a')
		local_2_old = self.differ.get_local_entry_by_path('/cross_rename/x')

		self.assertIsNotNone(local_1_old)
		self.assertIsNotNone(local_2_old)

		def mv(a: str, b: str):
			root = '/' + self.common.root.strip('/') + '/'
			a = root + a.lstrip('/')
			b = root + b.lstrip('/')

			res = self.common.cloud_client.move(a, b)

			for i, s in enumerate(self._remote_files):
				x = self._remote_files[i]
				if x.startswith(a):
					self._remote_files[i] = x.replace(a, b, 1)
			self.assertTrue(res)

		mv('/cross_rename/a/', '/cross_rename/tmp/')
		mv('/cross_rename/x/', '/cross_rename/a/')
		mv('/cross_rename/tmp/', '/cross_rename/x/')

		remote_1_new = self.differ.get_remote_entry_by_path('/cross_rename/x')
		remote_2_new = self.differ.get_remote_entry_by_path('/cross_rename/a')

		self.assertIsNotNone(remote_1_new)
		self.assertIsNotNone(remote_2_new)

		actions = self.differ.diff_from_remote([
			remote_1_new,
			remote_2_new,
		])

		# show_state('- - Initial state - -')

		action1 = next(actions)
		self.assertEqual(action1.type, 'local.dir.moveRenamePlusChildren')
		self.runner._run_action(action1)

		# show_state('- - Intermediate incoherent state - -')

		action2 = next(actions)
		self.assertEqual(action2.type, 'local.dir.moveRenamePlusChildren')
		self.runner._run_action(action2)

		self.assertEqual(len(list(actions)), 0)

		# show_state('- - Intermediate state before renames - -')

		self.runner._run_deferred_tasks()

		# show_state('- - Final state - -')

		self.assertEqual(
			self.differ.get_local_entry_by_path('/cross_rename/x'),
			self.differ.get_local_entry_by_id(remote_1_new.nextcloud_id),
		)

		self.assertEqual(
			self.differ.get_local_entry_by_path('/cross_rename/a'),
			self.differ.get_local_entry_by_id(remote_2_new.nextcloud_id),
		)

		local_1_new_expected = EntryLocal(
			path='/cross_rename/x/',
			etag=remote_1_new.etag,
			last_updated=remote_1_new.last_updated,
			nextcloud_id=remote_1_new.nextcloud_id,
			parent_id=remote_1_new.parent_id,
			_frappe_name=local_1_old._frappe_name,
		)
		local_1_new_real = self.differ.get_local_entry_by_path(
			'/cross_rename/x/')
		self.assertEqual(local_1_new_expected, local_1_new_real)

		local_2_new_expected = EntryLocal(
			path='/cross_rename/a/',
			etag=remote_2_new.etag,
			last_updated=remote_2_new.last_updated,
			nextcloud_id=remote_2_new.nextcloud_id,
			parent_id=remote_2_new.parent_id,
			_frappe_name=local_2_old._frappe_name,
		)
		local_2_new_real = self.differ.get_local_entry_by_path(
			'/cross_rename/a/')
		self.assertEqual(local_2_new_expected, local_2_new_real)

		self.assertIsNotNone(frappe.get_doc('File', 'Home/cross_rename/a'))

		self.assertEqual(
			frappe.get_doc('File', 'Home/cross_rename/a').file_name,
			'a')

		self.assertIsNotNone(frappe.get_doc('File', 'Home/cross_rename/x'))

		self.assertEqual(
			frappe.get_doc('File', 'Home/cross_rename/x').file_name,
			'x')

		# check that all local folders have been renamed
		for f in self._local_files:
			if f.nextcloud_id and f.is_folder:
				# reload the doc
				f = frappe.get_doc('File', {'nextcloud_id': f.nextcloud_id})
				self.assertEqual(
					f.name, f'{f.folder}/{f.file_name}'.strip('/'))


# try:
# 	frappe.db.rollback()
# 	t = TestActions()
# 	t.setUp()
# 	t.test_create()
# 	t.test_join()
# 	t.test_file_mv()
# 	t.test_dir_mv()
# 	t.test_dir_cross_rename()
# except Exception as e:
# 	print(e)
# 	import traceback
# 	traceback.print_exc()

# 	import pdb
# 	pdb.post_mortem()
# 	raise
# finally:
# 	t.tearDown()
# 	frappe.db.rollback()
