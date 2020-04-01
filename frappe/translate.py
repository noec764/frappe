# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals, print_function

from six import iteritems, text_type, string_types, PY2

"""
	frappe.translate
	~~~~~~~~~~~~~~~~

	Translation tools for frappe
"""

import frappe, os, re, io, codecs, json
from frappe.model.utils import render_include, InvalidIncludePath
from frappe.utils import strip, strip_html_tags, is_html
from jinja2 import TemplateError
import itertools, operator
from collections import defaultdict
from functools import reduce

def guess_language(lang_list=None):
	"""Set `frappe.local.lang` from HTTP headers at beginning of request"""
	lang_codes = frappe.request.accept_languages.values()
	if not lang_codes:
		return frappe.local.lang

	guess = None
	if not lang_list:
		lang_list = get_all_languages() or []

	for l in lang_codes:
		code = l.strip()
		if not isinstance(code, text_type):
			code = text_type(code, 'utf-8')
		if code in lang_list or code == "en":
			guess = code
			break

		# check if parent language (pt) is setup, if variant (pt-BR)
		if "-" in code:
			code = code.split("-")[0]
			if code in lang_list:
				guess = code
				break

	return guess or frappe.local.lang

def get_user_lang(user=None):
	"""Set frappe.local.lang from user preferences on session beginning or resumption"""
	if not user:
		user = frappe.session.user

	# via cache
	lang = frappe.cache().hget("lang", user)

	if not lang:

		# if defined in user profile
		lang = frappe.db.get_value("User", user, "language")
		if not lang:
			lang = frappe.db.get_default("lang")

		if not lang:
			lang = frappe.local.lang or 'en'

		frappe.cache().hset("lang", user, lang)

	return lang

def get_lang_code(lang):
	return frappe.db.get_value('Language', {'language_name': lang}) or lang

def set_default_language(lang):
	"""Set Global default language"""
	if frappe.db.get_default("lang") != lang:
		frappe.db.set_default("lang", lang)
	frappe.local.lang = lang

def get_all_languages():
	"""Returns all language codes ar, ch etc"""
	def _get():
		if not frappe.db:
			frappe.connect()
		return frappe.db.sql_list('select name from tabLanguage')
	return frappe.cache().get_value('languages', _get)

def get_lang_dict():
	"""Returns all languages in dict format, full name is the key e.g. `{"english":"en"}`"""
	return dict(frappe.db.sql('select language_name, name from tabLanguage'))

def get_dict(fortype, name=None):
	"""Returns translation dict for a type of object.

	 :param fortype: must be one of `doctype`, `page`, `report`, `include`, `jsfile`, `boot`
	 :param name: name of the document for which assets are to be returned.
	 """
	fortype = fortype.lower()
	cache = frappe.cache()
	asset_key = fortype + ":" + (name or "-")
	translation_assets = cache.hget("translation_assets", frappe.local.lang, shared=True) or {}

	if not asset_key in translation_assets:
		if fortype=="doctype":
			messages = get_messages_from_doctype(name)
		elif fortype=="page":
			messages = get_messages_from_page(name)
		elif fortype=="report":
			messages = get_messages_from_report(name)
		elif fortype=="include":
			messages = get_messages_from_include_files()
		elif fortype=="jsfile":
			messages = get_messages_from_file(name)
		elif fortype=="template":
			messages = get_all_messages_from_template_files()
		elif fortype=="boot":
			messages = get_messages_from_include_files()
			messages += get_all_messages_from_js_files()
			messages += frappe.db.sql("select concat('Print Format: ', name), name from `tabPrint Format`")
			messages += frappe.db.sql("select concat('DocType: ', name), name from tabDocType")
			messages += frappe.db.sql("select concat('Role: ', name), name from tabRole")
			messages += frappe.db.sql("select concat('Module: ', name), name from `tabModule Def`")
			messages += frappe.db.sql("select concat('Page: ', name), name from `tabPage`")
			messages += frappe.db.sql("select concat('Report: ', name), name from `tabReport`")
			messages += "null"

		message_dict = make_dict_from_messages(messages)
		message_dict.update(get_dict_from_hooks(fortype, name))

		try:
			# get user specific translation data
			user_translations = get_user_translations(frappe.local.lang)
		except Exception:
			user_translations = None

		if user_translations:
			message_dict.update(user_translations)

		translation_assets[asset_key] = message_dict

		cache.hset("translation_assets", frappe.local.lang, translation_assets, shared=True)

	return translation_assets[asset_key]

