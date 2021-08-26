// Copyright (c) 2021, Dokos SAS and Contributors
// License: See license.txt

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
 * @property {boolean} add_fullpage_edit_btn
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
	doc = null

	/** @type {frappe.ui.Slides} */
	slidesInstance = null

	/**
	 * @typedef {Object} SlideViewerOptions
	 * @property {string} route - The Slide View route name. Required.
	 * @property {string} [docname] - The document to edit using this Slide View. Optional.
	 * @property {string} [starting_slide] - The slide to show first.
	 * @property {Function} [SlideClass]
	 * @property {Function} [SlidesClass]
	 * @property {(self: SlidesViewer) => any} [additional_settings] - A function returning additional settings for the Slides instance
	 */

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
			reference_doctype && SlideViewer.fetchMetaForDocType(reference_doctype),
		])

		// check permissions
		let mode = 'Error'
		let error = ''

		if (reference_doctype) {
			const meta = frappe.get_meta(reference_doctype)
			if (meta.issingle && !this.documentName) {
				if (can_edit_doc) {
					// Single DocType
					mode = 'Edit'
					this.documentName = meta.name
				} else { error = 'cannot edit' }
			} else if (this.documentName) {
				if (can_edit_doc) { mode = 'Edit' }
				else { error = 'cannot edit' }
			} else {
				if (can_create_doc) { mode = 'Create' }
				else { error = 'cannot create' }
			}
		} else {
			// @todo not an invalid state, check for .slides and .on_complete
			return frappe.throw('[Slide Viewer] cannot edit document with a Slide View without reference_doctype')
		}

		if (mode === 'Edit') {
			// edit mode / duplicate mode
			let is403 = false
			this.doc = await frappe.model.with_doc(reference_doctype, this.documentName, (name, r) => {
				// callback is called before promise resolution
				if (r && r['403']) is403 = true;
			});

			if (this.doc) {
				// okay
			} else if (is403) {
				error = 'forbidden'
			} else {
				error = 'missing document'
			}
		}
		else if (mode === 'Create') {
			this.doc = frappe.model.get_new_doc(reference_doctype)
			if (this.doc) {
				// okay
			} else {
				error = 'frappe.model.get_new_doc returned null --> doctype meta not loaded?'
			}
		}

		if (error === 'cannot edit') {
			frappe.show_not_permitted(__("Slide View"))
			throw new Error('[Slide Viewer] cannot edit document with this Slide View')
		} else if (error === 'cannot create') {
			frappe.show_not_permitted(__("Slide View"))
			throw new Error('[Slide Viewer] cannot create document with this Slide View')
		} else if (error === 'missing document') {
			frappe.show_not_found(__(reference_doctype) + " - " + __(this.documentName));
			throw new Error('[Slide Viewer] ' + __("{0} {1} not found", [__(reference_doctype), __(this.documentName)]))
		} else if (error === 'forbidden') {
			frappe.show_not_permitted(__(reference_doctype) + " - " + __(this.documentName));
			throw new Error('[Slide Viewer] ' + __("You don't have the permissions to access this document"))
		} else if (error) {
			return frappe.throw('[Slide Viewer] an unknown error: ' + error)
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
		if (!this.doc || !this.slideView) {
			frappe.show_not_found('');
			throw new Error("[SlideViewer.renderInWrapper]: missing .doc or .slideView");
		}

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
			const msg = __("Oops, there are no slides to display.", null, "Slide View")
			const img = 'empty.svg'
			frappe.show_message_page({
				page_name: msg,
				message: msg,
				img: `/assets/frappe/images/ui/${img}`
			})
		}

	async getSlidesSettings(params) {
		const allSlides = await this.getSlides();
		if (!allSlides || allSlides.length === 0) { return null }

		const baseSettings = {
			slidesViewer: this,
			slide_class: this.SlideClass,

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

		Object.assign(baseSettings, params);

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
		const shouldGenerateAutoSlides = true;
		if (shouldGenerateAutoSlides) {
			if (ref_doctype) {
				allSlides = await getAutoslidesForDocType(ref_doctype, this.documentName);
			} else {
				// cannot generate auto slides without doctype
			}
		} else {
			// slides = await getSlidesForSlideView(slideView)
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
		return frappe.xcall('frappe.custom.page.slide_viewer.api.get_slide_view_by_route', { route })
	}

	static async fetchMetaForDocType(doctype) {
		return new Promise((cb) => frappe.model.with_doctype(doctype, cb))
	}

	static async getMetaForDocType(doctype) {
		if (!frappe.get_meta(doctype)) {
			await SlideViewer.fetchMetaForDocType(doctype)
		}
		return frappe.get_meta(doctype)
	}
}

frappe.pages['slide-viewer'].on_page_show = async function(wrapper) {
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

	const { route, docname, starting_slide } = SlideViewer.getParamsFromRouter()

	const slidesViewer = new SlideViewer({
		route,
		docname,
		starting_slide,
		SlidesClass: SlidesWithForm,
		SlideClass: SlideWithForm,

		/** @this {SlideViewer} */
		additional_settings() {
			if (this.slideView.add_fullpage_edit_btn) {
				this.SlidesClass = SlidesWithFullPageEditButton
			}

			return { text_complete_btn: __("Save") }
		},
	})

	// const dialog = new frappe.ui.Dialog({ size: 'large' })
	// dialog.show()
	// await slidesViewer.renderInDialog(dialog)

	const container = $('<div style="padding: 2rem 1rem">').appendTo(page.body)
	await slidesViewer.renderInWrapper(container)
	slidesViewer.slidesInstance.render_progress_dots()
}

async function getAutoslidesForDocType(doctype, docname = '') {
	const meta = await SlideViewer.getMetaForDocType(doctype)
	const fields = meta.fields
	const slides = []

	let globalTitle = ''
	if (meta.issingle) {
		globalTitle = __(meta.name)
	} else if (docname) {
		const href = `/app/${frappe.router.slug(doctype)}/${encodeURIComponent(docname)}`;
		const link = `<a href="${href}" onclick="frappe.set_route('${href}');event&&event.preventDefault()">${docname}</a>`
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

	return slides.filter(slide => slide.fields.length > 0)
	/* return slides.filter(slide => {
		const f = slide.fields.filter(df => {
			if (frappe.model.layout_fields.includes(df.fieldtype)) {
				return false
			}
			if (df.read_only && !df.read_only_depends_on) {
				return false
			}
			return true
		})
		return f.length > 0
	}) */

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

class SlidesWithForm extends frappe.ui.Slides {
	before_load() {
		super.before_load()
		this.$container.css({ width: '100%', maxWidth: '800px' })
	}

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

		frappe.model.on(fakeform.doctype, "*", (fieldname, value, doc) => {
			if (doc.name === fakeform.docname) {
				this.render_progress_dots();
				this.show_hide_prev_next(this.current_id);
			}
		});
	}
}

class SlideWithForm extends frappe.ui.Slide {
	set_form_values(values) { return Promise.resolve() }

	should_skip() {
		if (super.should_skip()) { return true }

		if (this.condition && this.parent_form && this.parent_form.layout) {
			const conditionValid = this.parent_form.layout.evaluate_depends_on_value(this.condition)
			if (!conditionValid) { return true }
		}

		return false
	}
}

class SlidesWithFullPageEditButton extends SlidesWithForm {
	before_load() {
		super.before_load()

		if (this.doc && this.doc.doctype && this.doc.name) {
			this.$fullPageEditBtn = $(`
				<button class="btn btn-secondary btn-edit-in-full-page">
					${frappe.utils.icon('edit', 'xs')}
					${__("Edit in full page")}
				</button>
			`);
			this.$fullPageEditBtn.appendTo(this.$footer.find('.text-left'));
			this.$fullPageEditBtn.on('click', () => {
				// @see open_doc() in frappe/public/js/frappe/form/quick_entry.js
				frappe.set_route('Form', this.doc.doctype, this.doc.name);
			});
		}
	}
	before_show_slide(id) {
		super.before_show_slide(id)

		if (this.$fullPageEditBtn) {
			if (this.can_go_prev(id)) {
				this.$fullPageEditBtn.hide()
			} else {
				this.$fullPageEditBtn.show()
			}
		}
	}
}

class FakeForm extends frappe.ui.form.Form {
	constructor(wrapper, doc, opts = {}) {
		if (!(typeof doc === 'object' && doc.doctype)) {
			frappe.throw('[Slide View/FakeForm] `doc` parameter should be an object with a `doctype` property.')
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

		// const sidebarProxy = new Proxy({}, {
		// 	get(o, k, r) {
		// 		return () => {
		// 			console.log(`%cfrm.sidebar.${k}`, 'color:pink')
		// 			return undefined
		// 		}
		// 	}
		// })
		// Object.defineProperty(this, 'sidebar', {
		// 	configurable: true,
		// 	get() { return sidebarProxy },
		// 	set(v) { },
		// })

		// this.toolbar = new Proxy({}, {
		// 	get(o, k, r) {
		// 		if (o[k]) { return o[k] }
		// 		return () => {
		// 			console.log(`%cfrm.toolbar.${k}`, 'color:pink')
		// 			return undefined
		// 		}
		// 	},
		// 	set(o, k, v) {
		// 		o[k] = v
		// 		return true
		// 	}
		// })
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
	}

	async save(...args) {
		this.fakeform_saving = true
		await super.save(...args)
		this.fakeform_saving = false
	}
	async savesubmit(...args) {
		this.fakeform_saving = true
		await super.savesubmit(...args)
		this.fakeform_saving = false
	}
	savecancel(btn, callback, on_error) {
		this.fakeform_saving = true
		super.savecancel(btn, (...args) => {
			callback&&callback(...args)
			this.fakeform_saving = false
		}, (...args) => {
			on_error&&on_error(...args)
			this.fakeform_saving = false
		})
	}
	async amend_doc() {
		this.fakeform_saving = true
		super.amend_doc()
		this.fakeform_saving = false
	}
	refresh(switched_docname) {
		if (!this.fakeform_saving) {
			// Skip the refresh during/after save to prevent the FakeForm from being reused on the real form page.
			super.refresh(switched_docname)
		}
	}
	refresh_header() { /* Prevent frappe.utils.set_title */ }
}
