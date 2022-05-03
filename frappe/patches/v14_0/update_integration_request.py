import frappe


def execute():
	doctype = "Integration Request"
	frappe.db.set_value(
		doctype,
		{
			"integration_type": ("in", ("Remote", "Webhook")),
			"integration_request_service": ("!=", "PayPal"),
		},
		"is_remote_request",
		1,
	)
	frappe.db.set_value(
		doctype,
		{"integration_type": "Webhook"},
		"request_description",
		"Subscription Notification",
	)