def get_dict_from_hooks(fortype, name):
	translated_dict = {}

	hooks = frappe.get_hooks("get_translated_dict")
	for (hook_fortype, fortype_name) in hooks:
		if hook_fortype == fortype and fortype_name == name:
			for method in hooks[(hook_fortype, fortype_name)]:
				translated_dict.update(frappe.get_attr(method)())

	return translated_dict

def make_dict_from_messages(messages, full_dict=None):
	"""Returns translated messages as a dict in Language specified in `frappe.local.lang`

	:param messages: List of untranslated messages
	"""

	out = defaultdict(dict)
	if full_dict==None:
		full_dict = get_full_dict(frappe.local.lang)

	for m in messages:
		if m[0] in full_dict:
			if m[1] in full_dict[m[0]]:
				out[m[1]] = full_dict[m[0]][m[1]]

	return dict(out)

def get_lang_js(fortype, name):
	"""Returns code snippet to be appended at the end of a JS script.

	:param fortype: Type of object, e.g. `DocType`
	:param name: Document name
	"""
	return "\n\n$.extend(frappe._messages, %s)" % json.dumps(get_dict(fortype, name))

def get_full_dict(lang):
	"""Load and return the entire translations dictionary for a language
	:param lang: Language Code, e.g. `fr`
	"""
	if not lang:
		return {}
	# found in local, return!
	if getattr(frappe.local, 'lang_full_dict', None) and frappe.local.lang_full_dict.get(lang, None):
		return frappe.local.lang_full_dict

	frappe.local.lang_full_dict = load_lang(lang)

	return frappe.local.lang_full_dict

# TODO: Find a more elegant way combined with `get_full_dict`
def get_reduced_dict(lang):
	"""Load and return the entire translations dictionary, reduced for a language
	:param lang: Language Code, e.g. `fr`
	"""
	if not lang:
		return {}
	# found in local, return!
	if getattr(frappe.local, 'lang_reduced_dict', None) and frappe.local.lang_reduced_dict.get(lang, None):
		return frappe.local.lang_reduced_dict

	frappe.local.lang_reduced_dict = reduce(lambda a,b: a.update(b) or a, list(load_lang(lang).values()), {})

	try:
		# get user specific translation data
		user_translations = get_user_translations(lang)
	except Exception:
		user_translations = None

	if user_translations:
		frappe.local.lang_reduced_dict.update(user_translations)

	return frappe.local.lang_reduced_dict

def load_lang(lang, apps=None):
	"""Combine all translations from `.json` files in all `apps`.
	For derivative languages (es-GT), take translations from the
	base language (es) and then update translations from the child (es-GT)"""

	if lang=='en':
		return {}

	out = frappe.cache().hget("lang_full_dict", lang, shared=True)

	if not out:
		out = {}
		for app in (apps or frappe.get_all_apps(True)):
			path = os.path.join(frappe.get_pymodule_path(app), "translations", lang + ".json")
			out.update(get_translation_dict_from_file(path, lang, app) or {})

		if '-' in lang:
			parent = lang.split('-')[0]
			parent_out = load_lang(parent)
			parent_out.update(out)
			out = parent_out

		frappe.cache().hset("lang_full_dict", lang, out, shared=True)

	return out or {}

def get_translation_dict_from_file(path, lang, app):
	"""load translation dict from given path"""
	json_content = {}
	if os.path.exists(path):
		with open(path, 'r') as f:
			json_content = json.loads(f.read())

	return json_content

def get_user_translations(lang):
	out = frappe.cache().hget('lang_user_translations', lang)
	if out is None:
		out = {}
		for fields in frappe.get_all('Translation',
			fields= ["source_name", "target_name"], filters={'language': lang}):
				out.update({fields.source_name: fields.target_name})
		frappe.cache().hset('lang_user_translations', lang, out)

	return out


def clear_cache():
	"""Clear all translation assets from :meth:`frappe.cache`"""
	cache = frappe.cache()
	cache.delete_key("langinfo")

	# clear translations saved in boot cache
	cache.delete_key("bootinfo")
	cache.delete_key("lang_full_dict", shared=True)
	cache.delete_key("translation_assets", shared=True)
	cache.delete_key("lang_user_translations")

