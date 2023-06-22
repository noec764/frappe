import re

import frappe
from frappe.desk.doctype.number_card.number_card import get_percentage_difference, get_result
from frappe.utils.block_editor.block_editor_render import prerender_with_template
from frappe.utils.data import get_url


def indicator_pill_round(rgb_color: str, icon_name: str):
	return f"""<span style="display:inline-block;padding:2px;border-radius:99px;background-color:rgba({rgb_color},0.2)">
		{icon(icon_name, rgb_color=rgb_color)}
	</span>&nbsp;"""


def icon(name, rgb_color="0,0,0", size="xs"):
	if name == "arrow-up-right":
		return f"""<svg viewBox="0 0 12 12" width=10 height=10 fill="none" stroke="rgb({rgb_color})" xmlns="http://www.w3.org/2000/svg">
			<path d="M2.5 9.5L9.5 2.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
			<path d="M9.5 8V2.5H4" stroke-linecap="round" stroke-linejoin="round"/>
		</svg>"""
	elif name == "arrow-down-right":
		return f"""<svg viewBox="0 0 12 12" width=10 height=10 fill="none" stroke="rgb({rgb_color})" xmlns="http://www.w3.org/2000/svg">
			<path d="M2.5 2.5L9.5 9.5" stroke-miterlimit="10" stroke-linecap="round" stroke-linejoin="round"/>
			<path d="M4 9.5h5.5v-5.5" stroke-linecap="round" stroke-linejoin="round"/>
		</svg>"""

	icon_sizes = {
		"xs": "12px",
		"sm": "16px",
		"base": "20px",
		"md": "20px",
		"lg": "24px",
		"xl": "75px",
	}
	svg_size = f"width={icon_sizes[size]} height={icon_sizes[size]}"
	icons_svg = get_url("/assets/frappe/icons/timeless/icons.svg")
	return f"""<svg class="icon icon-{size}" {svg_size} stroke="rgb({rgb_color})">
		<use href="{icons_svg}#icon-{name}"></use>
	</svg>"""


def make_error(error: str, block: dict, doc=None):
	return (
		"details",
		[
			("summary", "Error: " + error),
			("pre", [(":text", frappe.as_json(block, indent=2))]),
			("pre", [(":text", frappe.as_json(doc, indent=2))]),
		],
	)


class UnsupportedFilter(Exception):
	pass


dynamic_filter_evaluators = [
	{
		"match": re.compile(r'^frappe\.defaults\.get_user_default\("(.*)"\)$'),
		"eval": lambda m: frappe.defaults.get_user_default(m.group(1)),
	},
	{
		"match": re.compile(r"^frappe\.session\.(.*)$"),
		"eval": lambda m: frappe.session.get(m.group(1)),
	},
]


def resolve_dynamic_filter(dynamic_filter: list, context: dict):
	if not isinstance(dynamic_filter, list) or len(dynamic_filter) != 4:
		raise UnsupportedFilter("Dynamic filter not supported")

	doctype, fieldname, operator, value = dynamic_filter
	for f in dynamic_filter_evaluators:
		if m := f["match"].match(value):
			value = f["eval"](m)
			break
	else:
		raise UnsupportedFilter("Dynamic filter not supported")
	return [doctype, fieldname, operator, value]


def evaluate_dynamic_filters(filters: list, context: dict):
	if not filters:
		return []
	if not isinstance(filters, list):
		raise UnsupportedFilter("Dynamic filters not supported")

	filters = list(map(lambda f: resolve_dynamic_filter(f, context), filters))
	return filters


def render(block: dict, context: dict):
	doctype = "Number Card"
	docname = block.get("data", {}).get("number_card_name", "")
	if not docname:
		return make_error("No number card name specified", block)

	doc = frappe.get_doc(doctype, docname)
	try:
		dyn_filters = frappe.parse_json(doc.dynamic_filters_json)
		dyn_filters = evaluate_dynamic_filters(dyn_filters, context=context)
	except UnsupportedFilter as e:
		return make_error(e.args[0], block, dyn_filters)

	filters = frappe.parse_json(doc.filters_json) + dyn_filters
	result = get_result(doc, filters=filters)
	evolution = get_percentage_difference(doc, filters=filters, result=result)

	df = None
	if doc.document_type and doc.aggregate_function_based_on:
		df = frappe.get_meta(doc.document_type).get_field(doc.aggregate_function_based_on)

	formatted_number = frappe.format_value(result, df=df)

	if not evolution:
		caret_html = ""
		caret_color = "100,100,100"
	elif evolution > 0:
		caret_color = "47,157,88"
		caret_html = indicator_pill_round(caret_color, "arrow-up-right")
	else:
		caret_color = "226,76,76"
		caret_html = indicator_pill_round(caret_color, "arrow-down-right")

	stats_qualifier = None
	if evolution is not None:
		stats_qualifier_map = {
			"Daily": frappe._("since previous day"),
			"Weekly": frappe._("since previous week"),
			"Monthly": frappe._("since previous month"),
			"Yearly": frappe._("since previous year"),
		}
		stats_qualifier = stats_qualifier_map.get(doc.stats_time_interval, "")
		evolution = f"{evolution:.2f}"

	template_path = __file__.replace(".py", ".jinja")
	return prerender_with_template(
		block,
		template_path=template_path,
		context={
			"result": result,
			"evolution": evolution,
			"formatted_number": formatted_number,
			"stats_qualifier": stats_qualifier,
			"color": doc.color or "#000000",
			"caret_color": caret_color,
			"caret_html": caret_html,
			"label": frappe._(doc.label or doc.name),
		},
	)
