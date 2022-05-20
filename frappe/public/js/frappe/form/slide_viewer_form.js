frappe.provide('frappe.ui.form');

/**
 * Because Frappe/Dodock is not built to have multiple instances
 * of the same type of Form (doctype, docname), the SlideViewerForm class
 * tries to prevent bugs related to `frappe.ui.form.handlers`,
 * `frappe.model.events`, `frappe.meta.docfield_copy`.
 */
frappe.ui.form.SlideViewerForm = class SlideViewerForm extends frappe.ui.form.Form {
	constructor(wrapper, doc, opts = {}) {
		if (!(typeof doc === 'object' && doc.doctype)) {
			frappe.throw('[SlideViewerForm] `doc` parameter should be an object with a `doctype` property.')
		}

		const doctype = doc.doctype

		const slide_viewer_form_parent = $('<div>')
		super(doctype, slide_viewer_form_parent, true, undefined)


		// values to store and restore
		this.__stored_values = {
			'docfield copy': {
				get: () => frappe.meta.docfield_copy,
				set: (prev) => { frappe.meta.docfield_copy = prev },
			},
			'model events': {
				get: () => frappe.model.events,
				set: (prev) => { frappe.model.events = prev },
			},
			'form events': {
				get: () => frappe.ui.form.handlers,
				set: (prev) => { frappe.ui.form.handlers = prev },
			},
		};
		this.slide_viewer_form_store_environment();


		this.ready = false
		this.form_wrapper = wrapper

		this.page = new Proxy({}, {
			get(o, k, r) {
				if (k === 'main') return $('<div>')
				return () => {
					// console.log(`%cfrm.page.${k}`, 'color:pink')
					return undefined
				}
			}
		})
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
	slide_viewer_form_set_fields({ df, list, dict }) {
		this.slide_viewer_form_fields_df = df
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
		this.layout.fields = this.slide_viewer_form_fields_df
		this.layout.fields_list = this.fields
		this.layout.fields_dict = this.fields_dict

		console.log(this.layout)

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
		 * When a (normal) Form is created after a SlideViewerForm is created,
		 * it also attaches its listeners with frappe.model.on,
		 * which causes all sorts of problems when navigating back and forth.
		 * The reverse is also true (SlideViewerForm then Form).
		 * The problems seem related to the layout.refresh_dependency call
		 * inside the watchers. That's why SlideViewerForm.slide_viewer_form_destroy() should
		 * always be called when hiding dialog or leaving page.
		 */
		this.watch_model_updates();

		this.ready = true;
		this.__defer_execute();
	}

	slide_viewer_form_store_environment () {
		for (const k in this.__stored_values) {
			const s = this.__stored_values[k]
			s.value = s.get() // preserve old value
			s.set(s.my_value || {}) // clear current value (eventually restoring previously updated value set by this form)
			delete s.my_value
		}
	}
	slide_viewer_form_restore_environment() {
		for (const k in this.__stored_values) {
			const s = this.__stored_values[k]
			s.my_value = s.get() // store current value (set by this form)
			s.set(s.value) // restore previous current value (set by other forms)
			delete s.value
		}
	}

	/** Always call slide_viewer_form_destroy when changing page/hiding dialog */
	slide_viewer_form_destroy() {
		if (this.slide_viewer_form_was_destroyed) return;
		this.slide_viewer_form_was_destroyed = true;

		this.slide_viewer_form_restore_environment();
	}

	/** Revert slide_viewer_form_destroy */
	slide_viewer_form_rebuild() {
		if (!this.slide_viewer_form_was_destroyed) return;
		delete this.slide_viewer_form_was_destroyed;

		this.slide_viewer_form_store_environment();
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
		this.__deferred.splice(0, n)
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
		this.slide_viewer_form_saving = true
		await super.save.apply(this, args)
		this.slide_viewer_form_saving = false
	}
	async savesubmit(...args) {
		this.slide_viewer_form_saving = true
		await super.savesubmit.apply(this, args)
		this.slide_viewer_form_saving = false
	}
	savecancel(btn, callback, on_error) {
		this.slide_viewer_form_saving = true
		super.savecancel(btn, (...args) => {
			callback&&callback(...args)
			this.slide_viewer_form_saving = false
		}, (...args) => {
			on_error&&on_error(...args)
			this.slide_viewer_form_saving = false
		})
	}
	async amend_doc() {
		this.slide_viewer_form_saving = true
		super.amend_doc()
		this.slide_viewer_form_saving = false
	}
	refresh(switched_docname) {
		if (!this.slide_viewer_form_saving) {
			// Skip the refresh during/after save to prevent the SlideViewerForm from being reused on the real form page.
			super.refresh(switched_docname)
		}
	}
	refresh_header() { /* Prevent frappe.utils.set_title */ }

	slide_viewer_form_get_missing_fields(frm = this) {
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