def get_messages_for_app(app):
	"""Returns all messages (list) for a specified `app`"""
	messages = []
	modules = ", ".join(['"{}"'.format(m.title().replace("_", " ")) \
		for m in frappe.local.app_modules[app]])

	# doctypes
	if modules:
		for name in frappe.db.sql_list("""select name from tabDocType
			where module in ({})""".format(modules)):
			messages.extend(get_messages_from_doctype(name))

		# pages
		for name, title in frappe.db.sql("""select name, title from tabPage
			where module in ({})""".format(modules)):
			messages.append(('Page: ' + (title or name), title or name))
			messages.extend(get_messages_from_page(name))


		# reports
		for name in frappe.db.sql_list("""select tabReport.name from tabDocType, tabReport
			where tabReport.ref_doctype = tabDocType.name
				and tabDocType.module in ({})""".format(modules)):
			messages.append(('Report: ' + name, name))
			messages.extend(get_messages_from_report(name))
			for i in messages:
				if not isinstance(i, tuple):
					raise Exception

	# workflow based on app.hooks.fixtures
	messages.extend(get_messages_from_workflow(app_name=app))

	# custom fields based on app.hooks.fixtures
	messages.extend(get_messages_from_custom_fields(app_name=app))

	# app_include_files
	messages.extend(get_all_messages_from_js_files(app))
	messages.extend(get_messages_from_include_files(app))

	# server_messages
	messages.extend(get_server_messages(app))
	return messages

def get_messages_from_doctype(name):
	"""Extract all translatable messages for a doctype. Includes labels, Python code,
	Javascript code, html templates"""
	messages = []
	meta = frappe.get_meta(name)

	messages = [meta.name, meta.module]

	if meta.description:
		messages.append(meta.description)

	# translations of field labels, description and options
	for d in meta.get("fields"):
		messages.extend([d.label, d.description])

		if d.fieldtype=='Select' and d.options:
			options = d.options.split('\n')
			if not "icon" in options[0]:
				messages.extend(options)

	# translations of roles
	for d in meta.get("permissions"):
		if d.role:
			messages.append(d.role)

	messages = [message for message in messages if message]
	messages = [('DocType: ' + name, message) for message in messages if is_translatable(message)]

	# extract from js, py files
	if not meta.custom:
		doctype_file_path = frappe.get_module_path(meta.module, "doctype", meta.name, meta.name)
		messages.extend(get_messages_from_file(doctype_file_path + ".js"))
		messages.extend(get_messages_from_file(doctype_file_path + "_list.js"))
		messages.extend(get_messages_from_file(doctype_file_path + "_list.html"))
		messages.extend(get_messages_from_file(doctype_file_path + "_calendar.js"))
		messages.extend(get_messages_from_file(doctype_file_path + "_dashboard.html"))

	# workflow based on doctype
	messages.extend(get_messages_from_workflow(doctype=name))

	return messages

def get_messages_from_workflow(doctype=None, app_name=None):
	assert doctype or app_name, 'doctype or app_name should be provided'

	# translations for Workflows
	workflows = []
	if doctype:
		workflows = frappe.get_all('Workflow', filters={'document_type': doctype})
	else:
		fixtures = frappe.get_hooks('fixtures', app_name=app_name) or []
		for fixture in fixtures:
			if isinstance(fixture, string_types) and fixture == 'Worflow':
				workflows = frappe.get_all('Workflow')
				break
			elif isinstance(fixture, dict) and fixture.get('dt', fixture.get('doctype')) == 'Workflow':
				workflows.extend(frappe.get_all('Workflow', filters=fixture.get('filters')))

	messages  = []
	for w in workflows:
		states = frappe.db.sql(
			'select distinct state from `tabWorkflow Document State` where parent=%s',
			(w['name'],), as_dict=True)

		messages.extend([('Workflow: ' + w['name'], state['state']) for state in states if is_translatable(state['state'])])

		states = frappe.db.sql(
			'select distinct message from `tabWorkflow Document State` where parent=%s and message is not null',
			(w['name'],), as_dict=True)

		messages.extend([("Workflow: " + w['name'], state['message'])
			for state in states if is_translatable(state['message'])])

		actions = frappe.db.sql(
			'select distinct action from `tabWorkflow Transition` where parent=%s',
			(w['name'],), as_dict=True)

		messages.extend([("Workflow: " + w['name'], action['action']) \
			for action in actions if is_translatable(action['action'])])

	return messages


