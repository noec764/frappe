frappe.provide('frappe.ui.form');

/**
 * Because Frappe/Dodock is not built to have multiple instances
 * of the same type of Form (doctype, docname), the FakeForm class
 * tries to prevent bugs with a special handling of
 * `frappe.model.events` and `frappe.meta.docfield_copy`.
 */
frappe.ui.form.FakeForm = class FakeForm extends frappe.ui.form.Form {
	constructor(wrapper, doc, opts = {}) {
		if (!(typeof doc === 'object' && doc.doctype)) {
			frappe.throw('[FakeForm] `doc` parameter should be an object with a `doctype` property.')
		}

		const doctype = doc.doctype

		const fakeparent = $('<div>')
		super(doctype, fakeparent, true, undefined)
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

		// bugfix: `autoname_df.hidden` was changed, affecting all of the subsequent slide views
		this.fakeform_own_docfield_copy = frappe.meta.docfield_copy;
		frappe.meta.docfield_copy = (this.fakeform_previous_docfield_copy || {});
		delete this.fakeform_previous_docfield_copy;
	}

	/** Revert fakeform_destroy */
	fakeform_rebuild() {
		if (!this.fakeform_was_destroyed) return;
		delete this.fakeform_was_destroyed;

		this.watch_model_updates();
		this.refresh();

		this.fakeform_previous_docfield_copy = frappe.meta.docfield_copy
		frappe.meta.docfield_copy = (this.fakeform_own_docfield_copy || {});
		delete this.fakeform_own_docfield_copy;
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
		await super.save.apply(this, args)
		this.fakeform_saving = false
	}
	async savesubmit(...args) {
		this.fakeform_saving = true
		await super.savesubmit.apply(this, args)
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
