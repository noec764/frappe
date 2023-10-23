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

frappe.provide("frappe.ui");

frappe.ui.SlideViewer = class SlideViewer {
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
		// Defaults
		this.SlideClass = frappe.ui.Slide;
		this.SlidesClass = frappe.ui.Slides;

		/** @type {SlideView} */
		this.slideView = null;
		this.route = null;
		this.starting_slide = 0;
		this.documentName = null;
		this.additional_settings = null;
		this.doc = null;

		/** @type {frappe.ui.Slides} */
		this.slidesInstance = null;

		if (options.route) {
			this.route = options.route;
		} else if (options.slideView) {
			this.slideView = options.slideView;
			const slideViewDefaults = {
				title: "",
				reference_doctype: null,
				allow_back: true,
				allow_any: true,
				done_state: false,
				can_edit_doc: true,
				can_create_doc: true,
				add_fullpage_edit_btn: false,
				slides: [],
			};
			for (const k in slideViewDefaults) {
				// if (this.slideView[k] === undefined) {
				if (!(k in this.slideView)) {
					this.slideView[k] = slideViewDefaults[k];
				}
			}
		} else {
			return this.throwDevError(
				"should have either route or slideView param",
				"constructor"
			);
		}

		if (options.with_form) {
			this.with_form = true;
			Object.assign(this, {
				SlidesClass: SlidesWithForm,
				SlideClass: SlideWithForm,
			});
		}

		if (options.docname) {
			this.documentName = options.docname;
		}
		if (options.starting_slide) {
			this.starting_slide = options.starting_slide;
		}
		if (options.additional_settings) {
			this.additional_settings = options.additional_settings;
		}

		if (options.SlideClass) {
			this.SlideClass = options.SlideClass;
		}
		if (options.SlidesClass) {
			this.SlidesClass = options.SlidesClass;
		}
	}

	showDevWarning(msg, ctx) {
		console.error(ctx ? `[Slide Viewer: ${ctx}]` : "[Slide Viewer]", msg); // eslint-disable-line no-console
	}

	throwDevError(error, ctx) {
		return frappe.throw((ctx ? `[Slide Viewer: ${ctx}]` : "[Slide Viewer]") + " " + error);
	}

	hide() {
		window.cur_slides = undefined;
		if (
			this.slidesInstance &&
			this.slidesInstance.parent_form &&
			this.slidesInstance.parent_form.slide_viewer_form_destroy
		)
			this.slidesInstance.parent_form.slide_viewer_form_destroy();
	}

	show() {
		window.cur_slides = this.slidesInstance;
		if (
			this.slidesInstance &&
			this.slidesInstance.parent_form &&
			this.slidesInstance.parent_form.slide_viewer_form_rebuild
		)
			this.slidesInstance.parent_form.slide_viewer_form_rebuild();
	}

	/**
	 * Fetch required data from server
	 */
	async _fetch() {
		if (!this.slideView) {
			await this._fetchSlideView();
		}

		const { reference_doctype } = this.slideView;

		if (reference_doctype) {
			// fetch meta for DocType
			await new Promise((cb) => frappe.model.with_doctype(reference_doctype, cb));
		}

		await this._fetchDoc();
	}

	async _fetchDoc() {
		const { reference_doctype, can_create_doc, can_edit_doc } = this.slideView;

		if (!reference_doctype) {
			if (this.slideView.slides && this.slideView.on_complete) {
				this.doc = {}; // okay
			} else if (this.slideView.slides) {
				this.showDevWarning(
					"missing slideView.on_complete function: the Slide Viewer cannot be submitted"
				);
				this.doc = {}; // kinda okay
			} else {
				this.throwDevError(
					"cannot open Slide View with neither reference_doctype nor slides",
					"constructor"
				);
			}
			return;
		}

		// check permissions
		let mode = "Error";
		let error = "";

		const meta = frappe.get_meta(reference_doctype);

		const is_new = this.documentName && this.documentName.match(/^new-.*-\d+$/);
		const in_locals =
			this.documentName && frappe.get_doc(reference_doctype, this.documentName);

		if (meta.issingle && !this.documentName) {
			// Single DocType
			mode = "Edit";
			this.documentName = meta.name;
		} else if (in_locals && is_new) {
			// edit if the document exists in locals and the name looks like a new name
			mode = "EditLocals";
		} else if (is_new) {
			// create if the name looks like a new name but the document is not in locals
			mode = "Create";
		} else if (this.documentName) {
			// edit if a document name was given
			mode = "Edit";
		} else {
			mode = "Create";
		}

		if ((mode === "Create" || mode === "EditLocals") && !can_create_doc) {
			mode = "Error";
			error = "cannot create";
		}
		if (mode === "Edit" && !can_edit_doc) {
			mode = "Error";
			error = "cannot edit";
		}

		if (mode === "Edit" || mode === "EditLocals") {
			if (mode === "EditLocals") {
				this.doc = frappe.get_doc(reference_doctype, this.documentName);

				if (!this.doc) {
					error = "missing document";
				}
			} else {
				let is403 = false;
				this.doc = await frappe.model.with_doc(
					reference_doctype,
					this.documentName,
					(name, r) => {
						// callback is called before promise resolution
						if (r && r["403"]) is403 = true;
					}
				);

				if (!this.doc) {
					error = "missing document";
				} else if (is403) {
					error = "forbidden";
				}
			}
		} else if (mode === "Create") {
			const with_mandatory_children = true;
			this.doc = frappe.model.get_new_doc(
				reference_doctype,
				undefined,
				undefined,
				with_mandatory_children
			);
			if (this.doc) {
				// okay
				this.documentName = this.doc.name;

				// if (cur_page.slideViewer === this) {
				if (this.route && frappe.router.get_sub_path().startsWith("slide-viewer")) {
					let newUrl = ["slide-viewer", this.slideView.route, this.documentName];
					newUrl = frappe.router.get_route_from_arguments(newUrl);
					newUrl = frappe.router.convert_to_standard_route(newUrl);
					newUrl = frappe.router.make_url(newUrl);
					setTimeout(() => {
						history.replaceState(null, null, newUrl);
						// frappe.router.route()
					}, 0); // run after page_show event
				}
			} else {
				error = "frappe.model.get_new_doc returned null --> doctype meta not loaded?";
			}
		}

		if (error) {
			this.showUserError(error);
			throw new Error(error); // fallback
		}
	}

	async _fetchSlideView() {
		// get Slide View by route
		this.slideView = await frappe.xcall(
			"frappe.custom.page.slide_viewer.api.get_slide_view_by_route",
			{ route: this.route }
		);
		this._checkSlideViewPermissions();
	}

	_checkSlideViewPermissions() {
		if (!this.slideView) {
			this.showUserError("missing slide view");
		}

		const perms = frappe.perm.get_perm("Slide View", this.slideView.name);
		if (!perms.some((x) => x.read)) {
			this.showUserError("slide view permissions");
		}
	}

	update_page_title() {
		if (this.documentName) {
			frappe.utils.set_title(__(this.slideView.title) + " - " + this.documentName);
		} else {
			frappe.utils.set_title(__(this.slideView.title));
		}
	}

	/**
	 * Renders the Slide Viewer in the given container
	 * @param {HTMLElement|JQuery} wrapper
	 */
	async renderInWrapper(wrapper) {
		await this._fetch();
		if (!this.doc || !this.slideView) {
			return this.throwDevError("missing .doc or .slideView", "renderInWrapper");
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
	async renderInDialog(dialogOptions = { size: "large" }) {
		const svr = this;
		Object.assign(dialogOptions, { onhide: () => svr.hide() });
		const dialog = new frappe.ui.Dialog(dialogOptions);

		await this._fetch();
		if (!this.doc || !this.slideView) {
			return this.throwDevError("missing .doc or .slideView", "renderInDialog");
		}

		// make the Slides instance with optional values to populate the form.
		dialog.standard_actions.empty();
		$(dialog.footer).show();
		$(dialog.footer).removeClass("hide");
		dialog.doc = this.doc;
		const slidesSettings = await this.getSlidesSettings({
			parent: dialog.wrapper,
			// parent_form: dialog,
			$container: $(dialog.wrapper),
			$body: dialog.$body,
			$footer: $(dialog.standard_actions),
			$header: $(dialog.header).find(".title-section").addClass("justify-center"),
			after_load() {
				this.$slide_progress.css({ margin: "0" });
				this.$footer.find(".flex-row").addClass("row");
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
						args: { doc: this.doc, action: "Save" },
						callback: (r) => {
							const doc = r.docs ? r.docs[0] : this.doc;
							frappe.set_route("Form", doc.doctype, doc.name);
							// $(document).trigger("save", [doc]);
						},
						error: (r) => {
							console.error(r); // eslint-disable-line no-console
						},
						btn: this.$complete_btn,
						freeze_message: __("Loading"),
					});
				} else {
					this.showDevWarning("cannot save document without doctype", "Dialog");
				}
			};
		}

		this._renderWithSettings(slidesSettings);
		dialog.show();
	}

	_renderWithSettings(slidesSettings) {
		if (!slidesSettings) {
			this.showUserError("no slides");
			return;
		}

		let SlidesClass = this.SlidesClass;
		if (this.with_form && this.slideView.add_fullpage_edit_btn) {
			SlidesClass = extendsWithFullPageEditButton(SlidesClass);
		}
		this.slidesInstance = new SlidesClass(slidesSettings);
		this.show();
	}

	showUserError(error) {
		// const canRedirect = Boolean(this.route)
		// const canRedirect = cur_page.slideViewer === this
		const canRedirect = frappe.router.get_sub_path().startsWith("slide-viewer");

		if (error === "cannot edit") {
			canRedirect && frappe.show_not_permitted(__("Slide View"));
			throw new Error("[Slide Viewer] cannot edit document with this Slide View");
		} else if (error === "cannot create") {
			canRedirect && frappe.show_not_permitted(__("Slide View"));
			throw new Error("[Slide Viewer] cannot create document with this Slide View");
		} else if (error === "missing document") {
			canRedirect &&
				frappe.show_not_found(
					__(this.slideView.reference_doctype) + " - " + __(this.documentName)
				);
			throw new Error(
				"[Slide Viewer] " +
					__("{0} {1} not found", [
						__(this.slideView.reference_doctype),
						__(this.documentName),
					])
			);
		} else if (error === "forbidden") {
			canRedirect &&
				frappe.show_not_permitted(
					__(this.slideView.reference_doctype) + " - " + __(this.documentName)
				);
			throw new Error(
				"[Slide Viewer] " + __("You don't have the permissions to access this document")
			);
		} else if (error === "slide view permissions") {
			canRedirect &&
				frappe.show_not_permitted(__(this.slideView.doctype) + " " + this.slideView.name);
			throw new Error(
				"[Slide View] Insufficient Permission for Slide View: " + this.slideView.name
			);
		} else if (error === "missing slide view") {
			return frappe.throw("[Slide Viewer] missing Slide View");
		} else if (error === "no slides") {
			const msg = __("Oops, there are no slides to display.", null, "Slide View");
			if (canRedirect) {
				frappe.show_message_page({
					page_name: msg,
					message: msg,
					img: `/assets/frappe/images/ui/empty.svg`,
				});
			} else {
				frappe.throw(msg);
			}
			throw new Error("[Slide View] " + msg);
		} else if (error) {
			return frappe.throw("[Slide Viewer] " + error);
		}
	}

	async getSlidesSettings(params) {
		const allSlides = await this.getSlides();
		if (!allSlides || allSlides.length === 0) {
			return null;
		}

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
			on_complete:
				typeof this.slideView.on_complete === "function"
					? this.slideView.on_complete
					: undefined,

			...params,
		};

		if (this.with_form) {
			settings.text_complete_btn = __("Save");
			settings.on_complete = function () {
				if (this.parent_form) {
					this.parent_form.save();
				}
			};
		}

		if (this.additional_settings) {
			if (typeof this.additional_settings === "function") {
				Object.assign(settings, this.additional_settings(this));
			} else {
				Object.assign(settings, this.additional_settings);
			}
		}

		return settings;
	}

	async getSlides() {
		const docname = (this.doc && this.doc.name) || this.documentName;
		return await getSlidesForSlideView(this.slideView, docname);
	}

	// utils
	static getParamsFromRouter() {
		let slideViewRoute = null;
		let docname = null;
		let starting_slide = null;

		const route = frappe.router.get_sub_path_string().split("/");
		if (route[0] === "slide-viewer") {
			if (route.length >= 2) {
				slideViewRoute = decodeURIComponent(route[1]);
			}
			if (route.length >= 3) {
				docname = decodeURIComponent(route[2]);
			}
			if (route.length >= 4) {
				starting_slide = cint(route[3]);
			}
		}

		return {
			route: slideViewRoute,
			docname: docname,
			starting_slide: starting_slide,
		};
	}
};

