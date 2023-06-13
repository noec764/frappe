from frappe.tests.utils import FrappeTestCase
from frappe.utils.block_editor.block_editor_render import block_editor_json_to_html


class TestBlockEditor(FrappeTestCase):
	def check(self, json: str | dict, right: str, context=None):
		left = block_editor_json_to_html(json, context=context, pretty_print=False, wrap=False)

		left = left.replace("\n", "").replace("\t", "")
		right = right.replace("\n", "").replace("\t", "")
		self.assertEqual(left, right)

	# def test_empty(self):
	# 	self.assertEqual(block_editor_json_to_html([], wrap=False), "")

	def test_empty(self):
		self.check([], "")

	def test_paragraph(self):
		self.check(
			[{"type": "paragraph", "data": {"text": "Hello World"}}],
			"<p>Hello World</p>",
		)

	def test_multiple_paragraphs(self):
		self.check(
			[
				{"type": "paragraph", "data": {"text": "One"}},
				{"type": "paragraph", "data": {"text": "Two"}},
				{"type": "paragraph", "data": {"text": "Three"}},
				{"type": "paragraph", "data": {"text": "Four"}},
			],
			"<p>One</p><p>Two</p><p>Three</p><p>Four</p>",
		)

	def test_alert(self):
		self.check(
			[
				{
					"type": "alert",
					"data": {
						"alert_type": "info",
						"contents": [{"type": "paragraph", "data": {"text": "Hello World"}}],
					},
				},
			],
			'<div class="alert alert-info"><p>Hello World</p></div>',
		)

	def test_jinja1(self):
		self.check(
			[{"type": "paragraph", "data": {"text": "{{ 42 }}"}}],
			"<p>42</p>",
		)

	def test_jinja2(self):
		self.check(
			[{"type": "paragraph", "data": {"text": "{{ x.y }}"}}],
			"<p>42</p>",
			context={"x": {"y": 42}},
		)
