# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
"""
	frappe.translate
	~~~~~~~~~~~~~~~~

	Translation tools for frappe
"""

import functools
import io
import itertools
import json
import operator
import os
import re
from typing import List, Tuple, Union

from pypika.terms import PseudoColumn

import frappe
from frappe.model.utils import InvalidIncludePath, render_include
from frappe.query_builder import DocType, Field
from frappe.utils import cstr, get_bench_path, is_html, strip, strip_html_tags
from frappe.utils.csvutils import to_csv

TRANSLATE_PATTERN = re.compile(
	r"_\([\s\n]*"  # starts with literal `_(`, ignore following whitespace/newlines
	# BEGIN: message search
	r"([\"']{,3})"  # start of message string identifier - allows: ', ", """, '''; 1st capture group
	r"(?P<message>((?!\1).)*)"  # Keep matching until string closing identifier is met which is same as 1st capture group
	r"\1"  # match exact string closing identifier
	# END: message search
	# BEGIN: python context search
	r"([\s\n]*,[\s\n]*context\s*=\s*"  # capture `context=` with ignoring whitespace
	r"([\"'])"  # start of context string identifier; 5th capture group
	r"(?P<py_context>((?!\5).)*)"  # capture context string till closing id is found
	r"\5"  # match context string closure
	r")?"  # match 0 or 1 context strings
	# END: python context search
	# BEGIN: JS context search
	r"(\s*,\s*(.)*?\s*(,\s*"  # skip message format replacements: ["format", ...] | null | []
	r"([\"'])"  # start of context string; 11th capture group
	r"(?P<js_context>((?!\11).)*)"  # capture context string till closing id is found
	r"\11"  # match context string closure
	r")*"
	r")*"  # match one or more context string
	# END: JS context search
	r"[\s\n]*\)"  # Closing function call ignore leading whitespace/newlines
)


def get_language(lang_list: List = None) -> str:
	"""Set `frappe.local.lang` from HTTP headers at beginning of request
	Order of priority for setting language:
	1. Form Dict => _lang
	2. Cookie => preferred_language (Non authorized user)
	3. Request Header => Accept-Language (Non authorized user)
	4. User document => language
	5. System Settings => language
	"""
	is_logged_in = frappe.session.user != "Guest"

	# fetch language from form_dict
	if frappe.form_dict._lang:
		language = get_lang_code(frappe.form_dict._lang or get_parent_language(frappe.form_dict._lang))
		if language:
			return language

	# use language set in User or System Settings if user is logged in
	if is_logged_in:
		return frappe.local.lang

	lang_set = set(lang_list or get_all_languages() or [])

	# fetch language from cookie
	preferred_language_cookie = get_preferred_language_cookie()

	if preferred_language_cookie:
		if preferred_language_cookie in lang_set:
			return preferred_language_cookie

		parent_language = get_parent_language(language)
		if parent_language in lang_set:
			return parent_language

	# fetch language from request headers
	accept_language = list(frappe.request.accept_languages.values())

	for language in accept_language:
		if language in lang_set:
			return language

		parent_language = get_parent_language(language)
		if parent_language in lang_set:
			return parent_language

	# fallback to language set in User or System Settings
	return frappe.local.lang


@functools.lru_cache()
def get_parent_language(lang: str) -> str:
	"""If the passed language is a variant, return its parent
	Eg:
	        1. zh-TW -> zh
	        2. sr-BA -> sr
	"""
	is_language_variant = "-" in lang
	if is_language_variant:
		return lang[: lang.index("-")]


def get_user_lang(user: str = None) -> str:
	"""Set frappe.local.lang from user preferences on session beginning or resumption"""
	user = user or frappe.session.user
	lang = frappe.cache().hget("lang", user)

	if not lang:
		# User.language => Session Defaults => frappe.local.lang => 'en'
		lang = (
			frappe.db.get_value("User", user, "language")
			or frappe.db.get_default("lang")
			or frappe.local.lang
			or "en"
		)

		frappe.cache().hset("lang", user, lang)

	return lang


def get_lang_code(lang: str) -> Union[str, None]:
	return frappe.db.get_value("Language", {"name": lang}) or frappe.db.get_value(
		"Language", {"language_name": lang}
	)


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
		return frappe.db.sql_list("select name from tabLanguage")

	return frappe.cache().get_value("languages", _get)


def get_all_language_with_name():
	return frappe.db.get_all("Language", ["language_code", "language_name"])


