// Copyright (c) 2021, Dokos SAS and Contributors
// License: See license.txt

/**
 * @typedef {Object} SlideViewerOptions
 * @property {string} route - The Slide View route name. Required.
 * @property {string} [docname] - The document to edit using this Slide View. Optional.
 * @property {string} [starting_slide] - The slide to show first.
 * @property {(self: SlidesViewer) => any} [additional_settings] - A function returning additional settings for the Slides instance
 * @property {Function} [SlideClass]
 * @property {Function} [SlidesClass]
 */

/**
 * @typedef {Object} SlidesView
 * @property {string} title
 * @property {string} reference_doctype
 * @property {string} route
 * @property {string} naming_series
 * @property {boolean} allow_back
 * @property {boolean} allow_any
 * @property {boolean} done_state
 * @property {boolean} can_edit_doc
 * @property {boolean} can_create_doc
 * @property {any[]} slides
 */

class SlideViewer {
	SlideClass = frappe.ui.Slide
	SlidesClass = frappe.ui.Slides

	/** @type {SlidesView} */
	slideView = null

	route = null
	starting_slide = 0
	documentName = null
	additional_settings = null
	doc = {}

	/** @type {frappe.ui.Slides} */
	slidesInstance = null

	/**
	 * @param {SlideViewerOptions} options
	 */
	constructor(options) {
		if (!options.route) { return frappe.throw('[Slide Viewer] missing param: route') } // @todo
		this.route = options.route

		if (options.docname) { this.documentName = options.docname }
		if (options.starting_slide) { this.starting_slide = options.starting_slide }
		if (options.additional_settings) { this.additional_settings = options.additional_settings }
		if (options.SlideClass) { this.SlideClass = options.SlideClass }
		if (options.SlidesClass) { this.SlidesClass = options.SlidesClass }
	}

	/**
	 * Fetch required data from server
	 */
	async _fetch() {
		await this._fetchView()

		const { reference_doctype, can_create_doc, can_edit_doc } = this.slideView

		await SlideViewer.getTranslations(reference_doctype)

		if (reference_doctype) { // @todo
			if (this.documentName) {
				if (can_edit_doc) {
					// edit mode / duplicate mode
					await this._fetchDocByName(this.documentName)
				} else {
					// frappe.show_alert({ message: __("Cannot edit this document."), indicator: 'red' })
					return frappe.throw('[Slide Viewer] cannot edit document with this Slide View') // @todo
				}
			} else {
				// create mode
				if (!can_create_doc) {
					return frappe.throw('[Slide Viewer] cannot create document with this Slide View') // @todo
				}
			}
		} else {
			// @todo check for slides
			return frappe.throw('[Slide Viewer] cannot edit document with a Slide View without reference_doctype')
		}
	}

	async _fetchView() {
		this.slideView = await SlideViewer.getSlideViewByRoute(this.route)
		if (!this.slideView) { return frappe.throw('[Slide Viewer] missing Slide View') } // @todo
	}

	async _fetchDocByName(docname) {
		const { reference_doctype } = this.slideView

		this.doc = {
			doctype: reference_doctype,
			name: docname,
		}
		this.doc = await this.get_doc()

		if (!this.doc) { // @todo
			return frappe.throw('[Slide Viewer] no such document')
		}
	}

	/**
	 * Renders the Slide Viewer in the given container
	 * @param {HTMLElement} wrapper
	 */
	async renderInWrapper(wrapper) {
		this.wrapper = wrapper

		await this._fetch()

		frappe.utils.set_title(__(this.slideView.title))

		// make the Slides instance with optional values to populate the form.
		const slidesSettings = await this.getSlidesSettings()
		if (slidesSettings) {
			this.slidesInstance = new (this.SlidesClass)(slidesSettings)
		} else {
			frappe.msgprint('Aucune diapositive à affficher') // @todo
		}
	}

	async get_doc() {
		if (this.doc) {
			const { doctype, name } = this.doc
			this.doc = await frappe.xcall('frappe.client.get', { doctype, name });
			return this.doc;
		}
	}

	async save_doc_and_open_form() {
		const { doctype, name } = await this.save_doc()
		frappe.set_route('Form', doctype, name);
	}

	async save_doc() {
		const values = this.slidesInstance.get_values()
		Object.assign(this.doc, values)
		this.doc = await frappe.xcall('frappe.client.save', { doc: this.doc })
		return this.doc
	}

	// async submit_doc() {
	// 	const values = this.slidesInstance.get_values()
	// 	Object.assign(this.doc, values)
	// 	this.doc = await frappe.xcall('frappe.client.submit', { doc: this.doc })
	// 	frappe.set_route("Form", this.doc.doctype, this.doc.name)
	// }

	async getSlidesSettings() {
		const allSlides = await this.getSlides();
		if (!allSlides || allSlides.length === 0) { return null }

		/** @type {ConstructorParameters<typeof frappe.ui.Slides>[0]} */
		const slidesViewer = this
		const baseSettings = {
			slidesViewer: this,
			slide_class: this.SlideClass,

			parent: this.wrapper,
			slides: allSlides,
			initial_values: this.getValuesFromDoc(),
			starting_slide: this.starting_slide,
			unidirectional: !this.slideView.allow_back,
			clickable_progress_dots: this.slideView.allow_any && this.slideView.allow_back,
			done_state: this.slideView.done_state,

			on_complete() {
				const hasErrors = this.has_errors()
				if (!hasErrors) {
					slidesViewer.save_doc_and_open_form();
				}
			},
		}

		if (this.additional_settings) {
			Object.assign(baseSettings, this.additional_settings(this))
		}

		return baseSettings
	}

