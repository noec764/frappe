from __future__ import unicode_literals, absolute_import
import click, frappe, os, shutil
from frappe.commands import pass_context

@click.command('build-docs')
@pass_context
@click.option('--app', default=None, help='The target app')
@click.option('--development', is_flag=True, default=False, help='Serve the docs locally')
def build_docs(context, app=None, development=False):
	"Setup docs in target folder of target app"
	from frappe.utils.setup_docs import setup_docs
	frappe.init('')

	setup_docs(app, development)

commands = [
	build_docs
]