// Slide classes with additional features to support SlideViewerForm

class SlidesWithForm extends frappe.ui.Slides {
	render_progress_dots(...args) {
		if (this.parent_form) this.updateSlidesWithErrorFields();
		super.render_progress_dots.apply(this, args);
	}

	before_load() {
		super.before_load();
		this.$container.css({ width: "100%", maxWidth: "800px" });
	}

	setup() {
		const slide_viewer_form = new frappe.ui.form.SlideViewerForm(this.$container, this.doc, {
			parentSlides: this,
		});
		this.parent_form = slide_viewer_form;
		cur_frm = slide_viewer_form;

		slide_viewer_form.setup();

		super.setup();

		for (const s of this.slide_instances) {
			if (!s.made) {
				s.make();
			}
		}

		const all_fields = this.slide_settings.flatMap((s) => s.fields);
		const fields_list = this.slide_instances.flatMap((s) => s.form.fields_list);
		const fields_dict = Object.fromEntries(
			this.slide_instances.flatMap((s) => Object.entries(s.form.fields_dict))
		);

		slide_viewer_form.slide_viewer_form_set_fields({
			df: all_fields,
			list: fields_list,
			dict: fields_dict,
		});

		slide_viewer_form.make();
		slide_viewer_form.refresh();

		frappe.model.on(slide_viewer_form.doctype, "*", (fieldname, value, doc) => {
			if (doc.name === slide_viewer_form.docname) {
				this.render_progress_dots();
				this.show_hide_prev_next(this.current_id);
			}
		});
	}

