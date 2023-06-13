import os
from typing import Callable, Iterable, Literal

from bs4 import BeautifulSoup, Tag

import frappe
from frappe.utils.block_editor.block_editor_jinja_utils import make_base_context


class block_t:
	id: str
	type: str
	data: dict


prerender_t = (
	tuple[Literal[":html"], str]
	| tuple[Literal[":text"], str]
	| tuple[str, Iterable["prerender_t"] | None, dict | None]
)


class BlockEditorRenderError(frappe.ValidationError):
	pass


def prepare_data(json: str | dict | list) -> list[block_t]:
	data = json
	blocks = []

	if isinstance(data, str):
		if not data:
			return []

		try:
			data = frappe.parse_json(data)
		except ValueError:
			return []

	if isinstance(data, dict):
		data = data.get("blocks", [])

	if isinstance(data, list):
		blocks = data
	else:
		raise BlockEditorRenderError(f"Invalid value for content: {repr(json)}")

	return blocks


def get_tool_for_type(typ: str, context: dict) -> Callable | str | None:
	if not typ or not isinstance(typ, str) or not typ.isidentifier():
		raise BlockEditorRenderError(f"Invalid type '{typ}'")

	if typ == "numberCard":
		from .templates.numberCard import render

		return render

	builtin_templates = [
		"alert",
		"card",
		"columns",
		"delimiter",
		"header",
		"image",
		"list",
		"paragraph",
		"raw",
		"spacer",
		"table",
	]
	if typ in builtin_templates:
		return typ

	return None


def recursive_prerender(block: dict, context: dict) -> prerender_t:
	typ = block.get("type")
	tool = get_tool_for_type(typ, context)

	if not tool:
		raise BlockEditorRenderError(f"No tool found for type '{typ}'")

	if callable(tool):
		return tool(block=block, context=context)
	elif isinstance(tool, str):
		return prerender_with_template(block, context=context)
	else:
		raise BlockEditorRenderError(f"Invalid tool '{repr(tool)}' for type '{typ}'")


# @lru_cache
def _get_cached_template(template_path: str) -> str:
	if not os.path.exists(template_path):
		e1 = BlockEditorRenderError(f"No such template '{template_path}'.")
		e2 = FileNotFoundError(template_path)
		raise e1 from e2

	with open(template_path) as f:
		return f.read()


def prerender_with_template(
	block: dict, template_path: str | None = None, context: dict | None = None
) -> prerender_t:
	from .block_editor_jinja_utils import make_context

	if not template_path:
		template_path = os.path.join(
			os.path.dirname(__file__), "templates", block.get("type") + ".jinja"
		)

	template = _get_cached_template(template_path)

	current_context = make_context(block=block, context=context)
	html = frappe.render_template(template, context=current_context, is_path=False, safe_render=True)
	return ":html", html


def append_to_node(dom: BeautifulSoup, parent: Tag, tup: prerender_t) -> None:
	"""Append a prerender tuple to a BeautifulSoup node.

	Args:
	        parent (BeautifulSoup): parent node
	        tup (prerender_t): prerender tuple
	"""

	if isinstance(tup, str):
		try:
			parent.append(tup)
		except TypeError:
			raise BlockEditorRenderError(f"Invalid value tup={repr(tup)} for prerender tuple.")
		return

	tag = tup[0]
	contents = tup[1] if len(tup) > 1 else None

	if tag == ":html":
		if contents:
			try:
				parent.append(BeautifulSoup(contents, "html.parser"))
			except TypeError:
				raise BlockEditorRenderError(f"Invalid value :html innerHTML={repr(contents)} for prerender.")
		return

	if tag == ":text":
		if contents:
			try:
				parent.append(contents)
			except TypeError:
				raise BlockEditorRenderError(f"Invalid value contents={repr(contents)} for prerender.")
		return

	attributes = tup[2] if len(tup) > 2 else None
	attributes = {**attributes} if attributes else {}
	innerHTML = str(attributes.pop("__html", ""))  # additional innerHTML

	if isinstance(contents, str):
		innerHTML += contents
		contents = None

	node: Tag = dom.new_tag(tag, **attributes)
	parent.append(node)

	if innerHTML:
		try:
			node.append(BeautifulSoup(innerHTML, "html.parser"))
		except TypeError:
			raise BlockEditorRenderError(f"Invalid value innerHTML={repr(innerHTML)} for prerender.")

	if contents and isinstance(contents, list):
		for child in contents:
			append_to_node(dom, node, child)


def block_editor_json_to_html(
	json: str | dict | list, context: dict = None, pretty_print=False, wrap=True
):
	if not json:
		return ""

	if isinstance(json, str) and not json.startswith("{"):
		return json

	blocks = prepare_data(json)
	dom = BeautifulSoup()
	root = dom

	for block in blocks:
		tup = recursive_prerender(block=block, context=context)
		append_to_node(dom, root, tup)

	html = dom.decode(pretty_print=pretty_print)

	if wrap:
		# Wrap in card
		html = f"""
		<table class="dodock-block-editor--readonly" role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" height="100%"><tr height="60px"></tr><tr><td></td><td bgcolor="#ffffff" width="600" style="word-wrap:break-word;max-width:600px;border-radius:7px;box-shadow:0 5px 15px rgba(0,0,0,.05),0 0 5px rgba(0,0,0,.05); padding: 1em;">{html}</td><td></td></tr><tr height="60px"></tr><tr height="100%"></tr></table>
		<style>html{{background:#fcfcfc}}</style>
		""".strip()

	return html


# @frappe.whitelist(xss_safe=True)
def render(json: str | dict | list, context: dict = None):
	html = block_editor_json_to_html(json, context=context, wrap=True)

	# Return as web page if requested
	if frappe.get_request_header("Accept", "").find("text/html") >= 0:
		from frappe.email.email_body import get_formatted_html

		html = get_formatted_html(subject="", message=html)
		return frappe.respond_as_web_page("", "", template="html-only", context={"html": html})

	return html


@frappe.whitelist(xss_safe=True)
def preview_with_random_document(json: str, doctype: str):
	frappe.only_for("System Manager")

	if "text/html" not in frappe.get_request_header("Accept", ""):
		return "expected text/html in Accept header"

	ctx = {}
	try:
		doc = frappe.get_doc(doctype, {})
	except frappe.DoesNotExistError:
		doc = frappe.new_doc(doctype)
	ctx["doc"] = doc

	return render(json, context=ctx)
