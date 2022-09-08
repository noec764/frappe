import sys

import frappe
import frappe.test_runner


def main():
	args = sys.argv

	frappe.init(site="test_site", sites_path="sites")

	frappe.flags.in_ci = True
	ret = frappe.test_runner.main(args[1], verbose=True)

	if len(ret.failures) == 0 and len(ret.errors) == 0:
		ret = 0

	sys.exit(ret)


if __name__ == "__main__":
	main()
