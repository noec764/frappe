import frappe
from frappe.model.meta import get_table_columns
from frappe.model.utils.rename_field import rename_field


def execute():
	if frappe.db.exists("DocType", "Incoming Webhook URL"):
		return

	frappe.rename_doc("DocType", "Slack Webhook URL", "Incoming Webhook URL")
	frappe.reload_doctype("Incoming Webhook URL", force=True)

	for doc in frappe.get_all("Incoming Webhook URL"):
		frappe.db.set_value("Incoming Webhook URL", doc.name, "service", "Slack")

	frappe.reload_doc("email", "doctype", "Notification")

	if "slack_webhook_url" in get_table_columns("Notification"):
		rename_field("Notification", "slack_webhook_url", "incoming_webhook_url")

	frappe.db.commit()

	for notification in frappe.get_all(
		"Notification", filters={"channel": "Slack"}, fields=["name", "slack_webhook_url"]
	):
		frappe.db.set_value("Notification", notification.name, "channel", "External Collaboration Tool")