def get_messages_from_custom_fields(app_name):
	fixtures = frappe.get_hooks('fixtures', app_name=app_name) or []
	custom_fields = []

	for fixture in fixtures:
		if isinstance(fixture, string_types) and fixture == 'Custom Field':
			custom_fields = frappe.get_all('Custom Field', fields=['name','label', 'description', 'fieldtype', 'options'])
			break
		elif isinstance(fixture, dict) and fixture.get('dt', fixture.get('doctype')) == 'Custom Field':
			custom_fields.extend(frappe.get_all('Custom Field', filters=fixture.get('filters'),
				fields=['name','label', 'description', 'fieldtype', 'options']))

	messages = []
	for cf in custom_fields:
		for prop in ('label', 'description'):
			if not cf.get(prop) or not is_translatable(cf[prop]):
				continue
			messages.append(('Custom Field - {}: {}'.format(prop, cf['name']), cf[prop]))
		if cf['fieldtype'] == 'Selection' and cf.get('options'):
			for option in cf['options'].split('\n'):
				if option and 'icon' not in option and is_translatable(option):
					messages.append(('Custom Field - Description: ' + cf['name'], option))

	return messages

def get_messages_from_page(name):
	"""Returns all translatable strings from a :class:`frappe.core.doctype.Page`"""
	return _get_messages_from_page_or_report("Page", name)

def get_messages_from_report(name):
	"""Returns all translatable strings from a :class:`frappe.core.doctype.Report`"""
	report = frappe.get_doc("Report", name)
	messages = _get_messages_from_page_or_report("Report", name,
		frappe.db.get_value("DocType", report.ref_doctype, "module"))
	# TODO position here!
	if report.query:
		messages.extend([(None, message) for message in re.findall('"([^:,^"]*):', report.query) if is_translatable(message)])
	messages.append((None,report.report_name))
	return messages

def _get_messages_from_page_or_report(doctype, name, module=None):
	if not module:
		module = frappe.db.get_value(doctype, name, "module")

	doc_path = frappe.get_module_path(module, doctype, name)

	messages = get_messages_from_file(os.path.join(doc_path, frappe.scrub(name) +".py"))

	if os.path.exists(doc_path):
		for filename in os.listdir(doc_path):
			if filename.endswith(".js") or filename.endswith(".html"):
				messages += get_messages_from_file(os.path.join(doc_path, filename))

	return messages

def get_server_messages(app):
	"""Extracts all translatable strings (tagged with :func:`frappe._`) from Python modules
		inside an app"""
	messages = []
	file_extensions = ('.py', '.html', '.js', '.vue')
	for basepath, folders, files in os.walk(frappe.get_pymodule_path(app)):
		for dontwalk in (".git", "public", "locale"):
			if dontwalk in folders: folders.remove(dontwalk)

		for f in files:
			f = frappe.as_unicode(f)
			if f.endswith(file_extensions):
				messages.extend(get_messages_from_file(os.path.join(basepath, f)))

	return messages

def get_messages_from_include_files(app_name=None):
	"""Returns messages from js files included at time of boot like desk.min.js for desk and web"""
	messages = []
	for file in (frappe.get_hooks("app_include_js", app_name=app_name) or []) + (frappe.get_hooks("web_include_js", app_name=app_name) or []):
		messages.extend(get_messages_from_file(os.path.join(frappe.local.sites_path, file)))

	for app in ([app_name] if app_name else frappe.get_installed_apps()):
		if os.path.isfile(frappe.get_app_path(app, "public/build.json")):
			with open(frappe.get_app_path(app, "public/build.json"), 'r') as f:

				for f in json.loads(f.read()):
					if not f.startswith("concat:"):
						messages.extend(get_messages_from_file(os.path.join(frappe.local.sites_path, "assets/" + f)))

	return messages

