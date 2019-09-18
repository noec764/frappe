# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
from __future__ import unicode_literals
from bs4 import BeautifulSoup
from frappe.utils import cint

def get_jenv():
	import frappe

	if not getattr(frappe.local, 'jenv', None):
		from jinja2 import DebugUndefined
		from jinja2.sandbox import SandboxedEnvironment

		# frappe will be loaded last, so app templates will get precedence
		jenv = SandboxedEnvironment(loader = get_jloader(),
			undefined=DebugUndefined)
		set_filters(jenv)

		jenv.globals.update(get_allowed_functions_for_jenv())

		frappe.local.jenv = jenv

	return frappe.local.jenv

def get_template(path):
	return get_jenv().get_template(path)

def get_email_from_template(name, args):
	from jinja2 import TemplateNotFound

	args = args or {}
	try:
		message = get_template('templates/emails/' + name + '.html').render(args)
	except TemplateNotFound as e:
		raise e

	try:
		text_content = get_template('templates/emails/' + name + '.txt').render(args)
	except TemplateNotFound:
		text_content = None

	return (message, text_content)

def validate_template(html):
	"""Throws exception if there is a syntax error in the Jinja Template"""
	import frappe
	from jinja2 import TemplateSyntaxError

	jenv = get_jenv()
	try:
		jenv.from_string(html)
	except TemplateSyntaxError as e:
		frappe.msgprint('Line {}: {}'.format(e.lineno, e.message))
		frappe.throw(frappe._("Syntax error in template"))

def render_template(template, context, is_path=None, safe_render=True):
	'''Render a template using Jinja

	:param template: path or HTML containing the jinja template
	:param context: dict of properties to pass to the template
	:param is_path: (optional) assert that the `template` parameter is a path
	:param safe_render: (optional) prevent server side scripting via jinja templating
	'''

	from frappe import get_traceback, throw
	from jinja2 import TemplateError

	if not template:
		return ""

	# if it ends with .html then its a freaking path, not html
	if (is_path
		or template.startswith("templates/")
		or (template.endswith('.html') and '\n' not in template)):
		return get_jenv().get_template(template).render(context)
	else:
		if safe_render and ".__" in template:
			throw("Illegal template")
		try:
			template = transform_template_blot(template, context)

			return get_jenv().from_string(template).render(context)
		except TemplateError:
			throw(title="Jinja Template Error", msg="<pre>{template}</pre><pre>{tb}</pre>".format(template=template, tb=get_traceback()))


def get_allowed_functions_for_jenv():
	import os, json
	import frappe
	import frappe.utils
	import frappe.utils.data
	from frappe.model.document import get_controller
	from frappe.website.utils import (get_shade, get_toc, get_next_link)
	from frappe.modules import scrub
	import mimetypes
	from html2text import html2text
	from frappe.www.printview import get_visible_columns

	datautils = {}
	if frappe.db:
		date_format = frappe.db.get_default("date_format") or "yyyy-mm-dd"
	else:
		date_format = 'yyyy-mm-dd'

	for key, obj in frappe.utils.data.__dict__.items():
		if key.startswith("_"):
			# ignore
			continue

		if hasattr(obj, "__call__"):
			# only allow functions
			datautils[key] = obj

	if "_" in getattr(frappe.local, 'form_dict', {}):
		del frappe.local.form_dict["_"]

	user = getattr(frappe.local, "session", None) and frappe.local.session.user or "Guest"

	out = {
		# make available limited methods of frappe
		"frappe": {
			"_": frappe._,
			"get_url": frappe.utils.get_url,
			'format': frappe.format_value,
			"format_value": frappe.format_value,
			'date_format': date_format,
			"format_date": frappe.utils.data.global_date_format,
			"form_dict": getattr(frappe.local, 'form_dict', {}),
			"get_hooks": frappe.get_hooks,
			"get_meta": frappe.get_meta,
			"get_doc": frappe.get_doc,
			"get_cached_doc": frappe.get_cached_doc,
			"get_list": frappe.get_list,
			"get_all": frappe.get_all,
			'get_system_settings': frappe.get_system_settings,
			"utils": datautils,
			"user": user,
			"get_fullname": frappe.utils.get_fullname,
			"get_gravatar": frappe.utils.get_gravatar_url,
			"full_name": frappe.local.session.data.full_name if getattr(frappe.local, "session", None) else "Guest",
			"render_template": frappe.render_template,
			"request": getattr(frappe.local, 'request', {}),
			'session': {
				'user': user,
				'csrf_token': frappe.local.session.data.csrf_token if getattr(frappe.local, "session", None) else ''
			},
			"socketio_port": frappe.conf.socketio_port,
		},
		'style': {
			'border_color': '#d1d8dd'
		},
		'get_toc': get_toc,
		'get_next_link': get_next_link,
		"_": frappe._,
		"get_shade": get_shade,
		"scrub": scrub,
		"guess_mimetype": mimetypes.guess_type,
		'html2text': html2text,
		'json': json,
		"dev_server": 1 if os.environ.get('DEV_SERVER', False) else 0
	}

	if not frappe.flags.in_setup_help:
		out['get_visible_columns'] = get_visible_columns
		out['frappe']['date_format'] = date_format
		out['frappe']["db"] = {
			"get_value": frappe.db.get_value,
			"get_single_value": frappe.db.get_single_value,
			"get_default": frappe.db.get_default,
			"escape": frappe.db.escape,
		}

	# load jenv methods from hooks.py
	for method_name, method_definition in get_jenv_customization("methods"):
		out[method_name] = frappe.get_attr(method_definition)

	return out

