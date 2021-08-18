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
		await this._fetchSlideView()

		const { reference_doctype, can_create_doc, can_edit_doc } = this.slideView

		await Promise.all([
			SlideViewer.getTranslations(reference_doctype),
			SlideViewer.fetchMetaForDocType(reference_doctype),
		])

		// check permissions
		let mode = 'Error'
		let error = ''

		if (reference_doctype) {
			if (this.documentName) {
				if (can_edit_doc) {
					mode = 'Edit'
				} else {
					error = 'cannot edit'
				}
			} else {
				if (can_create_doc) {
					mode = 'Create'
				} else {
					error = 'cannot create'
				}
			}
		} else {
			// @todo not an invalid state, check for .slides
			return frappe.throw('[Slide Viewer] cannot edit document with a Slide View without reference_doctype')
		}

		if (mode === 'Edit') {
			// edit mode / duplicate mode
			this.doc = await frappe.xcall('frappe.client.get', {
				doctype: reference_doctype,
				name: this.documentName,
			});

			// frappe.client.get should throw when doc is not found
			if (!this.doc) { return frappe.throw(__("{0} {1} not found", [__(reference_doctype), __(this.documentName)])) }

			frappe.provide("frappe.model.docinfo." + this.doc.doctype + "." + this.doc.name)
			frappe.model.add_to_locals(this.doc)
		}
		else if (mode === 'Create') {
			this.doc = frappe.model.get_new_doc(reference_doctype)
			frappe.provide("frappe.model.docinfo." + this.doc.doctype + "." + this.doc.name)
			frappe.model.add_to_locals(this.doc)
		}
		else {
			if (error === 'cannot edit') {
				// frappe.show_alert({ message: __("Cannot edit this document."), indicator: 'red' })
				return frappe.throw('[Slide Viewer] cannot edit document with this Slide View') // @todo
			} else if (error === 'cannot create') {
				return frappe.throw('[Slide Viewer] cannot create document with this Slide View') // @todo
			} else if (error) {
				return frappe.throw('[Slide Viewer] an unknown error: ' + error)
			}
		}
	}

	async _fetchSlideView() {
		this.slideView = await SlideViewer.getSlideViewByRoute(this.route)
		this._checkSlideViewPermissions()
	}

	_checkSlideViewPermissions() {
		if (!this.slideView) {
			// @todo
			return frappe.throw('[Slide Viewer] missing Slide View')
		}

		const perms = frappe.perm.get_perm('Slide View', this.slideView.name)
		if (!perms.some(x => x.read)) {
			// @todo
			frappe.show_not_permitted(__(this.slideView.doctype) + " " + this.slideView.name);
			throw new Error('[Slide View] Insufficient Permission for Slide View: ' + this.slideView.name)
		}
	}

	/**
	 * Renders the Slide Viewer in the given container
	 * @param {HTMLElement} wrapper
	 */
	async renderInWrapper(wrapper) {
		this.wrapper = wrapper

		await this._fetch()

		if (this.documentName) {
			frappe.utils.set_title(__(this.slideView.title) + " - " + this.documentName)
		} else {
			frappe.utils.set_title(__(this.slideView.title))
		}

		// make the Slides instance with optional values to populate the form.
		const slidesSettings = await this.getSlidesSettings()
		if (slidesSettings) {
			this.slidesInstance = new (this.SlidesClass)(slidesSettings)
		} else {
			frappe.msgprint('Aucune diapositive à affficher') // @todo
		}
	}

	// async get_doc(doctype, name) {
	// 	if (this.doc && doctype === undefined && name === undefined) {
	// 		doctype = this.doc.doctype
	// 		name = this.doc.name
	// 	}
	// 	this.doc = await frappe.xcall('frappe.client.get', { doctype, name });
	// 	return this.doc;
	// }

	// async save_doc_and_open_form() {
	// 	const { doctype, name } = await this.save_doc()
	// 	frappe.set_route('Form', doctype, name);
	// }

	// async save_doc() {
	// 	const values = this.slidesInstance.get_values()
	// 	Object.assign(this.doc, values)
	// 	this.doc = await frappe.xcall('frappe.client.save', { doc: this.doc })
	// 	return this.doc
	// }

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
			initial_values: this.doc,
			starting_slide: this.starting_slide,
			unidirectional: !this.slideView.allow_back,
			clickable_progress_dots: this.slideView.allow_any && this.slideView.allow_back,
			done_state: this.slideView.done_state,

			on_complete() {
				cur_frm.save(undefined, undefined, this.$complete_btn, undefined)
			},
		}

		if (this.additional_settings) {
			if (typeof this.additional_settings === 'function') {
				Object.assign(baseSettings, this.additional_settings(this))
			} else {
				Object.assign(baseSettings, this.additional_settings)
			}
		}

		return baseSettings
	}

	async getSlides() {
		let allSlides = [];

		const ref_doctype = this.slideView.reference_doctype;
		const shouldGenerateAutoSlides = (!this.slideView.slides) || this.slideView.slides.length === 0;
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

	static async fetchMetaForDocType(doctype) {
		return new Promise((cb) => frappe.model.with_doctype(doctype, cb))
	}

	static async getFieldsForDocType(doctype) {
		if (!frappe.get_meta(doctype)) {
			await SlideViewer.fetchMetaForDocType(doctype)
		}
		const meta = frappe.get_meta(doctype)
		return meta.fields
	}
}

