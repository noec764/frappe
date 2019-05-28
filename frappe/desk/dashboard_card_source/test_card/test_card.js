
frappe.provide('frappe.dashboards.card_sources');

frappe.dashboards.card_sources["Test Card"] = {
	method: "frappe.desk.dashboard_card_source.test_card.test_card.get",
	color: "#6be273",
	icon: "fa fa-binoculars"
};