def get_lang_dict():
	"""Returns all languages in dict format, full name is the key e.g. `{"english":"en"}`"""
	result = dict(
		frappe.get_all("Language", fields=["language_name", "name"], order_by="modified", as_list=True)
	)
	return result


def get_dict(fortype, name=None):
	"""Returns translation dict for a type of object.

	:param fortype: must be one of `doctype`, `page`, `report`, `include`, `jsfile`, `boot`
	:param name: name of the document for which assets are to be returned.
	"""
	fortype = fortype.lower()
	cache = frappe.cache()
	asset_key = fortype + ":" + (name or "-")
	translation_assets = cache.hget("translation_assets", frappe.local.lang, shared=True) or {}

	if asset_key not in translation_assets:
		if fortype == "doctype":
			messages = get_messages_from_doctype(name)
		elif fortype == "page":
			messages = get_messages_from_page(name)
		elif fortype == "report":
			messages = get_messages_from_report(name)
		elif fortype == "include":
			messages = get_messages_from_include_files()
		elif fortype == "jsfile":
			messages = get_messages_from_file(name)
		elif fortype == "pyfile":
			messages = get_messages_from_file(name)
		elif fortype == "template":
			messages = get_all_messages_from_template_files()
		elif fortype == "boot":
			messages = get_messages_from_include_files()
			messages += get_all_messages_from_js_files()
			messages += get_messages_from_doctype("DocPerm")
			messages += get_messages_from_navbar()
			messages += (
				frappe.qb.from_("Print Format").select(PseudoColumn("'Print Format:'"), "name")
			).run()
			messages += (frappe.qb.from_("DocType").select(PseudoColumn("'DocType:'"), "name")).run()
			messages += frappe.qb.from_("Role").select(PseudoColumn("'Role:'"), "name").run()
			messages += (frappe.qb.from_("Module Def").select(PseudoColumn("'Module:'"), "name")).run()
			messages += (
				frappe.qb.from_("Page").where(Field("title").isnotnull()).select(PseudoColumn("''"), "title")
			).run()
			messages += (frappe.qb.from_("Report").select(PseudoColumn("'Report:'"), "name")).run()
			messages += (
				frappe.qb.from_("Workspace Shortcut")
				.where(Field("format").isnotnull())
				.select(PseudoColumn("''"), "format")
			).run()
			messages += get_messages_from_workspaces()
			messages += (
				frappe.qb.from_("Web Template").select(PseudoColumn("'Web Template:'"), "name")
			).run()
			messages += (
				frappe.qb.from_("Web Template Field")
				.where(Field("label").isnotnull())
				.select(PseudoColumn("'Web Template Field:'"), "label")
			).run()
			messages += (frappe.qb.from_("Onboarding Step").select(PseudoColumn("''"), "title")).run()
			messages += (
				frappe.qb.from_("Number Card").select(PseudoColumn("'Number Card:'"), "label")
			).run()
			messages += (
				frappe.qb.from_("Dashboard Chart").select(PseudoColumn("'Dashboard Chart:'"), "chart_name")
			).run()

		messages = deduplicate_messages(messages)
		message_dict = make_dict_from_messages(messages, load_user_translation=False)
		message_dict.update(get_dict_from_hooks(fortype, name))

		try:
			# get user specific translation data
			user_translations = get_user_translations(frappe.local.lang)
		except Exception:
			user_translations = {}

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


def make_dict_from_messages(messages, full_dict=None, load_user_translation=True):
	"""Returns translated messages as a dict in Language specified in `frappe.local.lang`

	:param messages: List of untranslated messages
	"""
	out = {}
	if full_dict is None:
		if load_user_translation:
			full_dict = get_full_dict(frappe.local.lang)
		else:
			full_dict = load_lang(frappe.local.lang)

	for m in messages:
		if m[1] in full_dict:
			out[m[1]] = full_dict[m[1]]
		# check if msg with context as key exist eg. msg:context
		if len(m) > 2 and m[2]:
			key = m[1] + ":::" + m[2]
			if full_dict.get(key):
				out[key] = full_dict[key]

	return out


def get_lang_js(fortype, name):
	"""Returns code snippet to be appended at the end of a JS script.

	:param fortype: Type of object, e.g. `DocType`
	:param name: Document name
	"""
	return "\n\n$.extend(frappe._messages, %s)" % json.dumps(get_dict(fortype, name))


