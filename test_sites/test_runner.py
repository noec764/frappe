import frappe

from frappe.commands.utils import run_tests
from frappe.commands import get_site

def main():
	site = get_site('test_site')
	frappe.init(site=site)

	frappe.test_runner.main('frappe', verbose=True)

	exit(0)

if __name__ == "__main__":
	main()