	updateSlidesWithErrorFields() {
		if (!this.parent_form.slide_viewer_form_get_missing_fields) return;
		const error_docs = this.parent_form.slide_viewer_form_get_missing_fields();
		// Names of the invalid fields in the main document.
		const error_root_fieldnames = [];

		for (const err of error_docs) {
			const { doc, error_fields } = err;
			if (doc.parentfield) {
				error_root_fieldnames.push(doc.parentfield);
			} else {
				for (const fieldname of error_fields) {
					error_root_fieldnames.push(fieldname);
				}
			}
		}

		this.slide_instances.forEach((s) => {
			const slide_fieldnames = s.fields.map((df) => df.fieldname);
			const has_error = error_root_fieldnames.some((fn) => slide_fieldnames.includes(fn));
			if (has_error) {
				s.last_validation_result = false; // force error
			}
		});
	}
}

class SlideWithForm extends frappe.ui.Slide {
	set_form_values(values) {
		return Promise.resolve();
	} // ignore

	should_skip() {
		if (super.should_skip()) {
			return true;
		}

		// skip or not by evaluating depends_on
		if (this.condition && this.parent_form && this.parent_form.layout) {
			const conditionValid = this.parent_form.layout.evaluate_depends_on_value(
				this.condition
			);
			if (!conditionValid) {
				return true;
			}
		}

		return false;
	}
}