def get_full_dict(lang):
	"""Load and return the entire translations dictionary for a language from :meth:`frape.cache`

	:param lang: Language Code, e.g. `hi`
	"""
	if not lang:
		return {}

	# found in local, return!
	if getattr(frappe.local, "lang_full_dict", None) is not None:
		return frappe.local.lang_full_dict

	frappe.local.lang_full_dict = load_lang(lang)

	try:
		# get user specific transaltion data
		user_translations = get_user_translations(lang)
		frappe.local.lang_full_dict.update(user_translations)
	except Exception:
		pass

	return frappe.local.lang_full_dict


def load_lang(lang, apps=None):
	"""Combine all translations from `.csv` files in all `apps`.
	For derivative languages (es-GT), take translations from the
	base language (es) and then update translations from the child (es-GT)"""

	if lang == "en":
		return {}

	out = frappe.cache().hget("lang_full_dict", lang, shared=True)
	if not out:
		out = {}
		for app in apps or frappe.get_all_apps(True):
			path = os.path.join(frappe.get_pymodule_path(app), "translations", lang + ".csv")
			out.update(get_translation_dict_from_file(path, lang, app) or {})

		if "-" in lang:
			parent = lang.split("-")[0]
			parent_out = load_lang(parent)
			parent_out.update(out)
			out = parent_out

		frappe.cache().hset("lang_full_dict", lang, out, shared=True)

	return out or {}


def get_translation_dict_from_file(path, lang, app, throw=False):
	"""load translation dict from given path"""
	translation_map = {}
	if os.path.exists(path):
		csv_content = read_csv_file(path)

		for item in csv_content:
			if len(item) == 3 and item[2]:
				key = item[0] + ":::" + item[2]
				translation_map[key] = strip(item[1])
			elif len(item) in [2, 3]:
				translation_map[item[0]] = strip(item[1])
			elif item:
				msg = "Bad translation in '{app}' for language '{lang}': {values}".format(
					app=app, lang=lang, values=cstr(item)
				)
				frappe.log_error(message=msg, title="Error in translation file")
				if throw:
					frappe.throw(msg, title="Error in translation file")

	return translation_map


def get_user_translations(lang):
	if not frappe.db:
		frappe.connect()

	out = frappe.cache().hget("lang_user_translations", lang)
	if out is None:
		out = {}
		user_translations = frappe.get_all(
			"Translation",
			fields=["source_text", "translated_text", "context"],
			filters={"language": lang},
		)

		for translation in user_translations:
			key = translation.source_text
			value = translation.translated_text
			if translation.context:
				key += ":::" + translation.context
			out[key] = value

		frappe.cache().hset("lang_user_translations", lang, out)

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


def get_messages_for_app(app, deduplicate=True, context=False):
	"""Returns all messages (list) for a specified `app`"""
	messages = []
	modules = [frappe.unscrub(m) for m in frappe.local.app_modules[app]]

	# doctypes
	if modules:
		if isinstance(modules, str):
			modules = [modules]

		filtered_doctypes = (
			frappe.qb.from_("DocType").where(Field("module").isin(modules)).select("name").run(pluck=True)
		)
		for name in filtered_doctypes:
			messages.extend(get_messages_from_doctype(name, context))

		# pages
		filtered_pages = (
			frappe.qb.from_("Page").where(Field("module").isin(modules)).select("name", "title").run()
		)
		for name, title in filtered_pages:
			messages.append(("Page: " + (title or name), title or name))
			messages.extend(get_messages_from_page(name))

		# reports
		report = DocType("Report")
		doctype = DocType("DocType")
		names = (
			frappe.qb.from_(doctype)
			.from_(report)
			.where((report.ref_doctype == doctype.name) & doctype.module.isin(modules))
			.select(report.name)
			.run(pluck=True)
		)
		for name in names:
			messages.append(("Report: " + name, name))
			messages.extend(get_messages_from_report(name))
			for i in messages:
				if not isinstance(i, tuple):
					raise Exception

		# workspaces
		workspace = DocType("Workspace")
		for name in (
			frappe.qb.from_(workspace)
			.where(Field("module").isin(modules))
			.select(workspace.name)
			.run(pluck=True)
		):
			messages.extend(get_messages_from_workspace(name))

		dashboard_chart = DocType("Dashboard Chart")
		for name in (
			frappe.qb.from_(dashboard_chart)
			.where((Field("module").isin(modules) & (dashboard_chart.is_standard == 1)))
			.select(dashboard_chart.name)
			.run(pluck=True)
		):
			messages.append(("Dashboard Chart: " + name, name))

	if app == "frappe":
		# Web templates
		for name in frappe.db.sql_list("""select name from `tabWeb Template`"""):
			messages.append(("Web Template: " + name, name))

		for label in frappe.db.sql_list("""select label from `tabWeb Template Field`"""):
			messages.append(("Web Template Field: " + label, label))

		for label in frappe.db.sql_list("""select item_label from `tabNavbar Item`"""):
			if label:
				messages.append(("Navbar Item: " + label, label))

	# workflow based on app.hooks.fixtures
	messages.extend(get_messages_from_workflow(app_name=app))

	# custom fields based on app.hooks.fixtures
	messages.extend(get_messages_from_custom_fields(app_name=app))

	# app_include_files
	messages.extend(get_all_messages_from_js_files(app))
	messages.extend(get_messages_from_include_files(app))

	# server_messages
	messages.extend(get_server_messages(app))

	if deduplicate:
		messages = deduplicate_messages(messages)

	return messages