	async getSlides() {
		let allSlides = [];

		const ref_doctype = this.slideView.reference_doctype;
		const shouldGenerateAutoSlides = this.slideView.slides.length === 0;
		if (shouldGenerateAutoSlides) {
			if (ref_doctype) {
				allSlides = await getAutoslidesForDocType(ref_doctype, this.documentName);
			} else {
				// cannot generate auto slides without doctype
			}
		} else {
			// slides = await create_slides_for_slides_view(slideView)
			// slides = await getSetupWizardSlides(slideView)
		}

		return allSlides;
	}

	getValuesFromDoc() {
		const values = {};
		if (this.doc) {
			const { creation, modified, modified_by, owner, ...rest } = this.doc;
			Object.assign(values, rest);
			if (typeof values.naming_series === 'string') {
				values.naming_series = values.naming_series.replace(/#+/g, '');
			}
		}
		return values;
	}

	// utils
	static getParamsFromRouter() {
		let slidesViewRoute = null
		let docname = null
		let starting_slide = null

		const route = frappe.router.get_sub_path_string().split('/')
		if (route[0] === "slide-viewer") {
			if (route.length >= 2) {
				slidesViewRoute = decodeURIComponent(route[1])
			}
			if (route.length >= 3) {
				docname = decodeURIComponent(route[2])
			}
			if (route.length >= 4) {
				starting_slide = cint(route[3])
			}
		}

		return {
			route: slidesViewRoute,
			docname: docname,
			starting_slide: starting_slide,
		}
	}

	static getTranslations(doctype) {
		return frappe.xcall('frappe.custom.page.slide_viewer.api.get_translations', { doctype })
	}

	static getSlideViewByRoute(route) {
		return frappe.xcall('frappe.custom.page.slide_viewer.api.get_slide_view', { route })
	}

	static async getFieldsForDocType(doctype) {
		await new Promise((cb) => frappe.model.with_doctype(doctype, cb))
		const meta = frappe.get_meta(doctype)
		return meta.fields
	}
}

frappe.pages['slide-viewer'].on_page_show = async function(wrapper) {
	wrapper.innerHTML = ''
	// const page = frappe.ui.make_app_page({
	// 	parent: wrapper,
	// 	single_column: false,
	// })
	frappe.utils.set_title(__("Slide Viewer")) // initial title

	const { route, docname, starting_slide } = SlideViewer.getParamsFromRouter()

	let $fullPageEditBtn = null

	const slidesViewer = new SlideViewer({
		route,
		docname,
		starting_slide,
		additional_settings: (self) => ({
			before_load: (/** @type {frappe.ui.Slides} */ slides) => {
				slides.$container.css({ width: '800px', maxWidth: '800px' })

				const ref_doctype = self.slideView.reference_doctype
				if (ref_doctype) {
					$fullPageEditBtn = $(`
						<button class="btn btn-secondary btn-sm">
							<svg class="icon icon-xs" style="">
								<use class="" href="#icon-edit"></use>
							</svg>
							${__("Edit in full page")}
						</button>
					`);
					$fullPageEditBtn.appendTo(slides.$footer.find('.text-left'));
					$fullPageEditBtn.on('click', () => {
						// @todo
						// see open_doc() in frappe/public/js/frappe/form/quick_entry.js
						// see fetch_and_render() in frappe/public/js/frappe/views/formview.js
						if (self.doc && self.doc.doctype && self.doc.name) {
							self.save_doc_and_open_form()
						} else {
							frappe.set_route('Form', ref_doctype, 'new');
						}
					});
				}
			},
			before_show_slide(id) {
				if (id === 0) {
					$fullPageEditBtn?.show()
				} else {
					$fullPageEditBtn?.hide()
				}
			},
		}),
	})

	// const dialog = new frappe.ui.Dialog()
	// dialog.show()
	// await slidesViewer.renderInWrapper(dialog.$body)

	// await slidesViewer.renderInWrapper(page.body)
	const container = $('<div style="padding: 2rem 1rem">').appendTo(wrapper)
	await slidesViewer.renderInWrapper(container)
}

async function getAutoslidesForDocType(doctype, docname = '') {
	const fields = await SlideViewer.getFieldsForDocType(doctype)
	const slides = []

	let globalTitle = ''
	if (docname) {
		globalTitle = __("Edit {0}", [docname])
	} else {
		globalTitle = __("New {0}", [__(doctype)])
	}

	if (slides.length === 0) {
		slides.push(newEmptySlide())
	}

	const filteredOutFieldTypes = [
		...frappe.model.layout_fields,
		...frappe.model.table_fields, // @todo: find out why User/HTML Table is buggy
	]
	for (const field of fields) {
		let slide = slides[slides.length - 1]

		const createNewSlide = [
			slide == null,
			// slide && slide.fields.length >= 4,
			field.fieldtype === 'Section Break',
			// field.fieldtype === 'Column Break',
		].some(x => x == true) // at least one condition

		if (createNewSlide) {
			let newSlideSubtitle = '???'
			if (field.fieldtype === 'Section Break') {
				newSlideSubtitle = __(field.label)
			} else {
				newSlideSubtitle = /*old slide*/slide.subtitle
			}
			slide = newEmptySlide(newSlideSubtitle)
			slides.push(slide)
		}

		const ignoreThisField = filteredOutFieldTypes.includes(field.fieldtype)
		if (!ignoreThisField) {
			slide.fields.push({
				...field,
				label: __(field.label), // translate label
			})
		}
	}

	return slides.filter(s => s.fields.length > 0)

	function newEmptySlide(translatedSubtitle = undefined) {
		return {
			name: 'autoslide_' + slides.length,
			title: globalTitle,
			subtitle: translatedSubtitle,
			icon: "fa fa-flag",
			fields: [],
		}
	}
}
