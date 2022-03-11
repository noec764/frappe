import os
from typing import List, Optional, Union
from typing_extensions import Literal
from datetime import datetime
import xml.etree.ElementTree as ET

import frappe

from owncloud.owncloud import Client, FileInfo, HTTPResponseError
from six.moves.urllib.parse import quote


class NextcloudIntegrationClient(Client):
	def __init__(self, url, **kwargs):
		super().__init__(url, dav_endpoint_version=999, **kwargs)

	def _make_dav_root_request(self, method, path, **kwargs):
		"""Makes a WebDAV request from the DAV root

		:param method: HTTP method
		:param path: remote path of the targeted file
		:param \*\*kwargs: optional arguments that ``requests.Request.request`` accepts
		:returns array of :class:`FileInfo` if the response
		contains it, or True if the operation succeded, False
		if it didn't
		"""

		# url = self._webdav_url + '/' + path.lstrip('/')
		url = self.url + 'remote.php/dav/' + path

		if self._debug:
			print('DAV request: %s %s' % (method, url))
			if kwargs.get('headers'):
				print('Headers: ', kwargs.get('headers'))
			if kwargs.get('data'):
				print('Data:')
				print(kwargs.get('data'))

		res = self._session.request(method, url, **kwargs)

		if self._debug:
			print('DAV status: %i' % res.status_code)
		if res.status_code in [200, 207]:
			return self._parse_dav_response(res)
		if res.status_code in [204, 201]:
			return True
		raise HTTPResponseError(res)

	def search(self, path, depth=1, data=None) -> List[FileInfo]:
		# https://github.com/nextcloud/3rdparty/blob/master/icewind/searchdav/src/DAV/SearchPlugin.php

		if path != '' and not path.endswith('/'):
			path += '/'

		headers = {'Content-Type': 'application/xml'}
		if isinstance(depth, int) or depth == "infinity":
			headers['Depth'] = str(depth)

		return self._make_dav_root_request('SEARCH', path, headers=headers, data=data)

	@property
	def _QUERY_PROPS(self):
		return [
			'{http://owncloud.org/ns}fileid',
			'{DAV:}getetag',
			# '{DAV:}getcontentlength',
			# '{DAV:}getcontenttype',
			'{DAV:}getlastmodified',
		]

	def list_updated_since(
			self,
			dt: datetime,
			path: Optional[str] = None,
			depth: Union[int, Literal['infinity']] = 'infinity',
			props: List[str] = None,
	) -> List[FileInfo]:
		dt_string = dt.strftime('%FT%TZ')  # yyyy-mm-ddThh:mm:ssZ

		if props == None:
			props = self._QUERY_PROPS

		search_where = f'''
			<d:gt>
				<d:prop>
					<d:getlastmodified />
				</d:prop>
				<d:literal>{dt_string}</d:literal>
			</d:gt>
		'''

		search_orderby = '''
			<d:prop>
				<d:href />
			</d:prop>
			<d:ascending />
		'''

		return self.basic_search_select_from_where(
			props=props,
			path=path,
			where=search_where,
			orderby=search_orderby,
			depth=depth,
		)

	def basic_search_select_from_where(
			self,
			props: List[str],
			where: str = '',
			orderby: str = '',
			path: str = '',
			depth: Union[int, Literal['infinity']] = 'infinity',
	) -> List[FileInfo]:
		user_id = self._session.auth[0]
		scope = '/files/' + quote(user_id)
		if path:
			scope += '/' + path

		propsxml = ET.Element('d:prop', {
			'xmlns:d': "DAV:",
			'xmlns:nc': "http://nextcloud.org/ns",
			'xmlns:oc': "http://owncloud.org/ns"
		})
		for p in props:
			ET.SubElement(propsxml, p)

		propsxml = ET.tostring(propsxml)
		if isinstance(propsxml, bytes):
			propsxml = propsxml.decode('utf8')

		data = f'''
<d:searchrequest xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">
	<d:basicsearch>
		<d:select>{propsxml}</d:select>
		<d:from>
			<d:scope>
				<d:href>{scope}</d:href>
				<d:depth>{depth}</d:depth>
			</d:scope>
		</d:from>
		<d:where>{where}</d:where>
		<d:orderby>{orderby}</d:orderby>
	</d:basicsearch>
</d:searchrequest>
'''
		return self.search(path='', depth=depth, data=data)

	def mkdir_p(self, _path: Union[str, List[str]]):
		"""Creates a remote directory and any parent directories as needed

		:param path: path to the remote directory to create
		:returns: True if the operation succeeded
		:raises: HTTPResponseError in case an HTTP error status was returned
		"""

		path: List[str] = []

		if isinstance(_path, str):
			path = os.path.normpath(_path).strip('/').split('/')
		elif isinstance(_path, list):
			def clean(p): return str(p).replace('/', '-')
			path = list(map(clean, filter(None, _path)))
		else:
			raise ValueError('expected argument of type str or list[str]')

		# print(_path, '->', path)

		current_path = ''
		for dir in path:
			current_path += dir + '/'

			try:
				self._make_dav_request('MKCOL', current_path)
			except HTTPResponseError as e:
				ok = (e.status_code == 409) or (e.status_code == 405)
				if not ok:
					raise e

		return True

	def file_info_by_fileid(self, fileid, properties=None):
		"""Returns the file info for the given remote file (by fileid)

		:param fileid: fileid of the remote file
		:param properties: a list of properties to request (optional)
		:returns: file info
		:rtype: :class:`FileInfo` object or `None` if file
			was not found
		:raises: HTTPResponseError in case an HTTP error status was returned
		"""
		if not properties:
			properties = self._QUERY_PROPS

		res = self.basic_search_select_from_where(
			properties,
			where=f'''
				<d:eq>
					<d:prop>
						<oc:fileid/>
					</d:prop>
					<d:literal>{fileid}</d:literal>
				</d:eq>
			''',
			orderby='',
			depth='infinity'
		)

		if res and len(res) > 0:
			return res[0]
		return None
