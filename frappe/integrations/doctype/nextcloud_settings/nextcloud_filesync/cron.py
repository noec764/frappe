import re

import frappe
from frappe import _

from frappe.integrations.doctype.nextcloud_settings import get_nextcloud_settings
from frappe.integrations.doctype.nextcloud_settings.exceptions import NextcloudException
from frappe.integrations.doctype.nextcloud_settings.nextcloud_filesync.diff_engine.Action import Action
from frappe.integrations.doctype.nextcloud_settings.nextcloud_filesync.sync import NextcloudFileSync, sync_log


ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
def strip_ansi(s):
	return ansi_escape.sub('', s)


def get_sync_module():
	settings = get_nextcloud_settings()
	return NextcloudFileSync(settings=settings)


class NextcloudFilesyncCronRunner():
	def __init__(self, sync_module: NextcloudFileSync):
		self.syncer = sync_module

	def log(self, *args):
		self.syncer.log(*args)

	def _on_sync_error(self, e: Exception):
		frappe.db.rollback()
		import traceback
		details = ''.join(traceback.format_exception(None, e, e.__traceback__))
		self._error_log(repr(e), details)
		raise e

	def _post_sync(self):
		if len(self.syncer.conflicts):
			def fmt_conflict(conflict: Action) -> str:
				s = ''

				if conflict.local:
					s += (conflict.local._frappe_name or conflict.local.path) + ' '
				elif conflict.remote:
					s += (conflict.remote._file_info and conflict.remote._file_info.path or conflict.remote.path) + ' '

				s += '(' + repr(conflict) + ')'
				return s

			title = _('File conflicts exist between Dokos and Nextcloud, it is not possible to synchronize those files.')

			conflicts = map(fmt_conflict, self.syncer.conflicts)

			details = _('The following files have conflicts:', context='Nextcloud Integration') \
				+ '\n * ' + '\n * '.join(conflicts)
			details = strip_ansi(details)

			frappe.db.rollback()
			self._error_log(title, details)
			self.syncer.client.logout()
			return

		self.syncer.client.logout()
		frappe.db.commit()

	def _error_log(self, title: str, details: str = ""):
		self.log('/!\\ ' + title)
		self.log(details)
		self.log()
		msg = "{}: {}".format(_('Nextcloud'), title)
		frappe.log_error(details, msg)

	# def _delete_remote_root(self):
	# 	p = self.syncer.common.root
	# 	self.log('deleting root:', p, self.syncer.common.cloud_client.delete(p))
	# 	self.syncer._unjoin_all_files()

	def run(self):
		self.log('--- CRON RUN ---')
		if self.syncer.settings.get('debug_disable_filesync_cron', False):
			self.log('CRON IS NOT ENABLED')
			self.log('--- CRON END ---')
			return

		try:
			self._run()
			self._post_sync()
		except Exception as e:
			self._on_sync_error(e)
		finally:
			self.log('--- CRON END ---')

	def _run(self):
		s = self.syncer.get_before_sync_status()
		self.log('STATUS:', s)

		if s.status == 'error':
			if s.message == 'home-different-ids':
				self._error_log(repr(s))
			else:
				raise NextcloudException(s.message)

		if s.sync_type == 'none':
			return
		elif s.sync_type == 'normal':
			self.syncer.complete_sync(conflict_strategy='stop', commit=False)
		elif s.sync_type == 'all':
			self.syncer.complete_sync(conflict_strategy='stop', down_sync_all=True, commit=False)
		elif s.sync_type == 'initial':
			self.syncer.complete_sync(conflict_strategy='stop', down_sync_all=True, force_upload=True, commit=False)
		elif s.sync_type == 'overwrite':
			self.syncer.preserve_remote_root_bak()
			self.syncer.complete_sync(conflict_strategy='stop', down_sync_all=True, force_upload=True, commit=False)
		else:
			raise ValueError('unknown sync type in' + s)


def run_cron():
	t = frappe.utils.now_datetime()
	NextcloudFilesyncCronRunner(get_sync_module()).run()
	sync_log('CRON DURATION:', (frappe.utils.now_datetime() - t).total_seconds())
