# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


def execute():
	from frappe.installer import remove_from_installed_apps
	remove_from_installed_apps("shopping_cart")