const extendsWithFullPageEditButton = (SlidesClass) =>
	class SlidesWithFullPageEditButton extends SlidesClass {
		before_load() {
			super.before_load();

			if (this.doc && this.doc.doctype && this.doc.name) {
				this.$fullPageEditBtn = $(`
				<button class="btn btn-secondary btn-edit-in-full-page">
					${frappe.utils.icon("edit", "xs")}
					${__("Edit in full page")}
				</button>
			`);
				this.$fullPageEditBtn.appendTo(this.$footer.find(".text-left"));
				this.$fullPageEditBtn.on("click", () => {
					// @see open_doc() in frappe/public/js/frappe/form/quick_entry.js
					frappe.set_route("Form", this.doc.doctype, this.doc.name);
				});
			}
		}
		before_show_slide(id) {
			super.before_show_slide(id);

			if (this.$fullPageEditBtn) {
				if (this.can_go_prev(id)) {
					this.$fullPageEditBtn.hide();
				} else {
					this.$fullPageEditBtn.show();
				}
			}
		}
	};

async function getSlidesForSlideView(slideView, docname) {
	const doctype = slideView.reference_doctype;
	const meta = doctype && async_get_meta(doctype);

	if (slideView.slides) {
		return fieldGroupsToSlides({
			title: slideView.title,
			groups: slideView.slides,
			docname,
			meta,
		});
	} else if (doctype && meta) {
		return getAutoslidesForMeta(meta, docname);
		// return getAutoslidesForMeta(meta, docname, slideView.title)
	} else {
		return [];
	}

	function async_get_meta(doctype) {
		const m = frappe.get_meta(doctype);
		if (m) return m;

		return new Promise((resolve) => {
			frappe.model.with_doctype(doctype, () => resolve(frappe.get_meta(doctype)));
		});
	}
}

