"""Automatically setup docs for a project

Call from command line:

	bench setup-docs app path

"""
from __future__ import unicode_literals, print_function
import frappe
import warnings
import os

from frappe.build import get_node_pacman, check_yarn

APP_PATHS = None
def setup():
	global APP_PATHS
	pymodules = []
	for app in frappe.get_all_apps(True):
		try:
			pymodules.append(frappe.get_module(app))
		except ImportError: pass
	APP_PATHS = [os.path.dirname(pymodule.__file__) for pymodule in pymodules]

def setup_docs(app, version, development=False):
	setup()

	pacman = get_node_pacman()
	mode = 'docs:dev' if development else 'docs:build'
	command = '{pacman} run {mode}'.format(pacman=pacman, mode=mode)

	frappe_app_path = os.path.abspath(os.path.join(APP_PATHS[0], '..'))
	check_yarn()
	frappe.commands.popen(command, cwd=frappe_app_path)