def get_messages_from_doctype(name, context=True):
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

		if d.fieldtype == "Select" and d.options:
			options = d.options.split("\n")
			if "icon" not in options[0]:
				messages.extend(options)

		if d.fieldtype == "HTML" and d.options:
			messages.append(d.options)

	# translations of actions
	for d in meta.get("actions"):
		messages.extend([d.label])

	# translations of roles
	for d in meta.get("permissions"):
		if d.role:
			messages.append(d.role)

	messages = [message for message in messages if message]
	if context:
		messages = [
			("DocType: " + name, message, name) for message in messages if is_translatable(message)
		]
	else:
		messages = [("DocType: " + name, message) for message in messages if is_translatable(message)]

	# extract from js, py files
	if not meta.custom:
		doctype_file_path = frappe.get_module_path(meta.module, "doctype", meta.name, meta.name)
		messages.extend(get_messages_from_file(doctype_file_path + ".js"))
		messages.extend(get_messages_from_file(doctype_file_path + "_list.js"))
		messages.extend(get_messages_from_file(doctype_file_path + "_list.html"))
		messages.extend(get_messages_from_file(doctype_file_path + "_tree.js"))
		messages.extend(get_messages_from_file(doctype_file_path + "_calendar.js"))
		messages.extend(get_messages_from_file(doctype_file_path + "_dashboard.html"))

		system_country = frappe.get_system_settings("country")
		if system_country:
			doctype_regional_file_path = frappe.get_module_path(
				meta.module, "doctype", meta.name, "regional", system_country
			)
			messages.extend(get_messages_from_file(doctype_regional_file_path + ".js"))
			messages.extend(get_messages_from_file(doctype_regional_file_path + "_list.js"))

		for hook in [
			"doctype_js",
			"doctype_list_js",
			"doctype_tree_js",
			"doctype_calendar_js",
		]:
			for path in get_code_files_via_hooks(hook, name):
				messages.extend(get_messages_from_file(path))

	# workflow based on doctype
	messages.extend(get_messages_from_workflow(doctype=name))

	return messages


def get_messages_from_workflow(doctype=None, app_name=None):
	assert doctype or app_name, "doctype or app_name should be provided"

	# translations for Workflows
	workflows = []
	if doctype:
		workflows = frappe.get_all("Workflow", filters={"document_type": doctype})
	else:
		fixtures = frappe.get_hooks("fixtures", app_name=app_name) or []
		for fixture in fixtures:
			if isinstance(fixture, str) and fixture == "Worflow":
				workflows = frappe.get_all("Workflow")
				break
			elif isinstance(fixture, dict) and fixture.get("dt", fixture.get("doctype")) == "Workflow":
				workflows.extend(frappe.get_all("Workflow", filters=fixture.get("filters")))

	messages = []
	document_state = DocType("Workflow Document State")
	for w in workflows:
		states = frappe.db.get_values(
			document_state,
			filters=document_state.parent == w["name"],
			fieldname="state",
			distinct=True,
			as_dict=True,
			order_by=None,
		)
		messages.extend(
			[
				("Workflow: " + w["name"], state["state"])
				for state in states
				if is_translatable(state["state"])
			]
		)
		states = frappe.db.get_values(
			document_state,
			filters=(document_state.parent == w["name"]) & (document_state.message.isnotnull()),
			fieldname="message",
			distinct=True,
			order_by=None,
			as_dict=True,
		)
		messages.extend(
			[
				("Workflow: " + w["name"], state["message"])
				for state in states
				if is_translatable(state["message"])
			]
		)

		actions = frappe.db.get_values(
			"Workflow Transition",
			filters={"parent": w["name"]},
			fieldname="action",
			as_dict=True,
			distinct=True,
			order_by=None,
		)

		messages.extend(
			[
				("Workflow: " + w["name"], action["action"])
				for action in actions
				if is_translatable(action["action"])
			]
		)

	return messages


