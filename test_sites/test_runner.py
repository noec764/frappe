import frappe
import frappe.test_runner

from frappe.commands.utils import run_tests
from frappe.commands import get_site

def main():
	frappe.init(site='test_site', sites_path="sites")

	frappe.test_runner.main('frappe', verbose=True)

	exit(0)

if __name__ == "__main__":
	main()