function getAutoslidesForMeta(meta, docname = "", title = "") {
	const doctype = meta.name;
	const fields = meta.fields.slice(); // create a shallow copy of meta.fields

	const is_new = docname && docname.match(/^new-.*-\d+$/);
	// const autonameFieldname = (is_new && meta && meta.autoname && meta.autoname.startsWith('field:')) ? meta.autoname.replace('field:', '') : null
	if (is_new && meta.autoname && ["prompt", "name"].includes(meta.autoname.toLowerCase())) {
		if (!fields.find((x) => x.fieldname === "name" || x.fieldname === "__newname")) {
			fields.unshift(getNewNameFieldForDocType(doctype));
		}
	}

	const slides = [];

	const globalTitle = title || getSlidesTitleForMeta(meta, docname);

	if (slides.length === 0) {
		slides.push(newEmptySlide());
	}

	const filteredOutFieldTypes = [
		"Section Break", // ...frappe.model.layout_fields,
	];
	for (const field of fields) {
		let slide = slides[slides.length - 1];

		const createNewSlide = [
			slide == null,
			field.fieldtype === "Section Break",
			// field.fieldtype === 'Column Break',
		].some((x) => x == true); // at least one condition

		if (createNewSlide) {
			let newSlideSubtitle = "???";
			if (field.fieldtype === "Section Break") {
				newSlideSubtitle = __(field.label);
			} else {
				newSlideSubtitle = /*old slide*/ slide.subtitle;
			}
			slide = newEmptySlide(newSlideSubtitle);
			slides.push(slide);

			if (field.fieldtype === "Section Break") {
				slide.condition = field.depends_on;
			}
		}

		const ignoreThisField = filteredOutFieldTypes.includes(field.fieldtype);
		if (!ignoreThisField) {
			slide.fields.push({
				...field,
				label: __(field.label), // translate label
			});
		}
	}

	return slides.filter((slide) => slide.fields.length > 0);
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
			name: "autoslide_" + slides.length,
			title: globalTitle,
			subtitle: translatedSubtitle,
			// icon: "fa fa-flag",
			fields: [],
		};
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
function fieldGroupsToSlides({ title, groups, docname, meta }) {
	const globalTitle = title || (meta && getSlidesTitleForMeta(meta, docname));
	const is_new = docname && docname.match(/^new-.*-\d+$/);

	const { fields_dict, sections } = getAliases(meta);

	const slides = [];
	const usedFieldnames = new Set();
	for (let index = 0; index < groups.length; index++) {
		const group = groups[index];
		const slide = groupToSlide(group, index);
		if (slide) {
			slide.fields.forEach((x) => usedFieldnames.add(x.fieldname));
			slides.push(slide);
		}
	}
	return slides;

	function groupToSlide(group, index = 0) {
		if (typeof group === "string" && group.startsWith("section:")) {
			const sectionName = group.replace("section:", "");
			const { section, sectionBreak } = sectionByNameOrLabel(sectionName);
			if (section) {
				return {
					name: "autoslide_" + index,
					title: globalTitle,
					subtitle: sectionBreak ? __(sectionBreak.label) : "",
					fields: section,
				};
			} else {
				frappe.throw(
					"[Slide Viewer: getSlidesForSlideView]",
					"no such section with name/label:",
					sectionName
				);
			}
		} else if (group === "*") {
			if (meta) {
				const missingFields = meta.fields.filter((x) => !usedFieldnames.has(x.fieldname));
				const slide = groupToSlide(missingFields, index);
				slide.should_skip = () => true;
				return slide;
			} else {
				frappe.throw(
					"[Slide Viewer: getSlidesForSlideView]",
					"cannot use `*` shorthand if no doctype is provided"
				);
			}
		} else if (Array.isArray(group)) {
			return {
				name: "autoslide_" + index,
				title: globalTitle,
				fields: group.map(mapToField).filter(Boolean),
			};
		} else if (typeof group === "object") {
			const fields = mapFieldsIfArray(group.fields);
			return {
				name: "autoslide_" + index,
				title: globalTitle,
				...group, // can override defaults
				fields: fields,
			};
		} else if (typeof group === "function") {
			const slide = group(index, groupToSlide, globalTitle);
			slide.fields = mapFieldsIfArray(slide.fields);
			return slide;
		} else {
			frappe.throw(
				"[Slide Viewer: getSlidesForSlideView]",
				"invalid slide descriptor:",
				group
			);
		}
	}

	function mapFieldsIfArray(fields) {
		if (Array.isArray(fields)) {
			return fields.map(mapToField).filter(Boolean);
		} else {
			return [];
		}
	}

	/**
	 * @returns {{ section?: DocField[]; sectionBreak?: DocField; }}
	 */
	function sectionByNameOrLabel(_name) {
		if (!meta)
			return frappe.throw(
				"[Slide Viewer: fieldGroupsToSlides] cannot use `section:` shorthand if no doctype is provided"
			);
		// if (!meta) return { section: null, sectionBreak: null }

		if (_name === "") return { section: sections[""], sectionBreak: null };

		const name = _name.toLocaleLowerCase();
		const nameMatch = (x) => x && x.toLocaleLowerCase() === name;
		const sectionBreak = meta.fields.find(
			(x) =>
				x.fieldtype === "Section Break" && (nameMatch(x.label) || nameMatch(x.fieldname))
		);
		const section = sections[sectionBreak.fieldname];
		return { section, sectionBreak };
	}

	function mapToField(fn) {
		if (typeof fn === "string") {
			if (!meta)
				return frappe.throw(
					"[Slide Viewer: fieldGroupsToSlides] cannot use `field_name` shorthand if no doctype is provided"
				);
			if (fn === "__newname") {
				if (
					is_new &&
					meta &&
					meta.autoname &&
					["prompt", "name"].includes(meta.autoname.toLowerCase())
				) {
					return getNewNameFieldForDocType(meta.name);
				}
			}

			return fields_dict[fn];
		} else {
			return fn;
		}
	}
}

