// Copyright (c) 2021, Dokos SAS and Contributors
// License: See license.txt

/**
 * @typedef {Object} SlideView
 * @property {string} title
 * @property {string} reference_doctype
 * @property {string} route
 * @property {boolean} allow_back
 * @property {boolean} allow_any
 * @property {boolean} done_state
 * @property {boolean} can_edit_doc
 * @property {boolean} can_create_doc
 * @property {boolean} add_fullpage_edit_btn
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
	 * @property {string} [route] - The Slide View route name. Required.
	 * @property {SlideView} [slideView]
	 *
	 * @property {string} [docname] - The document to edit using this Slide View. Optional.
	 * @property {string} [starting_slide] - The slide to show first.
	 * @property {Function} [SlideClass]
	 * @property {Function} [SlidesClass]
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
		} else {
			return frappe.throw('[Slide Viewer] constructor: should have either route or slideView param') // @todo
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

		// check permissions
		let mode = 'Error'
		let error = ''
		let fetchFromLocals = false

		if (reference_doctype) {
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
		} else {
			// @todo not an invalid state, check for .slides and .on_complete
			return frappe.throw('[Slide Viewer] cannot edit document with a Slide View without reference_doctype')
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
				let newUrl = ['slide-viewer', this.slideView.route, this.documentName]
				newUrl = frappe.router.get_route_from_arguments(newUrl)
				newUrl = frappe.router.convert_to_standard_route(newUrl)
				newUrl = frappe.router.make_url(newUrl)
				setTimeout(() => {
					frappe.router.push_state(newUrl)
				}, 0) // run after page_show event
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
	async renderInDialog(dialog) {
		await this._fetch()
		if (!this.doc || !this.slideView) {
			frappe.show_not_found('');
			throw new Error("[SlideViewer.renderInWrapper]: missing .doc or .slideView");
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

				this.make_all_slides();
				const all_fields = this.slide_settings.flatMap(s => s.fields)
				const fields_list = this.slide_instances.flatMap(s => s.form.fields_list)
				const fields_dict = Object.fromEntries(this.slide_instances.flatMap(s => Object.entries(s.form.fields_dict)))

				dialog.fields = all_fields
				dialog.fields_list = fields_list
				dialog.fields_dict = fields_dict
			},
			on_complete() {
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
					freeze_message: 'freeze message',
				})
			}
		});

		this._renderWithSettings(slidesSettings);
	}

	_renderWithSettings(slidesSettings) {
		if (!slidesSettings) {
			this.showErrorNoSlides();
			return;
		}

		this.slidesInstance = new (this.SlidesClass)(slidesSettings);
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

		const baseSettings = {
			slideViewer: this,
			slide_class: this.SlideClass,

			slides: allSlides,
			doc: this.doc,
			starting_slide: this.starting_slide,
			unidirectional: !this.slideView.allow_back,
			unidirectional_allow_back: false,
			clickable_progress_dots: this.slideView.allow_any && this.slideView.allow_back,
			done_state: this.slideView.done_state,

			on_complete() {
				if (this.parent_form) {
					this.parent_form.save();
				}
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
		const shouldGenerateAutoSlides = (this.slideView.slides === undefined);
		if (shouldGenerateAutoSlides) {
			if (ref_doctype) {
				allSlides = await getAutoslidesForDocType(ref_doctype, (this.doc&&this.doc.name) || this.documentName);
			} else {
				// cannot generate auto slides without doctype
			}
		} else {
			// allSlides = await getSlidesForSlideView(slideView)
			allSlides = this.slideView.slides;
		}

		return allSlides;
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

			debugger
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
		SlidesClass: SlidesWithForm,
		SlideClass: SlideWithForm,

		/** @this {SlideViewer} */
		additional_settings() {
			if (this.slideView.add_fullpage_edit_btn) {
				this.SlidesClass = extendsWithFullPageEditButton(this.SlidesClass)
			}

			return { text_complete_btn: __("Save") }
		},
	})

	const container = $('<div style="padding: 2rem 1rem">').appendTo(page.body)
	wrapper.slideViewer = slideViewer // set before render
	await slideViewer.renderInWrapper(container)
	slideViewer.slidesInstance.render_progress_dots()
}

async function getAutoslidesForDocType(doctype, docname = '') {
	const meta = await SlideViewer.getMetaForDocType(doctype)
	const fields = meta.fields.slice()

	const is_new = docname && docname.match(/^new-.*-\d+$/)

	if (is_new && meta.autoname && ['prompt', 'name'].includes(meta.autoname.toLowerCase())) {
		fields.unshift({
			parent: doctype,
			fieldtype: 'Data',
			fieldname: '__newname',
			reqd: 1,
			// hidden: 1,
			label: __('Name'),
			get_status: () => 'Write'
		})
	}

	const slides = []

	let globalTitle = ''
	if (meta.issingle) {
		globalTitle = __(meta.name)
	} else if (!is_new) {
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
