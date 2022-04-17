from frappe import _

class NextcloudException(Exception):
	pass

class NextcloudSyncMissingRoot(NextcloudException):
	def __init__(self, *args):
		super().__init__('no root directory', *args)

class NextcloudSyncCannotCreateRoot(NextcloudException):
	def __init__(self, *args):
		super().__init__('failed to create root directory', *args)

class NextcloudSyncCannotFetchRoot(NextcloudException):
	def __init__(self, *args):
		super().__init__('failed to fetch root directory', *args)

class NextcloudExceptionServerIsDown(NextcloudException):
	def __init__(self, *args):
		super().__init__(_('Nextcloud server is down', context='Nextcloud'), *args)

class NextcloudExceptionInvalidCredentials(NextcloudException):
	def __init__(self, *args):
		super().__init__(_('Invalid Credentials', context='Nextcloud'), *args)

class NextcloudExceptionInvalidUrl(NextcloudException):
	def __init__(self, *args):
		super().__init__(_('Invalid URL', context='Nextcloud'), *args)