def get_messages_from_custom_fields(app_name):
	fixtures = frappe.get_hooks("fixtures", app_name=app_name) or []
	custom_fields = []

	for fixture in fixtures:
		if isinstance(fixture, str) and fixture == "Custom Field":
			custom_fields = frappe.get_all(
				"Custom Field", fields=["name", "label", "description", "fieldtype", "options"]
			)
			break
		elif isinstance(fixture, dict) and fixture.get("dt", fixture.get("doctype")) == "Custom Field":
			custom_fields.extend(
				frappe.get_all(
					"Custom Field",
					filters=fixture.get("filters"),
					fields=["name", "label", "description", "fieldtype", "options"],
				)
			)

	messages = []
	for cf in custom_fields:
		for prop in ("label", "description"):
			if not cf.get(prop) or not is_translatable(cf[prop]):
				continue
			messages.append(("Custom Field - {}: {}".format(prop, cf["name"]), cf[prop]))
		if cf["fieldtype"] == "Selection" and cf.get("options"):
			for option in cf["options"].split("\n"):
				if option and "icon" not in option and is_translatable(option):
					messages.append(("Custom Field - Description: " + cf["name"], option))

	return messages


def get_messages_from_page(name):
	"""Returns all translatable strings from a :class:`frappe.core.doctype.Page`"""
	return _get_messages_from_page_or_report("Page", name)


def get_messages_from_report(name):
	"""Returns all translatable strings from a :class:`frappe.core.doctype.Report`"""
	report = frappe.get_doc("Report", name)
	messages = _get_messages_from_page_or_report(
		"Report", name, frappe.db.get_value("DocType", report.ref_doctype, "module")
	)

	if report.columns:
		context = (
			"Column of report '%s'" % report.name
		)  # context has to match context in `prepare_columns` in query_report.js
		messages.extend([(None, report_column.label, context) for report_column in report.columns])

	if report.filters:
		messages.extend([(None, report_filter.label) for report_filter in report.filters])

	if report.query:
		messages.extend(
			[
				(None, message)
				for message in re.findall('"([^:,^"]*):', report.query)
				if is_translatable(message)
			]
		)
	messages.append((None, report.report_name))
	return messages


def get_messages_from_workspaces():
	workspaces = frappe.qb.from_("Workspace").select("label", "content").run(as_dict=True)
	output = []

	for workspace in workspaces:
		if workspace.get("label"):
			output.append(("Workspace label: ", workspace.get("label")))
		if workspace.get("content"):
			content = frappe.parse_json(workspace.get("content"))
			for c in content:
				if c.get("type") == "header" and c.get("data", {}).get("text"):
					output.append(("Workspace header: ", frappe.utils.strip_html(c.get("data", {}).get("text"))))

	return tuple(output)


def get_messages_from_workspace(name):
	desk_page = frappe.get_doc("Workspace", name)
	messages = []

	for field in "label":
		if desk_page.get(field):
			messages.append(("Workspace label: " + name, desk_page.get(field)))

	if desk_page.get("content"):
		content = frappe.parse_json(desk_page.get("content"))
		for c in content:
			if c.get("type") == "header" and c.get("data", {}).get("text"):
				messages.append(("Workspace header: ", frappe.utils.strip_html(c.get("data", {}).get("text"))))

	for shortcut in desk_page.shortcuts:
		if shortcut.get("format"):
			messages.append(("Workspace Shortcut: " + name, shortcut.get("format")))
		if shortcut.get("label"):
			messages.append(("Workspace Shortcut: " + name, shortcut.get("label")))

	for card in desk_page.links:
		if card.get("label"):
			messages.append(("Workspace Link: " + name, card.get("label")))

	return messages