def get_jloader():
	import frappe
	if not getattr(frappe.local, 'jloader', None):
		from jinja2 import ChoiceLoader, PackageLoader, PrefixLoader

		if frappe.local.flags.in_setup_help:
			apps = ['frappe']
		else:
			apps = frappe.get_hooks('template_apps')
			if not apps:
				apps = frappe.local.flags.web_pages_apps or frappe.get_installed_apps(sort=True)
				apps.reverse()

		if not "frappe" in apps:
			apps.append('frappe')

		frappe.local.jloader = ChoiceLoader(
			# search for something like app/templates/...
			[PrefixLoader(dict(
				(app, PackageLoader(app, ".")) for app in apps
			))]

			# search for something like templates/...
			+ [PackageLoader(app, ".") for app in apps]
		)

	return frappe.local.jloader

def set_filters(jenv):
	import frappe
	from frappe.utils import global_date_format, cint, cstr, flt, markdown
	from frappe.website.utils import get_shade, abs_url

	jenv.filters["global_date_format"] = global_date_format
	jenv.filters["markdown"] = markdown
	jenv.filters["json"] = frappe.as_json
	jenv.filters["get_shade"] = get_shade
	jenv.filters["len"] = len
	jenv.filters["int"] = cint
	jenv.filters["str"] = cstr
	jenv.filters["flt"] = flt
	jenv.filters["abs_url"] = abs_url

	if frappe.flags.in_setup_help: return

	# load jenv_filters from hooks.py
	for filter_name, filter_function in get_jenv_customization("filters"):
		jenv.filters[filter_name] = frappe.get_attr(filter_function)

def get_jenv_customization(customizable_type):
	import frappe

	if getattr(frappe.local, "site", None):
		for app in frappe.get_installed_apps():
			for jenv_customizable, jenv_customizable_definition in frappe.get_hooks(app_name=app).get("jenv", {}).items():
				if customizable_type == jenv_customizable:
					for data in jenv_customizable_definition:
						split_data = data.split(":")
						yield split_data[0], split_data[1]

def transform_template_blot(template, context):
	import frappe
	soup = BeautifulSoup(template, "html.parser")
	soup.insert(0, '{%- from "templates/letters/standard_macros.html" import render_table -%}')
	soup.insert(0, "{% " + " set doc_values = frappe.get_doc('{0}', '{1}') ".format(context.get('doctype'), context.get('name')) + " %}")
	fields = soup.find_all('template-blot')

	if not fields:
		return template

	doctypes = []

	for f in fields:
		new_tag = soup.new_tag("span")

		if f['data-doctype'] == "Custom Functions" and f['data-function'] != "null":
			content = "{{" + "{0}|safe".format(f['data-function'].split('#', 1)[-1]) + "}}"
			if f['data-function'].startswith("Signature"):
				content = soup.new_tag("img", src=content, height=200, width=200)
				new_tag.append(content)
			else:
				new_tag.string = content
		
		else:
			if f['data-doctype'] != "Custom Functions" and {f['data-doctype']: f['data-reference']} not in doctypes \
				and f['data-reference'] != "name":
				doctypes.append({f['data-doctype']: f['data-reference']})

			new_tag.string = "{{ " + "{0}|safe".format(get_newtag_string(f, context)) + " }}"

		f.replace_with(new_tag)

	for doctype in doctypes:
		for key in doctype:
			get_doc = "{% " + " set {0} = frappe.get_doc('{1}', {2}) ".format(key.replace(" ", "").lower(), key, \
				'doc.{0}'.format(doctype[key]) if 'doc' in context else doctype[key]) + " %}"
			soup.insert(0, get_doc)

	for method in frappe.get_hooks('jinja_template_extensions'):
		soup = frappe.get_attr(method)(soup)

	return soup.prettify()

def get_newtag_string(field, context):
	docname = None

	if (field['data-reference'] == "name" and "doc" in context) or field['data-reference'] != "name":
		docname = field['data-doctype'].replace(" ", "").lower()

	if field['data-fieldtype'] == "Table":
		value = "render_table({0}.meta.get_field('{1}').as_dict(), {0})".format(docname or 'doc_values', field['data-value'])
	else:
		if docname:
			value = "{0}.{1} or ''".format(docname, field['data-value'])
		else:
			value = "{0} or ''".format(field['data-value'])

		if field['data-function'] != "null":
			value = "{0}({1})".format(field['data-function'], value)

	return value