frappe.pages['slide-viewer'].on_page_show = async function(wrapper) {
	wrapper.innerHTML = ''
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		single_column: false,
	})
	page.wrapper.empty()
	cur_page = page

	frappe.utils.set_title(__("Slide Viewer")) // initial title

	const { route, docname, starting_slide } = SlideViewer.getParamsFromRouter()

	let $fullPageEditBtn = null

	const slidesViewer = new SlideViewer({
		route,
		docname,
		starting_slide,
		additional_settings: (self) => ({
			before_load: (/** @type {frappe.ui.Slides} */ slides) => {
				slides.$container.css({ width: '100%', maxWidth: '800px' })

				if (self.doc && self.doc.doctype) {
					$fullPageEditBtn = $(`
						<button class="btn btn-secondary btn-sm">
							${frappe.utils.icon('edit', 'xs')}
							${__("Edit in full page")}
						</button>
					`);
					$fullPageEditBtn.appendTo(slides.$footer.find('.text-left'));
					$fullPageEditBtn.on('click', () => {
						// @see open_doc() in frappe/public/js/frappe/form/quick_entry.js

						if (self.doc && self.doc.doctype) {
							// @todo FakeForm is reused on real Form page
							// @see frappe/public/js/frappe/form/form.js:247
							cur_frm.dirty() // force dirty
							cur_frm.save()
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
		const href = `/app/${frappe.router.slug(doctype)}/${encodeURIComponent(docname)}`;
		const link = `<a href="${href}">${docname}</a>`
		globalTitle = __("Edit {0}", [link])
	} else {
		globalTitle = __("New {0}", [__(doctype)])
	}

	if (slides.length === 0) {
		slides.push(newEmptySlide())
	}

	const filteredOutFieldTypes = [
		'Section Break', // ...frappe.model.layout_fields,
	]
	for (const field of fields) {
		let slide = slides[slides.length - 1]

		const createNewSlide = [
			slide == null,
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

			if (field.fieldtype === 'Section Break') {
				slide.condition = field.depends_on
			}
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
			// icon: "fa fa-flag",
			fields: [],
		}
	}
}

frappe.ui.Slides = class SlidesWithFakeForm extends frappe.ui.Slides {
	setup() {
		const fakeform = new FakeForm(cur_page.body, this.doc, { parentSlides: this })
		this.parent_form = fakeform
		cur_frm = fakeform

		fakeform.setup()

		super.setup()

		for (const s of this.slide_instances) {
			if (!s.made) { s.make() }
		}

		const all_fields = this.slide_settings.flatMap(s => s.fields)
		const fields_list = this.slide_instances.flatMap(s => s.form.fields_list)
		const fields_dict = Object.fromEntries(this.slide_instances.flatMap(s => Object.entries(s.form.fields_dict)))

		fakeform.fakeform_set_fields({
			df: all_fields,
			list: fields_list,
			dict: fields_dict,
		})

		fakeform.make()
		fakeform.refresh()
	}
}

frappe.ui.Slide = class SlideWithFakeForm extends frappe.ui.Slide {
	set_form_values(values) { return Promise.resolve() }

	should_skip() {
		if (this.condition) {
			const conditionValid = this.slidesInstance.fakeform.layout.evaluate_depends_on_value(this.condition)
			if (!conditionValid) {
				return true
			}
		}
	}
}


class FakeForm extends frappe.ui.form.Form {
	constructor(wrapper, doc, opts = {}) {
		if (!(typeof doc === 'object' && doc.doctype)) {
			frappe.throw('[Slide View/FakeForm] `doc` parameter should be an object with at least a `doctype` property.')
		}

		const doctype = doc.doctype

		const fakeparent = $('<div>')
		super(doctype, fakeparent, true, undefined)
		this.ready = false
		this.form_wrapper = wrapper

		this.page = cur_page
		this.$wrapper = $('<div>')

		this.doc = doc
		this.doctype = this.doc.doctype
		this.docname = this.doc.name

		this.events = {}
		this.meta = frappe.get_doc('DocType', this.doctype)

		this.fields = []
		this.fields_dict = {}

		Object.assign(this, opts)
	}
	fakeform_set_fields({ df, list, dict }) {
		this.fakeform_fields_df = df
		this.fields = list
		this.fields_dict = dict
		this.layout.fields = df
		this.layout.fields_list = list
		this.layout.fields_dict = dict
	}
	setup() {
		this.script_manager = new frappe.ui.form.ScriptManager({ frm: this })

		this.layout = new frappe.ui.form.Layout({
			parent: $('<div>'),
			doctype: this.doctype,
			docname: this.docname,
			doctype_layout: undefined,
			frm: this,
			with_dashboard: false,
			card_layout: false,
		})
		this.layout.wrapper = $('<div>')
		this.layout.message = $('<div>')
		this.layout.fields = this.fakeform_fields_df
		this.layout.fields_list = this.fields
		this.layout.fields_dict = this.fields_dict

		this.dashboard = new Proxy({}, {
			get(o, k, r) {
				return () => {
					// console.log(`%cfrm.dashboard.${k}`, 'color:pink')
					return undefined
				}
			}
		})

		const sidebarProxy = new Proxy({}, {
			get(o, k, r) {
				return () => {
					// console.log(`%cfrm.sidebar.${k}`, 'color:pink')
					return undefined
				}
			}
		})
		Object.defineProperty(this, 'sidebar', {
			configurable: true,
			get() { return sidebarProxy },
			set(v) { },
		})

		this.toolbar = new Proxy({}, {
			get(o, k, r) {
				if (o[k]) { return o[k] }
				return () => {
					// console.log(`%cfrm.toolbar.${k}`, 'color:pink')
					return undefined
				}
			},
			set(o, k, v) {
				o[k] = v
				return true
			}
		})
	}
	make() {
		this.layout.doc = this.doc
		this.layout.refresh_dependency();
		this.layout.attach_doc_and_docfields(true);

		this.script_manager.setup();

		this.watch_model_updates();

		this.ready = true;
		this.__defer_execute();
	}

	__defer(method, ...args) {
		if (!this.__deferred) { this.__deferred = [] }
		this.__deferred.push({ method, args })
	}
	__defer_execute() {
		if (!this.__deferred) { return }

		const n = this.__deferred.length // prevent infinite loops
		for (let i = 0; i < n; i++) {
			const { method, args } = this.__deferred[i]
			// console.log('%c:' + method, 'color:orange', args)
			this[method](...args)
		}
	}

	refresh_field(fname) {
		if (!this.ready) { return this.__defer('refresh_field', fname) }
	  super.refresh_field(fname)
	}
	set_df_property (fieldname, prop, value) {
		if (!this.ready) { return this.__defer('set_df_property', fieldname, prop, value) }
		super.set_df_property(fieldname, prop, value)
		// this.ff(fieldname)?.set_df_property?.(fieldname, prop, value);
	}
	// ff_get_form_for_field(fieldname) {
	// 	for (const s of this.parentSlides.slide_instances) {
	// 		const f = s.form && s.form.fields_dict[fieldname]
	// 		if (f) { return s.form }
	// 	}
	// 	return undefined
	// }
	// ff(fieldname) {
	// 	const form = this.ff_get_form_for_field(fieldname)
	// 	if (!form) { console.log('%cNo form for field: ' + fieldname, 'background:red;color:white') }
	// 	return form
	// }
	refresh_header() { /* Prevent frappe.utils.set_title */ }
}
