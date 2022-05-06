import frappe

from frappe.integrations.doctype.nextcloud_settings.nextcloud_filesync.diff_engine.tests._tester import NextcloudTester, using_local_files, using_remote_files
from frappe.integrations.doctype.nextcloud_settings.nextcloud_filesync.sync import NextcloudFileSync
from frappe.integrations.doctype.nextcloud_settings.nextcloud_filesync.diff_engine.Action import Action

class TestSyncer(NextcloudTester):
	@using_remote_files([
		'/test_missing_remote_parent/',
		'/test_missing_remote_parent/A/',
		'/test_missing_remote_parent/A/file',
		'/test_missing_remote_parent/A/dir/',
	])
	@using_local_files([
		dict(file_name='test_missing_remote_parent', folder='Home', is_folder=1),
		dict(file_name='A', folder='Home/test_missing_remote_parent', is_folder=1),
		dict(file_name='dir', folder='Home/test_missing_remote_parent/A', is_folder=1),
		dict(file_name='file', folder='Home/test_missing_remote_parent/A', content='z'),
	])
	def test_missing_remote_parent(self):
		def compare_hierarchies():
			r, l = self.get_remote_and_local_files_as_lists('/test_missing_remote_parent/')
			r, l = map(lambda s: s.replace('/test_missing_remote_parent/', '/'), (r, l))
			self.assertMultiLineEqual(r, l)

		for path in self._remote_files:
			self.join(path)

		compare_hierarchies()

		self.syncer = NextcloudFileSync(self.settings)
		self.syncer.common = self.common
		self.syncer.differ = self.differ
		self.syncer.fetcher = self.fetcher
		self.syncer.runner = self.runner

		# self.remote_delete('/test_missing_remote_parent/A/')
		self.remote_delete('/test_missing_remote_parent/')

		children = frappe.get_all('File', {
			'folder': 'Home/test_missing_remote_parent/A'
		})

		for f in children:
			doc = frappe.get_doc('File', f)
			print(f'cofudir({doc}, False)')
			self.syncer._create_or_force_update_doc_in_remote(doc, False)

		for doc in self._local_files:
			l = self.common.convert_local_doc_to_entry(doc)
			r = self.common.get_remote_entry_by_path(l.path)
			if l.etag != r.etag:
				self.runner.run_actions([
					Action('meta.updateEtag', l, r)
				])

		compare_hierarchies()
