// Copyright (c) 2021, Dokos SAS and Contributors
// License: See license.txt

frappe.provide('frappe.ui')

frappe.pages['slide-viewer'].on_page_show = async function(/** @type {HTMLElement} */ wrapper) {
	if (!wrapper.loaded) {
		wrapper.loaded = true
		$(wrapper).on('hide', () => {
			if (wrapper.slideViewer) {
				wrapper.slideViewer.hide()
			}
		})
	}

	if (wrapper.slideViewer) {
		const svr = wrapper.slideViewer
		const sv = svr.slideView

		if (sv) {
			// const slide_viewer_form = svr.slidesInstance && svr.slidesInstance.parent_form
			// const doc = slide_viewer_form ? slide_viewer_form.doc : svr.doc
			const r = frappe.ui.SlideViewer.getParamsFromRouter()

			const slide_view_in_locals = frappe.get_doc('Slide View', sv.name)
			const slide_view_changed = slide_view_in_locals && (sv !== slide_view_in_locals)

			const document_in_locals = svr.documentName && frappe.get_doc(sv.reference_doctype, svr.documentName)
			const docname_changed = r.docname && (r.docname !== svr.documentName)
			const route_changed = r.route !== svr.route

			if (slide_view_changed || route_changed || docname_changed || !document_in_locals) {
				svr.hide()
				delete wrapper.slideViewer // re-render
			} else {
				svr.show()
				return; // don't render again
			}
		} else {
			delete wrapper.slideViewer // re-render
		}
	}

	wrapper.innerHTML = ''
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		single_column: true,
	})
	page.wrapper.children('.page-head').hide()
	page.sidebar.hide()
	page.body.empty()
	cur_page = page

	frappe.utils.set_title(__("Slide View")) // initial title

	const { route, docname, starting_slide } = frappe.ui.SlideViewer.getParamsFromRouter()

	const slideViewer = new frappe.ui.SlideViewer({
		route,
		docname,
		starting_slide,
		with_form: true,
	})

	const container = $('<div style="padding: 2rem 1rem">').appendTo(page.body)
	wrapper.slideViewer = slideViewer // set before render
	await slideViewer.renderInWrapper(container)
	slideViewer.slidesInstance.render_progress_dots()
}
