import frappe
from frappe.utils.jinja_globals import is_rtl


def estimate_df_from_jinja_code(code: str, doc: dict):
	# Split code by . and [ but keep the delimiters
	parts = split_in_parts(code)

	# Reject if there are no parts or if the first part is not doc
	if not parts or parts[0] != "doc":
		return None

	try:
		df_or_meta: dict = frappe.get_meta(doc.get("doctype"))
		for part in parts[1:]:
			if not df_or_meta:
				return None
			if part.startswith("["):
				df_or_meta = frappe.get_meta(df_or_meta.options)
			else:
				df_or_meta = df_or_meta.get_field(part)
		if df_or_meta and df_or_meta.doctype == "DocField":
			return df_or_meta
	except Exception:
		return None
	return None


def get_array_from_jinja_template(code: str, wrt_variable: str, doc: dict):
	parts = split_in_parts(code)
	if not parts or parts[0] != "doc":
		return None

	curr = doc
	for part in parts[1:]:
		if not curr:
			return None
		if part == "[" + wrt_variable + "]":
			# break here
			return curr
		else:
			curr = curr.get(part)
	return None


def is_jinja_row_template(code: str):
	return "[i]" in code.replace(" ", "")


def split_in_parts(code: str):
	if not code:
		return None

	# Reject {% %} in code
	if "{%" in code or "%}" in code:
		return None

	# Strip {{ }} from code
	code = code.replace("{{", "").replace("}}", "")

	parts = []
	part = ""
	for c in code:
		if c.isspace():
			continue
		elif c == "]":
			part += c
			parts.append(part.strip())
			part = ""
		elif c in ".[":
			if part:
				parts.append(part.strip())
			part = c if c == "[" else ""
		else:
			part += c
	if part:
		parts.append(part.strip())
	return parts


def make_formatter(context):
	def fmt(value, code: str | None = None):
		doc = context.get("doc") or None
		if isinstance(value, str) and code is None:
			code = value
			value = context.get("nested")("{{" + code + "}}")

		df = estimate_df_from_jinja_code(code, doc=doc)
		df = df or None
		return frappe.format(value, df=df, doc=doc)

	return fmt


def has_content(val):
	if not val:
		return False
	if isinstance(val, str):
		return bool(val)
	if isinstance(val, list):
		return any(has_content(v) for v in val)
	if isinstance(val, dict) and val.get("blocks") and isinstance(val.get("blocks"), list):
		return True
	if isinstance(val, dict) and val.get("type"):
		return True
	return True


styles = {
	"table": 'role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"',
	"table_colspacing": lambda hpadding: f'{styles["table"]} style="border-spacing: {hpadding} 0px; border-collapse: separate;"',
	"table_card": lambda: f'{styles["table"]} style="box-shadow: 0 0 0 2px rgba(0,0,0,.05); border-radius: 5px;"',
}


def make_columns(columns: list[dict], attrs: str):
	className = "block-editor--columns " + attrs.get("class", "")
	html = ""
	html += f'<table {attrs} class="{className}">'
	html += "<tr>"
	for column in columns:
		width = column.get("width", 100 / len(columns))
		if isinstance(width, (int, float)):
			width = f"{width}%"
		body = column.get("body", "")
		attrs = column.get("attrs", "")
		html += f'<td width="{width}" valign="top" {attrs}>{body}</td>'
	html += "</tr>"
	html += "</table>"
	return html


def make_base_context():
	return {
		"lang": frappe.local.lang,
		"layout_direction": "rtl" if is_rtl() else "ltr",
	}


def make_context(block, context=None, parent_block=None):
	from frappe.utils.block_editor.block_editor_render import block_editor_json_to_html

	full_context = {}

	def r(val):
		return block_editor_json_to_html(val, wrap=False, context=context)

	def nested(val, ctx=None):
		if isinstance(val, list):
			return r({"blocks": val})

		if isinstance(val, dict):
			if isinstance(val.get("blocks"), list):
				return r(val)
			if val.get("type"):
				return r({"blocks": [val]})

		if isinstance(val, str):
			ctx = ctx.copy() if ctx else {}
			ctx.update(full_context or {})
			return frappe.render_template(val, context=ctx, is_path=False)

		if val is None:
			return ""

		return ("?" + repr(type(val)) + repr(val)).replace("<", "&lt;")

	jinja_utils = {
		"nested": nested,
		"has_content": has_content,
		"get_array_from_jinja_template": get_array_from_jinja_template,
		"is_jinja_row_template": is_jinja_row_template,
		"fmt": make_formatter(full_context),
	}

	full_context.update(
		{
			**(context or {}),
			"_block_utils": jinja_utils,
			"parent_block": parent_block,
			"block": block.get("data", {}),
			"block_type": block.get("type"),
			"block_id": block.get("id"),
			**make_base_context(),
			**jinja_utils,
			"styles": styles,
			"_context": full_context,
		}
	)

	return full_context
