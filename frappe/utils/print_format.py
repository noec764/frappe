from __future__ import unicode_literals

import frappe, os
from frappe import _
from frappe.utils import scrub_urls

from frappe.utils.pdf import get_pdf,cleanup
from PyPDF2 import PdfFileWriter

no_cache = 1

base_template_path = "templates/www/printview.html"
standard_format = "templates/print_formats/standard.html"

@frappe.whitelist()
def download_multi_pdf(doctype, name, format=None):
	"""
	Concatenate multiple docs as PDF .

	Returns a PDF compiled by concatenating multiple documents. The documents
	can be from a single DocType or multiple DocTypes

	Note: The design may seem a little weird, but it exists exists to
		ensure backward compatibility. The correct way to use this function is to
		pass a dict to doctype as described below

	NEW FUNCTIONALITY
	=================
	Parameters:
	doctype (dict):
		key (string): DocType name
		value (list): of strings of doc names which need to be concatenated and printed
	name (string):
		name of the pdf which is generated
	format:
		Print Format to be used

	Returns:
	PDF: A PDF generated by the concatenation of the mentioned input docs

	OLD FUNCTIONALITY - soon to be deprecated
	=========================================
	Parameters:
	doctype (string):
		name of the DocType to which the docs belong which need to be printed
	name (string or list):
		If string the name of the doc which needs to be printed
		If list the list of strings of doc names which needs to be printed
	format:
		Print Format to be used

	Returns:
	PDF: A PDF generated by the concatenation of the mentioned input docs
	"""

	import json
	output = PdfFileWriter()

	if not isinstance(doctype, dict):
		result = json.loads(name)

		# Concatenating pdf files
		for i, ss in enumerate(result):
			output = frappe.get_print(doctype, ss, format, as_pdf = True, output = output)
		frappe.local.response.filename = "{doctype}.pdf".format(doctype=doctype.replace(" ", "-").replace("/", "-"))
	else:
		for doctype_name in doctype:
			for doc_name in doctype[doctype_name]:
				try:
					output = frappe.get_print(doctype_name, doc_name, format, as_pdf = True, output = output)
				except Exception:
					frappe.log_error("Permission Error on doc {} of doctype {}".format(doc_name, doctype_name))
		frappe.local.response.filename = "{}.pdf".format(name)

	frappe.local.response.filecontent = read_multi_pdf(output)
	frappe.local.response.type = "download"

def read_multi_pdf(output):
	# Get the content of the merged pdf files
	fname = os.path.join("/tmp", "frappe-pdf-{0}.pdf".format(frappe.generate_hash()))
	output.write(open(fname,"wb"))

	with open(fname, "rb") as fileobj:
		filedata = fileobj.read()

	return filedata

@frappe.whitelist()
def download_pdf(doctype, name, format=None, doc=None, no_letterhead=0):
	html = frappe.get_print(doctype, name, format, doc=doc, no_letterhead=no_letterhead)
	frappe.local.response.filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
	frappe.local.response.filecontent = get_pdf(html)
	frappe.local.response.type = "pdf"

@frappe.whitelist()
def report_to_pdf(html, orientation="Landscape"):
	frappe.local.response.filename = "report.pdf"
	frappe.local.response.filecontent = get_pdf(html, {"orientation": orientation})
	frappe.local.response.type = "pdf"

@frappe.whitelist()
def letter_to_pdf(html, title, letterhead=None, attach=False, doctype=None, docname=None):
	html = get_formatted_letter(title, html, letterhead)
	pdf = get_pdf(html)

	if attach:
		try:
			private_files = frappe.get_site_path('private', 'files')
			fname = os.path.join(private_files, "{0}-{1}.pdf".format(title, frappe.generate_hash(length=6)))
			with open(fname, "wb") as f:
				f.write(pdf)

			new_file = frappe.get_doc({
				"doctype": "File",
				"file_name": title,
				"attached_to_doctype": doctype,
				"attached_to_name": docname,
				"file_url": "/private/files/" + fname.split('/private/files/')[1]
			})
			new_file.insert()
		except Exception:
			frappe.log_error("Letter error", frappe.get_traceback())

	frappe.local.response.filename = "{0}.pdf".format(title.replace(" ", "-").replace("/", "-"))
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"

def get_formatted_letter(title, message, letterhead=None):
	no_letterhead = True

	if letterhead:
		letter_head = frappe.db.get_value("Letter Head", letterhead, "content")
		no_letterhead = False

	rendered_letter = frappe.get_template("templates/letters/standard.html").render({
		"content": message,
		"title": title,
		"letter_head": letter_head,
		"no_letterhead": no_letterhead
	})

	html = scrub_urls(rendered_letter)

	return html


@frappe.whitelist()
def print_by_server(doctype, name, print_format=None, doc=None, no_letterhead=0):
	print_settings = frappe.get_doc("Print Settings")
	try:
		import cups
	except ImportError:
		frappe.throw("You need to install pycups to use this feature!")
		return
	try:
		cups.setServer(print_settings.server_ip)
		cups.setPort(print_settings.port)
		conn = cups.Connection()
		output = PdfFileWriter()
		output = frappe.get_print(doctype, name, print_format, doc=doc, no_letterhead=no_letterhead, as_pdf = True, output = output)
		file = os.path.join("/", "tmp", "frappe-pdf-{0}.pdf".format(frappe.generate_hash()))
		output.write(open(file,"wb"))
		conn.printFile(print_settings.printer_name,file , name, {})
	except IOError as e:
		if ("ContentNotFoundError" in e.message
			or "ContentOperationNotPermittedError" in e.message
			or "UnknownContentError" in e.message
			or "RemoteHostClosedError" in e.message):
			frappe.throw(_("PDF generation failed"))
	except cups.IPPError:
		frappe.throw(_("Printing failed"))
	finally:
		cleanup(file,{})