def _get_messages_from_page_or_report(doctype, name, module=None):
	if not module:
		module = frappe.db.get_value(doctype, name, "module")

	doc_path = frappe.get_module_path(module, doctype, name)

	messages = get_messages_from_file(os.path.join(doc_path, frappe.scrub(name) + ".py"))

	if os.path.exists(doc_path):
		for filename in os.listdir(doc_path):
			if filename.endswith(".js") or filename.endswith(".html"):
				messages += get_messages_from_file(os.path.join(doc_path, filename))

	return messages


def get_server_messages(app):
	"""Extracts all translatable strings (tagged with :func:`frappe._`) from Python modules
	inside an app"""
	messages = []
	file_extensions = (".py", ".html", ".js", ".vue")
	for basepath, folders, files in os.walk(frappe.get_pymodule_path(app)):
		for dontwalk in (".git", "public", "locale", "query_builder"):
			if dontwalk in folders:
				folders.remove(dontwalk)

		for f in files:
			f = frappe.as_unicode(f)
			if f.endswith(file_extensions):
				messages.extend(get_messages_from_file(os.path.join(basepath, f)))

	return messages


def get_messages_from_navbar():
	"""Return all labels from Navbar Items, as specified in Navbar Settings."""
	labels = frappe.get_all("Navbar Item", filters={"item_label": ("is", "set")}, pluck="item_label")
	return [("Navbar:", label, "Label of a Navbar Item") for label in labels]


def get_messages_from_include_files(app_name=None):
	"""Returns messages from js files included at time of boot like desk.min.js for desk and web"""
	from frappe.utils.jinja_globals import bundled_asset

	messages = []
	app_include_js = frappe.get_hooks("app_include_js", app_name=app_name) or []
	web_include_js = frappe.get_hooks("web_include_js", app_name=app_name) or []
	include_js = app_include_js + web_include_js

	for js_path in include_js:
		file_path = bundled_asset(js_path)
		relative_path = os.path.join(frappe.local.sites_path, file_path.lstrip("/"))
		messages_from_file = get_messages_from_file(relative_path)
		messages.extend(messages_from_file)

	return messages


def get_all_messages_from_js_files(app_name=None):
	"""Extracts all translatable strings from app `.js` files"""
	messages = []
	excluded_paths = ["frappe/public/js/lib", "frappe/public/dist"]
	for app in [app_name] if app_name else frappe.get_installed_apps():
		if os.path.exists(frappe.get_app_path(app, "public")):
			for basepath, dummy, files in os.walk(frappe.get_app_path(app, "public")):
				if any(bp in basepath for bp in excluded_paths):
					continue

				for fname in files:
					if fname.endswith(".js") or fname.endswith(".html") or fname.endswith(".vue"):
						messages.extend(get_messages_from_file(os.path.join(basepath, fname)))

	return messages


def get_all_messages_from_template_files(app_name=None):
	"""Extracts all translatable strings from app templates files"""
	messages = []
	for app in [app_name] if app_name else frappe.get_installed_apps():
		if os.path.exists(frappe.get_app_path(app, "templates")):
			for basepath, dummy, files in os.walk(frappe.get_app_path(app, "templates")):
				for fname in files:
					if fname.endswith(".js") or fname.endswith(".html") or fname.endswith(".vue"):
						messages.extend(get_messages_from_file(os.path.join(basepath, fname)))

	return messages


def get_messages_from_file(path: str) -> List[Tuple[str, str, str, str]]:
	"""Returns a list of transatable strings from a code file

	:param path: path of the code file
	"""
	frappe.flags.setdefault("scanned_files", [])
	# TODO: Find better alternative
	# To avoid duplicate scan
	if path in set(frappe.flags.scanned_files):
		return []

	frappe.flags.scanned_files.append(path)

	bench_path = get_bench_path()
	if os.path.exists(path):
		with open(path, "r") as sourcefile:
			try:
				file_contents = sourcefile.read()
			except Exception:
				print("Could not scan file for translation: {0}".format(path))
				return []

			return [
				(os.path.relpath(path, bench_path), message, context, line)
				for (line, message, context) in extract_messages_from_code(file_contents)
			]
	else:
		return []


def extract_messages_from_code(code):
	"""
	Extracts translatable strings from a code file
	:param code: code from which translatable files are to be extracted
	:param is_py: include messages in triple quotes e.g. `_('''message''')`
	"""
	from jinja2 import TemplateError

	try:
		code = frappe.as_unicode(render_include(code))

	# Exception will occur when it encounters John Resig's microtemplating code
	except (TemplateError, ImportError, InvalidIncludePath, IOError) as e:
		if isinstance(e, InvalidIncludePath):
			frappe.clear_last_message()

	messages = []
	for m in TRANSLATE_PATTERN.finditer(code):
		message = m.group("message")
		context = m.group("py_context") or m.group("js_context")
		pos = m.start()

		if is_translatable(message):
			messages.append([pos, message, context])

	return add_line_number(messages, code)


