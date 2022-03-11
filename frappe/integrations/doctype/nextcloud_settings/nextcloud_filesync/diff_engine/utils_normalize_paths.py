import unicodedata


def _remove_prefix(s: str, prefix: str) -> str:
	if s.startswith(prefix):
		return s[len(prefix):]
	return s


def util_denormalize_to_local_path(path: str):
	p = path.strip('/')
	if not p:  # empty
		return (None, 'Home')  # The root dir is 'Home'
	elif '/' not in p:
		return ('Home', p)  # Direct child of 'Home'
	else:
		# NOTE: components are stripped of leading and trailing slashes
		# folder and file_name are both NOT empty
		folder, file_name = p.rsplit('/', 1)
		folder = 'Home/' + folder
		return (folder, file_name)


def util_normalize_local_path(folder: str, file_name: str, is_dir: bool) -> str:
	if not folder and file_name == 'Home':
		return '/'

	folder = unicodedata.normalize('NFC', folder or '')
	file_name = unicodedata.normalize('NFC', file_name or '')
	# print('\x1b[33;7m', folder, file_name, '\x1b[m')

	p = folder + '/' + file_name
	p = '/' + _remove_prefix(p, 'Home/')
	terminator = '/' if is_dir else ''
	return '/' + p.strip('/') + terminator


def util_denormalize_to_remote_path(path: str, root: str):
	return '/' + (root.rstrip('/') + '/' + path.lstrip('/')).strip('/')


def util_normalize_remote_path(path: str, is_dir: bool, root: str) -> str:
	p = path
	p = unicodedata.normalize('NFC', p or '')

	p = p.strip('/')
	# self.log('\x1b[33;7m', p, '\x1b[m')
	p = _remove_prefix('/' + p, root).strip('/')
	# p = _remove_prefix('/' + p, '/Administrator').strip('/')

	# p = '/' + os.path.relpath(p, root).strip('/')
	# p = '/' + _remove_prefix(p, '/Administrator/')

	if p == '':
		return '/'

	terminator = '/' if is_dir else ''
	return '/' + p.strip('/') + terminator
