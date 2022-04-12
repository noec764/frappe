import sys

import frappe
import frappe.test_runner


def main():
	frappe.init(site="test_site", sites_path="sites")

	frappe.flags.in_ci = True
	ret = frappe.test_runner.main("frappe", verbose=True)

	if len(ret.failures) == 0 and len(ret.errors) == 0:
		ret = 0

	sys.exit(ret)


if __name__ == "__main__":
	main()