def is_translatable(m):
	if (
		re.search("[a-zA-Z]", m)
		and not m.startswith("fa fa-")
		and not m.startswith("fas fa-")
		and not m.startswith("far fa-")
		and not m.startswith("uil uil-")
		and not m.endswith("px")
		and not m.startswith("eval:")
	):
		return True
	return False


def add_line_number(messages, code):
	ret = []
	messages = sorted(messages, key=lambda x: x[0])
	newlines = [m.start() for m in re.compile(r"\\n").finditer(code)]
	line = 1
	newline_i = 0
	for pos, message, context in messages:
		while newline_i < len(newlines) and pos > newlines[newline_i]:
			line += 1
			newline_i += 1
		ret.append([line, message, context])
	return ret


def read_csv_file(path):
	"""Read CSV file and return as list of list

	:param path: File path"""
	from csv import reader

	with io.open(path, mode="r", encoding="utf-8", newline="") as msgfile:
		data = reader(msgfile)
		newdata = [[val for val in row] for row in data]

	return newdata


def write_csv_file(path, lang_dict):
	"""Write translation CSV file.

	:param path: File path, usually `[app]/translations`.
	:param app_messages: Translatable strings for this app.
	:param lang_dict: Full translated dict.
	"""
	lang_input = {k: v for k, v in sorted(lang_dict.items(), key=lambda item: item[0] + item[1])}
	output = []
	for key, value in lang_input.items():
		if not value:
			continue
		split_key = key.split(":::")
		context = split_key[1] if len(split_key) > 1 else ""
		output.append([split_key[0], value, context])

	with open(path, "w") as msgfile:
		msgfile.write(to_csv(output, quoting="QUOTE_MINIMAL", lineterminator="\n"))


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
	untranslated = []
	if app:
		messages = get_messages_for_app(app)
	else:
		for app in frappe.get_all_apps(True):
			messages.extend(get_messages_for_app(app))

	contextual_messages = []
	for m in messages:
		contextual_messages.append(m[1] + ":::" + m[2] if len(m) > 2 and m[2] else m[1])

	def escape_newlines(s):
		return s.replace("\\\n", "|||||").replace("\\n", "||||").replace("\n", "|µ||")

	if get_all:
		print(str(len(contextual_messages)) + " messages")
		output = []
		for m in contextual_messages:
			# replace \n with ||| so that internal linebreaks don't get split
			split_key = m.split(":::")
			context = split_key[1] if len(split_key) > 1 else ""
			output.append([escape_newlines(split_key[0]), "", context])

		with open(untranslated_file, "w") as f:
			f.write(to_csv(output, quoting="QUOTE_MINIMAL", lineterminator="\n"))

	else:
		full_dict = get_full_dict(lang)

		for m in contextual_messages:
			if not full_dict.get(m):
				untranslated.append(m)

		if untranslated:
			print(str(len(untranslated)) + " missing translations of " + str(len(messages)))
			output = []
			for m in untranslated:
				# replace \n with ||| so that internal linebreaks don't get split
				split_key = m.split(":::")
				context = split_key[1] if len(split_key) > 1 else ""
				output.append([escape_newlines(split_key[0]), "", context])
			with open(untranslated_file, "w") as f:
				f.write(to_csv(output, quoting="QUOTE_MINIMAL", lineterminator="\n"))
		else:
			print("all translated!")


def update_translations(lang, translated_file, app):
	"""Update translations from a source and target file for a given language.

	:param lang: Language code (e.g. `en`).
	:param untranslated_file: File path with the messages in English.
	:param translated_file: File path with messages in language to be updated.
	:param app: Select untranslated strings for a particular app"""
	clear_cache()
	full_dict = load_lang(lang, [app])
	if full_dict:

		def restore_newlines(s):
			return s.replace("||||||", "\\\n").replace("||||", "\\n").replace("|µ||", "\n")

		translation_dict = get_translation_dict_from_file(translated_file, lang, app)
		newdict = {}
		for key, value in translation_dict.items():
			# undo hack in get_untranslated
			newdict[restore_newlines(key)] = restore_newlines(value)

		full_dict.update(newdict)
		write_translations_file(app, lang, full_dict)


