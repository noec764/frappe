from frappe.website.page_renderers.document_page import DocumentPage
from frappe.website.router import get_page_info_from_web_form
from frappe.website.utils import get_sidebar_items


class WebFormPage(DocumentPage):
	def can_render(self):
		web_form = get_page_info_from_web_form(self.path)
		if web_form:
			self.doctype = "Web Form"
			self.docname = web_form.name
			return True
		else:
			return False

	def post_process_context(self):
		self.context.sidebar_items = get_sidebar_items(self.context.website_sidebar, self.basepath)
		super().post_process_context()
