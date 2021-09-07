// Copyright (c) 2021, Dokos SAS and Contributors
// License: See license.txt

/**
 * @typedef {Object} SlideView
 * @property {string} title
 * @property {string} [reference_doctype]
 * @property {string} [route]
 * @property {any[]} [slides]
 * @property {boolean} allow_back
 * @property {boolean} allow_any
 * @property {boolean} done_state
 * @property {boolean} can_edit_doc
 * @property {boolean} can_create_doc
 * @property {boolean} add_fullpage_edit_btn
 * @property {function} [on_complete]
 */

frappe.provide('frappe.ui');

const SlideViewer = frappe.ui.SlideViewer = class SlideViewer {
	SlideClass = frappe.ui.Slide
	SlidesClass = frappe.ui.Slides

	/** @type {SlideView} */
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
	 * @property {SlideView} [slideView] - The Slide View object/document. Required if `route` not provided.
	 * @property {string} [route] - The `route` value of the Slide View to fetch. Required if `slideView` is not provided.
	 *
	 * @property {true} [with_form] - Add form-like features to the Slide Viewer. Cannot be used with `SlideClass` or `SlidesClass` options. Experimental.
	 *
	 * @property {string} [docname] - The document to edit using this Slide View. Optional.
	 * @property {string} [starting_slide] - The slide to show first.
	 * @property {Function} [SlideClass] - The class to use for each Slide. Overwritten if `with_form` is true.
	 * @property {Function} [SlidesClass] - The class to use for the Slides instance. Overwritten if `with_form` is true.
	 * @property {(self: SlideViewer) => any} [additional_settings] - A function returning additional settings for the Slides instance
	 */

	/**
	 * @param {SlideViewerOptions} options
	 */
	constructor(options) {
		if (options.route) {
			this.route = options.route
		} else if (options.slideView) {
			this.slideView = options.slideView
			const slideViewDefaults = {
				title: '',
				reference_doctype: null,
				allow_back: true,
				allow_any: true,
				done_state: false,
				can_edit_doc: true,
				can_create_doc: true,
				add_fullpage_edit_btn: false,
				slides: [],
			}
			for (const k in slideViewDefaults) {
				// if (this.slideView[k] === undefined) {
				if (!(k in this.slideView)) {
					this.slideView[k] = slideViewDefaults[k]
				}
			}
		} else {
			return frappe.throw('[Slide Viewer] constructor: should have either route or slideView param') // @todo
		}

		if (options.with_form) {
			this.with_form = true
			Object.assign(this, {
				SlidesClass: SlidesWithForm,
				SlideClass: SlideWithForm,
			})
		}

		if (options.docname) { this.documentName = options.docname }
		if (options.starting_slide) { this.starting_slide = options.starting_slide }
		if (options.additional_settings) { this.additional_settings = options.additional_settings }

		if (options.SlideClass) { this.SlideClass = options.SlideClass }
		if (options.SlidesClass) { this.SlidesClass = options.SlidesClass }
	}

	hide() {
		window.cur_slides = undefined
		this?.slidesInstance?.parent_form?.fakeform_destroy?.()
	}

	show() {
		window.cur_slides = this.slidesInstance
		this?.slidesInstance?.parent_form?.fakeform_rebuild?.()
	}

	/**
	 * Fetch required data from server
	 */
	async _fetch() {
		if (!this.slideView) {
			await this._fetchSlideView()
		}

		const { reference_doctype } = this.slideView

		if (reference_doctype) {
			await SlideViewer.fetchMetaForDocType(reference_doctype)
		}

		await this._fetchDoc()
	}

	async _fetchDoc() {
		const { reference_doctype, can_create_doc, can_edit_doc } = this.slideView

		if (!reference_doctype) {
			if (this.slideView.slides && this.slideView.on_complete) {
				this.doc = {} // okay
			} else if (this.slideView.slides) {
				console.warn('[Slide Viewer] missing slideView.on_complete function: the Slide Viewer cannot be submitted')
				this.doc = {} // kinda okay
			} else {
				frappe.throw('[Slide Viewer] cannot edit/create document with a Slide View without reference_doctype')
			}
			return
		}

		// check permissions
		let mode = 'Error'
		let error = ''
		let fetchFromLocals = false

		const meta = frappe.get_meta(reference_doctype)

		const is_new = this.documentName && this.documentName.match(/^new-.*-\d+$/)
		const in_locals = this.documentName && frappe.get_doc(reference_doctype, this.documentName)

		if (meta.issingle && !this.documentName) {
			// Single DocType
			mode = 'Edit'
			this.documentName = meta.name
		} else if (in_locals && is_new) {
			// edit if the document exists in locals and the name looks like a new name
			mode = 'Edit'
			fetchFromLocals = true
		} else if (is_new) {
			// create if the name looks like a new name but the document is not in locals
			mode = 'Create'
		} else if (this.documentName) {
			// edit if a document name was given
			mode = 'Edit'
		} else {
			mode = 'Create'
		}

		if (mode === 'Create' && !can_create_doc) {
			mode = 'Error'
			error = 'cannot create'
		}
		if (mode === 'Edit' && !can_edit_doc) {
			mode = 'Error'
			error = 'cannot edit'
		}

		if (mode === 'Edit') {
			// edit mode / duplicate mode

			if (fetchFromLocals) {
				this.doc = frappe.get_doc(reference_doctype, this.documentName)

				if (!this.doc) {
					error = 'missing document'
				}
			} else {
				let is403 = false
				this.doc = await frappe.model.with_doc(reference_doctype, this.documentName, (name, r) => {
					// callback is called before promise resolution
					if (r && r['403']) is403 = true;
				})

				if (!this.doc) {
					error = 'missing document'
				} else if (is403) {
					error = 'forbidden'
				}
			}
		}
		else if (mode === 'Create') {
			const with_mandatory_children = true
			this.doc = frappe.model.get_new_doc(reference_doctype, undefined, undefined, with_mandatory_children)
			if (this.doc) {
				// okay
				this.documentName = this.doc.name

				if (this.route) {
				// if (frappe.router.get_sub_path().startsWith('slide-viewer')) {
					let newUrl = ['slide-viewer', this.slideView.route, this.documentName]
					newUrl = frappe.router.get_route_from_arguments(newUrl)
					newUrl = frappe.router.convert_to_standard_route(newUrl)
					newUrl = frappe.router.make_url(newUrl)
					setTimeout(() => {
						frappe.router.push_state(newUrl)
					}, 0) // run after page_show event
				}
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

	update_page_title() {
		if (this.documentName) {
			frappe.utils.set_title(__(this.slideView.title) + " - " + this.documentName)
		} else {
			frappe.utils.set_title(__(this.slideView.title))
		}
	}

	/**
	 * Renders the Slide Viewer in the given container
	 * @param {HTMLElement|JQuery} wrapper
	 */
	async renderInWrapper(wrapper) {
		await this._fetch()
		if (!this.doc || !this.slideView) {
			frappe.show_not_found('');
			throw new Error("[SlideViewer.renderInWrapper]: missing .doc or .slideView");
		}

		this.update_page_title();

		// make the Slides instance with optional values to populate the form.
		const slidesSettings = await this.getSlidesSettings({
			parent: wrapper,
		});
		this._renderWithSettings(slidesSettings);
	}

	/**
	 * Renders the Slide Viewer in the given Dialog
	 * @param {frappe.ui.Dialog} dialog
	 */
	async renderInDialog(dialogOptions = { size: 'large' }) {
		const svr = this
		Object.assign(dialogOptions, { onhide: () => svr.hide() })
		const dialog = new frappe.ui.Dialog(dialogOptions)

		await this._fetch()
		if (!this.doc || !this.slideView) {
			frappe.show_not_found('');
			throw new Error("[SlideViewer.renderInDialog]: missing .doc or .slideView");
		}

		// make the Slides instance with optional values to populate the form.
		dialog.standard_actions.empty();
		$(dialog.footer).show();
		$(dialog.footer).removeClass('hide');
		dialog.doc = this.doc;
		const slidesSettings = await this.getSlidesSettings({
			parent: dialog.wrapper,
			// parent_form: dialog,
			$container: $(dialog.wrapper),
			$body: dialog.$body,
			$footer: $(dialog.standard_actions),
			$header: $(dialog.header).find('.title-section').addClass('justify-center'),
			after_load() {
				this.$slide_progress.css({ margin: '0' });
				this.$footer.find('.flex-row').addClass('row');
				// this.make_all_slides();
				// const all_fields = this.slide_settings.flatMap(s => s.fields)
				// const fields_list = this.slide_instances.flatMap(s => s.form.fields_list)
				// const fields_dict = Object.fromEntries(this.slide_instances.flatMap(s => Object.entries(s.form.fields_dict)))
				// dialog.fields = all_fields
				// dialog.fields_list = fields_list
				// dialog.fields_dict = fields_dict
			},
		});

		if (slidesSettings && !slidesSettings.on_complete) {
			slidesSettings.on_complete = function () {
				if (this.doc && this.doc.doctype) {
					frappe.call({
						method: "frappe.desk.form.save.savedocs",
						args: { doc: this.doc, action: 'Save' },
						callback: (r) => {
							const doc = r.docs ? r.docs[0] : this.doc;
							frappe.set_route("Form", doc.doctype, doc.name);
							// $(document).trigger("save", [doc]);
						},
						error: (r) => {
							console.error(r);
						},
						btn: this.$complete_btn,
						freeze_message: __('Loading'),
					})
				} else {
					console.warn('[SlideViewer Dialog] cannot save document without doctype');
				}
			}
		}

		this._renderWithSettings(slidesSettings);
		dialog.show();
	}

	_renderWithSettings(slidesSettings) {
		if (!slidesSettings) {
			this.showErrorNoSlides();
			return;
		}

		let SlidesClass = this.SlidesClass
		if (this.with_form && this.slideView.add_fullpage_edit_btn) {
			SlidesClass = extendsWithFullPageEditButton(SlidesClass)
		}
		this.slidesInstance = new SlidesClass(slidesSettings);
		this.show();
	}

	showErrorNoSlides() {
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

		const settings = {
			slideViewer: this,
			slide_class: this.SlideClass,

			slides: allSlides,
			doc: this.doc,
			starting_slide: this.starting_slide,
			unidirectional: !this.slideView.allow_back,
			unidirectional_allow_back: false,
			clickable_progress_dots: this.slideView.allow_any && this.slideView.allow_back,
			done_state: this.slideView.done_state,
			on_complete: typeof this.slideView.on_complete === 'function' ? this.slideView.on_complete : undefined,

			...params,
		}

		if (this.with_form) {
			settings.text_complete_btn = __("Save")
			settings.on_complete = function () {
				if (this.parent_form) {
					this.parent_form.save();
				}
			}
		}

		if (this.additional_settings) {
			if (typeof this.additional_settings === 'function') {
				Object.assign(settings, this.additional_settings(this))
			} else {
				Object.assign(settings, this.additional_settings)
			}
		}

		return settings
	}

	async getSlides() {
		const docname = (this.doc&&this.doc.name) || this.documentName;
		return await getSlidesForSlideView(this.slideView, docname);
	}

	// utils
	static getParamsFromRouter() {
		let slideViewRoute = null
		let docname = null
		let starting_slide = null

		const route = frappe.router.get_sub_path_string().split('/')
		if (route[0] === "slide-viewer") {
			if (route.length >= 2) {
				slideViewRoute = decodeURIComponent(route[1])
			}
			if (route.length >= 3) {
				docname = decodeURIComponent(route[2])
			}
			if (route.length >= 4) {
				starting_slide = cint(route[3])
			}
		}

		return {
			route: slideViewRoute,
			docname: docname,
			starting_slide: starting_slide,
		}
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
			// const fakeform = svr.slidesInstance && svr.slidesInstance.parent_form
			// const doc = fakeform ? fakeform.doc : svr.doc
			const r = SlideViewer.getParamsFromRouter()

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

	const { route, docname, starting_slide } = SlideViewer.getParamsFromRouter()

	const slideViewer = new SlideViewer({
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

function getAutoslidesForMeta(meta, docname = '', title = '') {
	const doctype = meta.name
	const fields = meta.fields.slice()

	const is_new = docname && docname.match(/^new-.*-\d+$/)

	if (is_new && meta.autoname && ['prompt', 'name'].includes(meta.autoname.toLowerCase())) {
		fields.unshift(getNewNameFieldForDocType(doctype))
	}

	const slides = []

	const globalTitle = title || getSlidesTitleForMeta(meta, docname);

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
	render_progress_dots(...args) {
		if (this.parent_form) {
			this.updateSlidesWithErrorFields();
		}
		super.render_progress_dots(...args);
	}

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

	updateSlidesWithErrorFields() {
		const error_docs = this.parent_form.fakeform_get_missing_fields();
		// Names of the invalid fields in the main document.
		const error_root_fieldnames = []

		for (const err of error_docs) {
			const { doc, error_fields } = err
			if (doc.parentfield) {
				error_root_fieldnames.push(doc.parentfield)
			} else {
				for (const fieldname of error_fields) {
					error_root_fieldnames.push(fieldname)
				}
			}
		}

		this.slide_instances.forEach(s => {
			const slide_fieldnames = s.fields.map(df => df.fieldname)
			const has_error = error_root_fieldnames.some(fn => slide_fieldnames.includes(fn))
			if (has_error) {
				s.last_validation_result = false; // force error
			}
		})
	}
}

class SlideWithForm extends frappe.ui.Slide {
	refresh() {
		super.refresh()
		// fix missing layout refresh
		this.form.refresh()
	}

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

const extendsWithFullPageEditButton = (SlidesClass) => class SlidesWithFullPageEditButton extends SlidesClass {
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
				if (k in o) {
					// console.log(`%cget form.toolbar.${k}`, 'color:pink')
					return o[k]
				}
				return () => {
					// console.log(`%ccall form.toolbar.${k}`, 'color:pink')
					return undefined
				}
			},
			set(o, k, v) {
				o[k] = v
				// console.log(`%cset form.toolbar.${k}`, 'color:pink')
				return true
			}
		})
	}
	make() {
		this.layout.doc = this.doc
		this.layout.refresh_dependency();
		this.layout.attach_doc_and_docfields();

		this.script_manager.setup();

		/**
		 * Note: watch_model_updates() attaches listeners
		 * with frappe.model.on but there is no way to detach them.
		 * When a (normal) Form is created after a FakeForm is created,
		 * it also attaches its listeners with frappe.model.on,
		 * which causes all sorts of problems when navigating back and forth.
		 * The reverse is also true (FakeForm then Form).
		 * The problems seem related to the layout.refresh_dependency call
		 * inside the watchers. That's why FakeForm.fakeform_destroy() should
		 * always be called when hiding dialog or leaving page.
		 */
		this.watch_model_updates();

		this.ready = true;
		this.__defer_execute();
	}

	/**
	 * This overriden method has two purposes:
	 * 1. Removing any watcher added by a previous form,
	 *    but preserving them to restore them later.
	 * 2. Preparing the `FakeForm.unwatch_model_updates` call by keeping
	 *    track of the watchers added by `super.watch_model_updates`.
	 */
	watch_model_updates() {
		if (this.fakeform_previous_model_watchers) { return }

		const table_fields = frappe.get_children("DocType", this.doctype, "fields", {
			fieldtype: ["in", frappe.model.table_fields]
		})
		const watched_doctypes = frappe.utils.unique([
			this.doctype, ...table_fields.map(df => df.options),
		])

		this.fakeform_previous_model_watchers = {}
		for (const doctype of watched_doctypes) {
			// add for all watched doctypes, even if no watcher
			this.fakeform_previous_model_watchers[doctype] = frappe.model.events[doctype] || null
			delete frappe.model.events[doctype]
		}

		super.watch_model_updates()
	}

	unwatch_model_updates() {
		if (!this.fakeform_previous_model_watchers) { return }

		for (const doctype in this.fakeform_previous_model_watchers) {
			// delete frappe.model.events[doctype]
			frappe.model.events[doctype] = this.fakeform_previous_model_watchers[doctype]
		}
		delete this.fakeform_previous_model_watchers
	}

	/** Always call fakeform_destroy when changing page/hiding dialog */
	fakeform_destroy() {
		if (this.fakeform_was_destroyed) return;
		this.fakeform_was_destroyed = true;

		this.unwatch_model_updates();
	}

	/** Revert fakeform_destroy */
	fakeform_rebuild() {
		if (!this.fakeform_was_destroyed) return;
		delete this.fakeform_was_destroyed;

		this.watch_model_updates();
		this.refresh();
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

	fakeform_get_missing_fields(frm = this) {
		if (frm.doc.docstatus == 2) return []; // don't check for cancel

		const error_docs = [];

		const allDocs = frappe.model.get_all_docs(frm.doc);
		for (const doc of allDocs) {
			const error_fields = [];

			const docfields = frappe.meta.docfield_list[doc.doctype] || []
			for (const docfield of docfields) {
				if (docfield.fieldname) {
					const df = frappe.meta.get_docfield(doc.doctype, docfield.fieldname, doc.name);

					const hasValue = frappe.model.has_value(doc.doctype, doc.name, df.fieldname)
					if (df.reqd && !hasValue) {
						error_fields.push(docfield.fieldname);
					}
				}
			}

			if (error_fields.length > 0) {
				error_docs.push({ doc, error_fields });
			}
		}

		return error_docs;
	}
}

const slide_viewer_templates = {
	'Booking Credits Addition': {
		title: 'Booking Credits Addition',
		with_form: true,
		additional_settings(sv) {
			Object.assign(sv.doc, {
				rule_type: "Booking Credits Addition",
				conditions: "doc.subscription",
				include_item_in_manufacturing: 0,
			})
		},
		slideView: {
			title: "Booking Credits Addition",
			reference_doctype: "Booking Credit Rule",
			slides: [
				"section:",
				"section:triggers_section",
				// "section:posting_date_section",
				// "section:expiration_section",
				// "section:recurrence_section",
				(index, groupToSlide, globalTitle) => {
					const slide = groupToSlide([], index) // empty slide
					const posting_date_fields = groupToSlide('section:posting_date_section').fields
					const expiration_fields = groupToSlide('section:expiration_section').fields
					const recurrence_fields = groupToSlide('section:recurrence_section').fields
					slide.fields = [
						...posting_date_fields,
						{ fieldtype: 'Section Break' },
						...expiration_fields,
						{ fieldtype: 'Section Break' },
						...recurrence_fields,
					]
					return slide
				},
				"section:fields_map",
				// "section:applicable_deduction_rules_section",
				// "section:custom_rules_section",
				"*",
			]
		},
	}
}

frappe.show_slide_viewer_template = async function (template_name, docname = null) {
	const template = slide_viewer_templates[template_name]
	if (!template) {
		return frappe.throw('[Slide Viewer] ' + 'no such template: ' + template_name)
	}
	const slideViewer = new SlideViewer({
		docname,
		...template,
	})
	await slideViewer.renderInDialog()
}

function getSlidesTitleForMeta(meta, docname) {
	const is_new = docname && docname.match(/^new-.*-\d+$/)
	const doctype = meta.name

	let globalTitle = '';
	if (meta.issingle) {
		globalTitle = __(meta.name);
	} else if (!is_new) {
		const href = `/app/${frappe.router.slug(doctype)}/${encodeURIComponent(docname)}`;
		const link = `<a href="${href}" onclick="frappe.set_route('${href}');event&&event.preventDefault()">${docname}</a>`;
		globalTitle = __("Edit {0}", [link]);
	} else {
		globalTitle = __("New {0}", [__(doctype)]);
	}
	return globalTitle;
}

async function getSlidesForSlideView(slideView, docname) {
	const doctype = slideView.reference_doctype
	const meta = doctype && async_get_meta(doctype)

	if (slideView.slides) {
		return fieldGroupsToSlides({
			title: slideView.title,
			groups: slideView.slides,
			docname,
			meta,
		})
	} else if (doctype && meta) {
		return getAutoslidesForMeta(meta, docname)
		// return getAutoslidesForMeta(meta, docname, slideView.title)
	} else {
		return []
	}

	function async_get_meta(doctype) {
		const m = frappe.get_meta(doctype);
		if (m) return m;

		return new Promise((resolve) => {
			frappe.model.with_doctype(doctype, () => resolve(frappe.get_meta(doctype)))
		})
	}
}


/**
 * # Field groups
 * The `groups` parameter is a list of items that can be one of:
 *
 * - An object.
 *   ```js
 *   {
 *     title: 'Slide title',
 *     subtitle: 'Slide <i>subtitle</i>',
 *     help: 'A small help text with <b>html</b> support.'
 *     fields: [
 *       { fieldtype: 'Data', label: 'Lorem', fieldname: 'lorem' },
 *       { fieldtype: 'Column Break' },
 *       { fieldtype: 'Data', label: 'Ipsum', fieldname: 'ipsum' },
 *     ],
 *   }
 *   ```
 *
 * - An array containing fields or field names.
 *   ```js
 *   [
 *     "item_code",
 *     "item_name",
 *     { fieldtype: 'Column Break' },
 *     "item_group",
 *     "stock_uom",
 *   ]
 *   ```
 *
 * - A string beginning by `section:` followed by a section name,
 *   to insert a slide containing all the fields of the corresponding section
 *   visible on the document form of the given doctype.
 *   The section name can be either the Section Break fieldname or label.
 *   Example: `"section:Website"`
 *   Note: If empty (`section:`), the first section of the document form is inserted.
 *
 * - The string `*` to append all the unused fields on one slide.
 *   Useful if a form controller require some fields to exist.
 *
 * - A function.
 *   ```js
 *   (index, groupToSlide, globalTitle) => {
 *     // append two fields to the Website section
 *     const slide = groupToSlide('section:Website', index)
 *     slide.fields.push({ fieldtype: 'Column Break' })
 *     slide.fields.push('website_url')
 *   }
 *   ```
 *
 *
 * # Fields
 * The `fields` property of a slide (or an Array field group) is a list of items that can be one of:
 *
 * - A DocField object.
 *   ```js
 *   {
 *     fieldtype: 'Data',
 *     label: 'Lorem',
 *     fieldname: 'lorem'
 *   }
 *   ```
 *
 * - A string that refers to the fieldname of a field of the reference doctype.
 *   ```js
 *   "item_name"
 *   ```
 *
 * - The string `__newname` to insert the new name field if needed.
 */
function fieldGroupsToSlides({
	title,
	groups,
	docname,
	meta,
}) {
	const globalTitle = title || (meta && getSlidesTitleForMeta(meta, docname))
	const { fields_dict, sections } = getAliases(meta)

	const slides = []
	const usedFieldnames = new Set()
	let index = 0
	for (const group of groups) {
		const slide = groupToSlide(group, index)
		if (slide) {
			slide.fields.forEach(x => usedFieldnames.add(x.fieldname))
			slides.push(slide)
		}
	}
	return slides

	function groupToSlide(group, index = 0) {
		if (typeof group === 'string' && group.startsWith('section:')) {
			const sectionName = group.replace('section:', '')
			const { section, sectionBreak } = sectionByNameOrLabel(sectionName)
			if (section) {
				return {
					name: 'autoslide_' + index,
					title: globalTitle,
					subtitle: sectionBreak ? __(sectionBreak.label) : '',
					fields: section,
				}
			} else {
				console.warn('[Slide Viewer: getSlidesForSlideView] no such section with name/label: ' + sectionName)
			}
		} else if (group === '*') {
			if (meta) {
				const missingFields = meta.fields.filter(x => !usedFieldnames.has(x.fieldname))
				const slide = groupToSlide(missingFields, index)
				slide.should_skip = () => true
				return slide
			}
		} else if (Array.isArray(group)) {
			return {
				name: 'autoslide_' + index,
				title: globalTitle,
				fields: group.map(mapToField).filter(Boolean),
			}
		} else if (typeof group === 'object') {
			const fields = mapFieldsIfArray(group.fields)
			return {
				name: 'autoslide_' + index,
				title: globalTitle,
				...group, // can override defaults
				fields: fields,
			}
		} else if (typeof group === 'function') {
			const slide = group(index, groupToSlide, globalTitle)
			slide.fields = mapFieldsIfArray(slide.fields)
			return slide
		}
	}

	function mapFieldsIfArray(fields) {
		if (Array.isArray(fields)) {
			return fields.map(mapToField).filter(Boolean)
		} else {
			return []
		}
	}

	/**
	 * @returns {{ section?: DocField[]; sectionBreak?: DocField; }}
	 */
	function sectionByNameOrLabel(_name) {
		// if (!meta) return frappe.throw('[Slide Viewer: fieldGroupsToSlides] cannot use `section:` shorthand if no doctype is provided')
		if (!meta) return { section: null, sectionBreak: null }

		if (_name === '') return { section: sections[''], sectionBreak: null }

		const name = _name.toLocaleLowerCase()
		const nameMatch = (x) => x && (x.toLocaleLowerCase() === name)
		const sectionBreak = meta.fields.find(x => (x.fieldtype === 'Section Break') && (nameMatch(x.label) || nameMatch(x.fieldname)))
		const section = sections[sectionBreak.fieldname]
		return { section, sectionBreak }
	}

	function mapToField(fn) {
		if (typeof fn === 'string') {
			// if (!meta) return frappe.throw('[Slide Viewer: fieldGroupsToSlides] cannot use `field_name` shorthand if no doctype is provided')
			if (fn === '__newname') {
				const is_new = docname && docname.match(/^new-.*-\d+$/)
				if (is_new && meta && meta.autoname && ['prompt', 'name'].includes(meta.autoname.toLowerCase())) {
					return getNewNameFieldForDocType(meta.name)
				}
			}

			return fields_dict[fn]
		} else {
			return fn
		}
	}
}

/**
 * @param {?any} meta
 * @returns {{ fields_dict: Record<string, DocField>, sections: Record<string, DocField[]> }}
 */
function getAliases(meta) {
	if (!meta) return { fields_dict: {}, sections: {} };

	// key-value map: fieldname string -> docfield object
	const fields_dict = {}
	const sections = { '': [] }
	let curr_section = ''
	for (const df of meta.fields) {
		fields_dict[df.fieldname] = df

		if (df.fieldtype === 'Section Break') {
			curr_section = df.fieldname
			sections[curr_section] = []
		} else {
			sections[curr_section].push(df)
		}
	}
	return { fields_dict, sections }
}

function autoMiniSlides(doctype) {
	const meta = frappe.get_meta(doctype)

	const slides = [
		getEmptySlide(0), // initial empty section
	]
	let cur_slide = slides[0]
	for (const df of meta.fields) {
		if (df.fieldtype === 'Section Break') {
			const new_slide = getEmptySlide(slides.length)
			new_slide.title = cur_slide.title
			new_slide.subtitle = __(df.label)
			if (df.depends_on) {
				new_slide.condition = df.depends_on
			}

			if (cur_slide.fields.length === 0) {
				slides.pop()
			}
			slides.push(new_slide)
			cur_slide = new_slide
			continue
		}

		const isImportant = (
			(df.reqd || df.bold || df.allow_in_quick_entry) && !df.read_only
			// || df.fieldname === 'attributes'
			// || df.fieldname === 'item_defaults'
			// || df.fieldname === 'taxes'
			// || df.fieldname === 'item_group'
		)
		if (isImportant) {
			cur_slide.fields.push(df)
		}
	}

	return slides.filter(s => s.fields.length > 0)

	function getEmptySlide(index) {
		return {
			title: __('New {0}', [__(doctype)]),
			name: 'autoslide_' + index,
			fields: [],
		}
	}
}

function getNewNameFieldForDocType(doctype) {
	return {
		parent: doctype,
		fieldtype: 'Data',
		fieldname: '__newname',
		reqd: 1,
		// hidden: 1,
		label: __('Name'),
		get_status: () => 'Write'
	}
}
