import frappe
from frappe.desk.doctype.number_card.number_card import get_percentage_difference, get_result
from frappe.utils.block_editor.block_editor_render import prerender_with_template
from frappe.utils.data import get_url


def icon(name, size="sm"):
	icons_svg = get_url("/assets/frappe/icons/timeless/icons.svg")
	return f"""<svg class="icon icon-{size}">
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


def render(block: dict, context: dict):
	doctype = "Number Card"
	docname = block.get("data", {}).get("number_card_name", "")
	if not docname:
		return make_error("No number card name specified", block)

	doc = frappe.get_doc(doctype, docname)
	dyn_filters = frappe.parse_json(doc.dynamic_filters_json)
	if dyn_filters:
		return make_error("Dynamic filters not supported", block, dyn_filters)

	filters = doc.filters_json
	result = get_result(doc, filters=filters)
	evolution = get_percentage_difference(doc, filters=filters, result=result)

	df = None
	if doc.document_type and doc.aggregate_function_based_on:
		df = frappe.get_meta(doc.document_type).get_field(doc.aggregate_function_based_on)

	formatted_number = frappe.format_value(result, df=df)

	if not evolution:
		caret_html = ""
		color_class = "grey"
	elif evolution > 0:
		caret_html = f"""<span class="indicator-pill-round green">
			{icon("arrow-up-right", "xs")}
		</span>"""
		color_class = "green"
	else:
		caret_html = f"""<span class="indicator-pill-round red">
			{icon("down-arrow", "xs")}
		</span>"""
		color_class = "red"

	stats_qualifier = None
	if evolution is not None:
		stats_qualifier_map = {
			"Daily": frappe._("since previous day"),
			"Weekly": frappe._("since previous week"),
			"Monthly": frappe._("since previous month"),
			"Yearly": frappe._("since previous year"),
		}
		stats_qualifier = stats_qualifier_map.get(doc.stats_time_interval, "")
		evolution = f"{evolution:.1f}"

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
			"color_class": color_class,
			"caret_html": caret_html,
			"label": frappe._(doc.label or doc.name),
		},
	)