def get_all_messages_from_js_files(app_name=None):
	"""Extracts all translatable strings from app `.js` files"""
	messages = []
	for app in ([app_name] if app_name else frappe.get_installed_apps()):
		if os.path.exists(frappe.get_app_path(app, "public")):
			for basepath, dummy, files in os.walk(frappe.get_app_path(app, "public")):
				if "frappe/public/js/lib" in basepath:
					continue

				if os.path.isfile(frappe.get_app_path(app, "public/build.json")):
					with open(frappe.get_app_path(app, "public/build.json"), 'r') as f:
						built_files = json.loads(f.read())
						built_files = reduce(lambda a,b: a.extend(b) or a, list(built_files.values()), [])

				for fname in files:
					if fname not in built_files and (fname.endswith(".js") or fname.endswith(".html") or fname.endswith(".vue")):
						messages.extend(get_messages_from_file(os.path.join(basepath, fname)))

	return messages

def get_all_messages_from_template_files(app_name=None):
	"""Extracts all translatable strings from app templates files"""
	messages = []
	for app in ([app_name] if app_name else frappe.get_installed_apps()):
		if os.path.exists(frappe.get_app_path(app, "templates")):
			for basepath, dummy, files in os.walk(frappe.get_app_path(app, "templates")):
				for fname in files:
					if fname.endswith(".js") or fname.endswith(".html") or fname.endswith(".vue"):
						messages.extend(get_messages_from_file(os.path.join(basepath, fname)))

	return messages

def get_messages_from_file(path):
	"""Returns a list of transatable strings from a code file

	:param path: path of the code file
	"""
	apps_path = get_bench_dir()
	if os.path.exists(path):
		with open(path, 'r') as sourcefile:
			return [(os.path.relpath(path, apps_path),
					message) for pos, message in extract_messages_from_code(sourcefile.read(), path.endswith(".py"))]
	else:
		return []

def extract_messages_from_code(code, is_py=False):
	"""Extracts translatable srings from a code file

	:param code: code from which translatable files are to be extracted
	:param is_py: include messages in triple quotes e.g. `_('''message''')`"""
	try:
		code = frappe.as_unicode(render_include(code))
	except (TemplateError, ImportError, InvalidIncludePath, IOError):
		# Exception will occur when it encounters John Resig's microtemplating code
		pass

	messages = []
	messages += [(m.start(), m.groups()[0]) for m in re.compile('_\("([^"]*)"').finditer(code)]
	messages += [(m.start(), m.groups()[0]) for m in re.compile("_\('([^']*)'").finditer(code)]
	if is_py:
		messages += [(m.start(), m.groups()[0]) for m in re.compile('_\("{3}([^"]*)"{3}.*\)').finditer(code)]

	messages = [(pos, message) for pos, message in messages if is_translatable(message)]
	return pos_to_line_no(messages, code)

def is_translatable(m):
	if re.search("[a-zA-Z]", m) and not m.startswith("fa fa-") and not m.startswith("fas fa-") and not m.startswith("far fa-") and not m.startswith("uil uil-") and not m.endswith("px") and not m.startswith("eval:"):
		return True
	return False

def pos_to_line_no(messages, code):
	ret = []
	messages = sorted(messages, key=lambda x: x[0])
	newlines = [m.start() for m in re.compile('\\n').finditer(code)]
	line = 1
	newline_i = 0
	for pos, message in messages:
		while newline_i < len(newlines) and pos > newlines[newline_i]:
			line+=1
			newline_i+= 1
		ret.append((line, message))
	return ret

def write_json_file(path, app_messages):
	"""Write translation JSON file.

	:param path: File path, usually `[app]/translations`.
	:param app_messages: Translatable strings for this app.
	"""
	with open(path, 'w', encoding="utf8", newline=os.linesep) as msgfile:
		json.dump(app_messages, msgfile, ensure_ascii=False, indent=4, sort_keys=True)
		msgfile.write(os.linesep)