def rebuild_all_translation_files():
	"""Rebuild all translation files: `[app]/translations/[lang].csv`."""
	for lang in get_all_languages():
		for app in frappe.get_all_apps():
			write_translations_file(app, lang)


def write_translations_file(app, lang, full_dict=None):
	"""Write a translation file for a given language.

	:param app: `app` for which translations are to be written.
	:param lang: Language code.
	:param full_dict: Full translated language dict (optional).
	:param app_messages: Source strings (optional).
	"""
	tpath = frappe.get_pymodule_path(app, "translations")
	frappe.create_folder(tpath)
	write_csv_file(os.path.join(tpath, lang + ".csv"), full_dict or get_full_dict(lang))


@frappe.whitelist(allow_guest=True)
def get_required_file_messages(file):
	filepath = file[1:]
	translations = get_dict("jsfile", filepath)
	send_translations(translations)


def send_translations(translation_dict):
	"""Append translated dict in `frappe.local.response`"""
	if "__messages" not in frappe.local.response:
		frappe.local.response["__messages"] = {}

	frappe.local.response["__messages"].update(translation_dict)


def deduplicate_messages(messages):
	ret = []
	op = operator.itemgetter(1)
	messages = sorted(messages, key=op)
	for k, g in itertools.groupby(messages, op):
		ret.append(next(g))
	return ret


def rename_language(old_name, new_name):
	if not frappe.db.exists("Language", new_name):
		return

	language_in_system_settings = frappe.db.get_single_value("System Settings", "language")
	if language_in_system_settings == old_name:
		frappe.db.set_value("System Settings", "System Settings", "language", new_name)

	frappe.db.sql(
		"""update `tabUser` set language=%(new_name)s where language=%(old_name)s""",
		{"old_name": old_name, "new_name": new_name},
	)


@frappe.whitelist()
def update_translations_for_source(source=None, translation_dict=None):
	if not (source and translation_dict):
		return

	translation_dict = json.loads(translation_dict)

	if is_html(source):
		source = strip_html_tags(source)

	# for existing records
	translation_records = frappe.db.get_values(
		"Translation", {"source_text": source}, ["name", "language"], as_dict=1
	)
	for d in translation_records:
		if translation_dict.get(d.language, None):
			doc = frappe.get_doc("Translation", d.name)
			doc.translated_text = translation_dict.get(d.language)
			doc.save()
			# done with this lang value
			translation_dict.pop(d.language)
		else:
			frappe.delete_doc("Translation", d.name)

	# remaining values are to be inserted
	for lang, translated_text in translation_dict.items():
		doc = frappe.new_doc("Translation")
		doc.language = lang
		doc.source_text = source
		doc.translated_text = translated_text
		doc.save()

	return translation_records


@frappe.whitelist()
def get_translations(source_text):
	if is_html(source_text):
		source_text = strip_html_tags(source_text)

	return frappe.db.get_list(
		"Translation",
		fields=["name", "language", "translated_text as translation"],
		filters={"source_text": source_text},
	)


@frappe.whitelist(allow_guest=True)
def get_all_languages(with_language_name=False):
	"""Returns all language codes ar, ch etc"""

	def get_language_codes():
		return frappe.get_all("Language", pluck="name")

	def get_all_language_with_name():
		return frappe.db.get_all("language", ["language_code", "language_name"])

	if not frappe.db:
		frappe.connect()

	if with_language_name:
		return frappe.cache().get_value("languages_with_name", get_all_language_with_name)
	else:
		return frappe.cache().get_value("languages", get_language_codes)


@frappe.whitelist(allow_guest=True)
def set_preferred_language_cookie(preferred_language):
	frappe.local.cookie_manager.set_cookie("preferred_language", preferred_language)


def get_preferred_language_cookie():
	return frappe.request.cookies.get("preferred_language")


# TODO: Commonify with function in frappe.desk.form.meta
def get_code_files_via_hooks(hook, name):
	code_files = []
	for app_name in frappe.get_installed_apps():
		code_hook = frappe.get_hooks(hook, default={}, app_name=app_name)
		if not code_hook:
			continue

		files = code_hook.get(name, [])
		if not isinstance(files, list):
			files = [files]

		for file in files:
			path = frappe.get_app_path(app_name, *file.strip("/").split("/"))
			code_files.append(path)

	return code_files