function autoMiniSlides(doctype) {
	const meta = frappe.get_meta(doctype);

	const slides = [
		getEmptySlide(0), // initial empty section
	];
	let cur_slide = slides[0];
	for (const df of meta.fields) {
		if (df.fieldtype === "Section Break") {
			const new_slide = getEmptySlide(slides.length);
			new_slide.title = cur_slide.title;
			new_slide.subtitle = __(df.label);
			if (df.depends_on) {
				new_slide.condition = df.depends_on;
			}

			if (cur_slide.fields.length === 0) {
				slides.pop();
			}
			slides.push(new_slide);
			cur_slide = new_slide;
			continue;
		}

		const isImportant = (df.reqd || df.bold || df.allow_in_quick_entry) && !df.read_only;
		// || df.fieldname === 'attributes'
		// || df.fieldname === 'item_defaults'
		// || df.fieldname === 'taxes'
		// || df.fieldname === 'item_group'
		if (isImportant) {
			cur_slide.fields.push(df);
		}
	}

	return slides.filter((s) => s.fields.length > 0);

	function getEmptySlide(index) {
		return {
			title: __("New {0}", [__(doctype)]),
			name: "autoslide_" + index,
			fields: [],
		};
	}
}

function getNewNameFieldForDocType(doctype) {
	return {
		parent: doctype,
		fieldtype: "Data",
		fieldname: "__newname",
		reqd: 1,
		// hidden: 1,
		label: __("Name"),
		get_status: () => "Write",
	};
}

function getSlidesTitleForMeta(meta, docname) {
	const is_new = docname && docname.match(/^new-.*-\d+$/);
	const doctype = meta.name;

	let globalTitle = "";
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

/**
 * @param {?any} meta
 * @returns {{ fields_dict: Record<string, DocField>, sections: Record<string, DocField[]> }}
 */
function getAliases(meta) {
	if (!meta) return { fields_dict: {}, sections: {} };

	// key-value map: fieldname string -> docfield object
	const fields_dict = {};
	const sections = { "": [] };
	let curr_section = "";
	for (const df of meta.fields) {
		fields_dict[df.fieldname] = df;

		if (df.fieldtype === "Section Break") {
			curr_section = df.fieldname;
			sections[curr_section] = [];
		} else {
			sections[curr_section].push(df);
		}
	}
	return { fields_dict, sections };
}

frappe.provide("frappe.slide_viewer_templates");

/**
 * Open a Slide Viewer dialog with the given template name.
 * @param {string|{}} template_name The template name in frappe.slide_viewer_templates, or a template object.
 * @param {string} [docname] The name of the document to edit. Optional.
 * @returns
 */
frappe.show_slide_viewer_template = async function (template_name, docname = null) {
	const template =
		typeof template_name === "object"
			? template_name
			: frappe.slide_viewer_templates[template_name];
	if (!template) {
		return frappe.throw("[Slide Viewer] " + "no such template: " + template_name);
	}
	const slideViewer = new frappe.ui.SlideViewer({
		docname,
		...template,
	});
	await slideViewer.renderInDialog();
};