def get_untranslated(lang, untranslated_file=None, get_all=False, app=None, write=True):
	"""Returns all untranslated strings for a language and writes in a file
	If a translation is already present in another file, a new translation will be initialized.
	Else the translation will be empty.
	If argument `get_all` is True, the translations will not be initialized.

	:param lang: Language code.
	:param untranslated_file: Output file path.
	:param get_all: Return all strings, translated or not.
	:param app: Select untranslated strings for a particular app"""
	clear_cache()

	messages = []
	untranslated = defaultdict(lambda: defaultdict(dict))
	if app:
		messages = get_messages_for_app(app)
	else:
		for app in frappe.get_all_apps(True):
			messages.extend(get_messages_for_app(app))

	messages = messages

	def escape_newlines(s):
		return (s.replace("\\\n", "|||||")
				.replace("\\n", "||||")
				.replace("\n", "|||"))

	full_dict = load_lang(lang, [app])
	comparison_dict = reduce(lambda a,b: a.update(b) or a, list(full_dict.values()), {})
	if get_all:
		print(str(len(messages)) + " messages")
		for m in messages:
				untranslated[m[0]][escape_newlines(m[1])] = get_existing_translation(escape_newlines(m[1]), comparison_dict)

		if write:
			write_json_file(untranslated_file, untranslated)
		else:
			return untranslated

	else:
		messages_count = 0
		untranslated_count = 0

		for m in messages:
			messages_count += 1
			if m[0] and m[0] not in full_dict:
				untranslated_count += 1
				untranslated[m[0]][escape_newlines(m[1])] = get_existing_translation(escape_newlines(m[1]), comparison_dict)

			elif m[0] and m[1] not in full_dict[m[0]]:
				untranslated_count += 1
				untranslated[m[0]][escape_newlines(m[1])] = get_existing_translation(escape_newlines(m[1]), comparison_dict)

		if untranslated:
			print(str(untranslated_count) + " missing translations of " + str(messages_count))
			
			if write:
				write_json_file(untranslated_file, untranslated)
			else:
				return untranslated

		else:
			print("all translated!")

def get_existing_translation(key, comparison_dict):
	if key in comparison_dict:
		return comparison_dict[key]
	else:
		return ''

def update_translations(lang, translated_data, app, is_file=True):
	"""Update translations from a source and target file for a given language.

	:param lang: Language code (e.g. `en`).
	:param untranslated_file: File path with the messages in English.
	:param translated_file: File path with messages in language to be updated.
	:param app: Select untranslated strings for a particular app"""
	clear_cache()
	full_dict = load_lang(lang, [app])

	if full_dict:
		def restore_newlines(s):
			return (s.replace("|||||", "\\\n")
					.replace("| | | | |", "\\\n")
					.replace("||||", "\\n")
					.replace("| | | |", "\\n")
					.replace("|||", "\n")
					.replace("| | |", "\n"))

		translation_dict = defaultdict(dict)
		for k in full_dict:
			for m in full_dict[k]:
				translation_dict[k][m] = full_dict[restore_newlines(k)][restore_newlines(m)]

		if is_file:
			new_translations = frappe._dict(frappe.get_file_json(translated_data))
		else:
			new_translations = translated_data

		for k in new_translations:
			for m in new_translations[k]:
				if new_translations[k][m] != "":
					translation_dict[k][restore_newlines(m)] = restore_newlines(new_translations[k][m])

		write_translations_file(app, lang, translation_dict)

def rebuild_all_translation_files():
	"""Rebuild all translation files: `[app]/translations/[lang].csv`."""
	for lang in get_all_languages():
		for app in frappe.get_all_apps():
			write_translations_file(app, lang)

def write_translations_file(app, lang, app_messages=None):
	"""Write a translation file for a given language.

	:param app: `app` for which translations are to be written.
	:param lang: Language code.
	:param app_messages: Source strings (optional).
	"""
	if not app_messages:
		app_messages = get_messages_for_app(app)

	if not app_messages:
		return

	tpath = frappe.get_pymodule_path(app, "translations")
	frappe.create_folder(tpath)
	write_json_file(os.path.join(tpath, lang + ".json"), app_messages)

def send_translations(translation_dict):
	"""Append translated dict in `frappe.local.response`"""
	if "__messages" not in frappe.local.response:
		frappe.local.response["__messages"] = {}

	frappe.local.response["__messages"].update(translation_dict)

def get_bench_dir():
	return os.path.join(frappe.__file__, '..', '..', '..', '..')

