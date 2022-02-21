from datetime import timedelta

import frappe  # type: ignore

from ..Action import Action

from ._tester import Tester, using_local_files, using_remote_files


class TestNCIdempotence(Tester):
	@using_remote_files([
		'/idempotence_create',
	])
	def test_idempotence_local_create(self):
		r = self.differ.get_remote_entry_by_path('/idempotence_create')
		a = Action('local.create', None, r)

		args = ('File', {'file_name': 'idempotence_create', 'folder': 'Home'})
		self.assertRaises(frappe.DoesNotExistError, frappe.get_doc, *args)

		for _ in range(3):
			self.runner.run_actions([a])
			self.assertEqual(len(frappe.get_list(*args)), 1)

		doc = frappe.get_doc(*args)
		self.assertEqual(doc.file_name, args[1]['file_name'])
		self.assertEqual(doc.folder, args[1]['folder'])
		self.assertEqual(str(doc.content_hash), str(r.etag))
		self.assertAlmostEqual(
			doc.modified, r.last_updated,
			delta=timedelta(seconds=1))  # allow 1 second difference
		self.assertEqual(str(doc.nextcloud_id), str(r.nextcloud_id))
		self.assertEqual(str(doc.nextcloud_parent_id), str(r.parent_id))

	@using_local_files([
		dict(file_name='idempotence_delete', folder='Home', content=b'x'),
	])
	def test_idempotence_for_delete(self):
		l = self.differ.get_local_entry_by_path('/idempotence_delete')
		a = Action('local.delete', l, None)

		args = ('File', {'file_name': 'idempotence_delete', 'folder': 'Home'})
		self.assertIsNotNone(frappe.get_doc(*args))

		for _ in range(3):
			self.runner.run_actions([a])
			self.assertRaises(frappe.DoesNotExistError, frappe.get_doc, *args)

	@using_remote_files([
		'/idempotence_RENAMED',
	])
	@using_local_files([
		dict(file_name='idempotence_rename', folder='Home', content=b'x'),
	])
	def test_idempotence_for_rename(self):
		r = self.differ.get_remote_entry_by_path('/idempotence_RENAMED')
		l = self.differ.get_local_entry_by_path('/idempotence_rename')
		a = Action('local.file.moveRename', l, r)

		args = ('File', {'file_name': 'idempotence_rename', 'folder': 'Home'})
		doc = frappe.get_doc(*args)
		self.assertIsNotNone(doc)

		docname = doc.name

		self.runner.run_actions([a])
		initial_json = frappe.get_doc('File', docname).as_json()

		for _ in range(3):
			self.runner.run_actions([a])
			j = frappe.get_doc('File', docname).as_json()
			self.assertEqual(initial_json, j)
