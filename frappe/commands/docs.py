from __future__ import unicode_literals, absolute_import
import click, frappe, os, shutil
from frappe.commands import pass_context

@click.command('build-docs')
@pass_context
@click.argument('app')
@click.option('--version', default='current')
def build_docs(context, app, version="current"):
	"Setup docs in target folder of target app"
	from frappe.utils.setup_docs import setup_docs
	frappe.init('')

	development = frappe.local.conf.developer_mode or False
	setup_docs(app, version, development)

commands = [
	build_docs,
]