def rename_language(old_name, new_name):
	if not frappe.db.exists('Language', new_name):
		return

	language_in_system_settings = frappe.db.get_single_value("System Settings", "language")
	if language_in_system_settings == old_name:
		frappe.db.set_value("System Settings", "System Settings", "language", new_name)

	frappe.db.sql("""update `tabUser` set language=%(new_name)s where language=%(old_name)s""",
		{ "old_name": old_name, "new_name": new_name })

@frappe.whitelist()
def update_translations_for_source(source=None, translation_dict=None):
	if not (source and translation_dict):
		return

	translation_dict = json.loads(translation_dict)

	# for existing records
	translation_records = frappe.db.get_values('Translation', { 'source_name': source }, ['name', 'language'],  as_dict=1)
	for d in translation_records:
		if translation_dict.get(d.language, None):
			doc = frappe.get_doc('Translation', d.name)
			doc.target_name = translation_dict.get(d.language)
			doc.save()
			# done with this lang value
			translation_dict.pop(d.language)
		else:
			frappe.delete_doc('Translation', d.name)

	# remaining values are to be inserted
	for lang, target_name in iteritems(translation_dict):
		doc = frappe.new_doc('Translation')
		doc.language = lang
		doc.source_name = source
		doc.target_name = target_name
		doc.save()

	return translation_records

@frappe.whitelist()
def get_translations(source_name):
	if is_html(source_name):
		source_name = strip_html_tags(source_name)

	return frappe.db.get_list('Translation',
		fields = ['name', 'language', 'target_name as translation'],
		filters = {
			'source_name': source_name
		}
	)

def legacy_csv_files_to_json(apps=None):
	for app in apps if apps else frappe.get_installed_apps():
		for lang in get_all_languages():
			csv_path = os.path.join(frappe.get_pymodule_path(app), "translations", lang + ".csv")
			json_path = os.path.join(frappe.get_pymodule_path(app), "translations", lang + ".json")

			if os.path.exists(csv_path):
				csv_content = read_csv_file(csv_path)
				jsonfile = open(json_path, 'w', encoding='utf8')

				result = {}

				for l in csv_content:
					l[0] = l[0].split(' +', 1)[0]

				for x in csv_content:
					if x[0] in result:
						result[x[0]].update({x[1]:x[2]})
					else:
						result[x[0]] = {x[1]:x[2]}

				json.dump(result, jsonfile, ensure_ascii=False)
				jsonfile.write(os.linesep)

				os.remove(csv_path)

def merge_existing_translations_for_language(apps=None, langs=None):
	for app in apps if apps else frappe.get_installed_apps():

		for lang in langs if langs else get_all_languages():
			print("Language: ", lang)
			untranslated = get_untranslated(lang=lang, get_all=False, app=app, write=False)
			if untranslated:
				update_translations(lang=lang, translated_data=untranslated, app=app, is_file=False)

def cleanup_translation_files(apps=None, langs=None):
	for app in apps if apps else frappe.get_installed_apps():
		messages = []
		messages.extend(get_messages_for_app(app))

		for lang in langs if langs else get_all_languages():
			print("Language: ", lang)
			existing_translations = {}
			cleaned_translations = defaultdict(lambda: defaultdict(dict))
			path = os.path.join(frappe.get_pymodule_path(app), "translations", lang + ".json")
			existing_translations.update(get_translation_dict_from_file(path, lang, app) or {})

			count = 0
			if existing_translations:
				for key in existing_translations:
					if key in set([x[0] for x in messages]):
						for t in existing_translations[key]:
							if t in set([x[1] for x in messages]):
								count += 1

								cleaned_translations[key][t] = existing_translations[key][t]

				print(str(count) + " clean messages")
				write_translations_file(app, lang, app_messages=dict(cleaned_translations))

def read_csv_file(path):
	"""Read CSV file and return as list of list

	:param path: File path"""
	from csv import reader

	if PY2:
		with codecs.open(path, 'r', 'utf-8') as msgfile:
			data = msgfile.read()

			# for japanese! #wtf
			data = data.replace(chr(28), "").replace(chr(29), "")
			data = reader([r.encode('utf-8') for r in data.splitlines()])
			newdata = [[text_type(val, 'utf-8') for val in row] for row in data]
	else:
		with io.open(path, mode='r', encoding='utf-8', newline='') as msgfile:
			data = reader(msgfile)
			newdata = [[ val for val in row ] for row in data]
	return newdata