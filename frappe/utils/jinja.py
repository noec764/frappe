# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

from bs4 import BeautifulSoup


def get_jenv():
	import frappe
	from frappe.utils.safe_exec import get_safe_globals

	if not getattr(frappe.local, "jenv", None):
		from jinja2 import DebugUndefined
		from jinja2.sandbox import SandboxedEnvironment

		# frappe will be loaded last, so app templates will get precedence
		jenv = SandboxedEnvironment(loader=get_jloader(), undefined=DebugUndefined)
		set_filters(jenv)

		jenv.globals.update(get_safe_globals())

		methods, filters = get_jinja_hooks()
		jenv.globals.update(methods or {})
		jenv.filters.update(filters or {})

		frappe.local.jenv = jenv

	return frappe.local.jenv


def get_template(path):
	return get_jenv().get_template(path)


def get_email_from_template(name, args):
	from jinja2 import TemplateNotFound

	args = args or {}
	try:
		message = get_template("templates/emails/" + name + ".html").render(args)
	except TemplateNotFound as e:
		raise e

	try:
		text_content = get_template("templates/emails/" + name + ".txt").render(args)
	except TemplateNotFound:
		text_content = None

	return (message, text_content)


def validate_template(html):
	"""Throws exception if there is a syntax error in the Jinja Template"""
	from jinja2 import TemplateSyntaxError

	import frappe

	if not html:
		return

	jenv = get_jenv()
	try:
		jenv.from_string(html)
	except TemplateSyntaxError as e:
		frappe.msgprint(f"Line {e.lineno}: {e.message}")
		frappe.throw(frappe._("Syntax error in template"))


def render_template(template, context, is_path=None, safe_render=True):
	"""Render a template using Jinja

	:param template: path or HTML containing the jinja template
	:param context: dict of properties to pass to the template
	:param is_path: (optional) assert that the `template` parameter is a path
	:param safe_render: (optional) prevent server side scripting via jinja templating
	"""

	from jinja2 import TemplateError

	from frappe import _, get_traceback, throw

	if not template:
		return ""

	if is_path or guess_is_path(template):
		return get_jenv().get_template(template).render(context)
	else:
		if safe_render and ".__" in template:
			throw(_("Illegal template"))
		try:
			template = transform_template_blot(template, context)

			return get_jenv().from_string(template).render(context)
		except TemplateError:
			throw(
				title="Jinja Template Error",
				msg=f"<pre>{template}</pre><pre>{get_traceback()}</pre>",
			)


def guess_is_path(template):
	# template can be passed as a path or content
	# if its single line and ends with a html, then its probably a path
	if "\n" not in template and "." in template:
		extn = template.rsplit(".")[-1]
		if extn in ("html", "css", "scss", "py", "md", "json", "js", "xml"):
			return True

	return False


def get_jloader():
	import frappe

	if not getattr(frappe.local, "jloader", None):
		from jinja2 import ChoiceLoader, PackageLoader, PrefixLoader

		apps = frappe.get_hooks("template_apps")
		if not apps:
			apps = frappe.local.flags.web_pages_apps or frappe.get_installed_apps(sort=True)
			apps.reverse()

		if "frappe" not in apps:
			apps.append("frappe")

		frappe.local.jloader = ChoiceLoader(
			# search for something like app/templates/...
			[PrefixLoader({app: PackageLoader(app, ".") for app in apps})]
			# search for something like templates/...
			+ [PackageLoader(app, ".") for app in apps]
		)

	return frappe.local.jloader


def set_filters(jenv):
	import frappe
	from frappe.utils import cint, cstr, flt

	jenv.filters.update(
		{
			"json": frappe.as_json,
			"len": len,
			"int": cint,
			"str": cstr,
			"flt": flt,
		}
	)


def transform_template_blot(template, context):
	import frappe

	soup = BeautifulSoup(template, "html.parser")
	soup.insert(0, '{%- from "templates/letters/standard_macros.html" import render_table -%}')
	soup.insert(
		0,
		"{% "
		+ " set doc_values = frappe.get_doc('{}', '{}') ".format(
			context.get("doctype"), context.get("name")
		)
		+ " %}",
	)
	fields = soup.find_all("template-blot")

	if not fields:
		return template

	doctypes = []

	for f in fields:
		new_tag = soup.new_tag("span")

		if f.get("data-doctype") == "Custom Functions" and f.get("data-function") != "null":
			content = "{{" + "{}|safe".format(f.get("data-function").split("#", 1)[-1]) + "}}"
			if f.get("data-function").startswith("Signature"):
				content = soup.new_tag("img", src=content, height=200, width=200)
				new_tag.append(content)
			else:
				new_tag.string = content

		else:
			if (
				f.get("data-doctype") != "Custom Functions"
				and {f.get("data-doctype"): f.get("data-reference")} not in doctypes
				and f.get("data-reference") != "name"
			):
				doctypes.append({f.get("data-doctype"): f.get("data-reference")})

			new_tag.string = "{{ " + f"{get_newtag_string(f, context)}|safe" + " }}"

		f.replace_with(new_tag)

	for doctype in doctypes:
		for key in doctype:
			get_doc = (
				"{% "
				+ " set {0} = frappe.get_doc('{1}', {2}) if {2} else None".format(
					key.replace(" ", "").lower(),
					key,
					f"doc.{doctype[key]}" if "doc" in context else doctype[key],
				)
				+ " %}"
			)
			soup.insert(0, get_doc)

	for method in frappe.get_hooks("jinja_template_extensions"):
		soup = frappe.get_attr(method)(soup)

	return soup.prettify()


def get_newtag_string(field, context):
	docname = None

	if (field.get("data-reference") == "name" and "doc" in context) or field.get(
		"data-reference"
	) != "name":
		docname = field["data-doctype"].replace(" ", "").lower()

	if field.get("data-fieldtype") == "Table":
		value = "render_table({0}.meta.get_field('{1}').as_dict(), {0})".format(
			docname or "doc_values", field.get("data-value")
		)
	else:
		if docname:
			value = "{}.{} or ''".format(docname, field.get("data-value"))
		else:
			value = "{} or ''".format(field.get("data-value"))

		if field["data-function"] != "null":
			value = "{}({})".format(field.get("data-function"), value)

	return value


def get_jinja_hooks():
	"""Returns a tuple of (methods, filters) each containing a dict of method name and method definition pair."""

	import frappe

	if not getattr(frappe.local, "site", None):
		return (None, None)

	from inspect import getmembers, isfunction
	from types import FunctionType, ModuleType

	def get_obj_dict_from_paths(object_paths):
		out = {}
		for obj_path in object_paths:
			try:
				obj = frappe.get_module(obj_path)
			except ModuleNotFoundError:
				obj = frappe.get_attr(obj_path)

			if isinstance(obj, ModuleType):
				functions = getmembers(obj, isfunction)
				for function_name, function in functions:
					out[function_name] = function
			elif isinstance(obj, FunctionType):
				function_name = obj.__name__
				out[function_name] = obj
		return out

	values = frappe.get_hooks("jinja")
	methods, filters = values.get("methods", []), values.get("filters", [])

	method_dict = get_obj_dict_from_paths(methods)
	filter_dict = get_obj_dict_from_paths(filters)

	return method_dict, filter_dict
