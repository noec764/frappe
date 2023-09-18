// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

frappe.provide("frappe.model");

$.extend(frappe.model, {
	all_fieldtypes: [
		"Autocomplete",
		"Attach",
		"Attach Image",
		"Barcode",
		"Button",
		"Check",
		"Code",
		"Color",
		"Currency",
		"Data",
		"Date",
		"Datetime",
		"Duration",
		"Dynamic Link",
		"Float",
		"Geolocation",
		"Heading",
		"HTML",
		"HTML Editor",
		"Icon",
		"Image",
		"Int",
		"JSON",
		"Link",
		"Long Text",
		"Markdown Editor",
		"Password",
		"Percent",
		"Phone",
		"Read Only",
		"Rating",
		"Select",
		"Signature",
		"Small Text",
		"Table",
		"Table MultiSelect",
		"Text",
		"Text Editor",
		"Time",
	],

	no_value_type: [
		"Section Break",
		"Column Break",
		"Tab Break",
		"HTML",
		"Table",
		"Table MultiSelect",
		"Button",
		"Image",
		"Fold",
		"Heading",
	],

	layout_fields: ["Section Break", "Column Break", "Tab Break", "Fold"],

	std_fields_list: [
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"_user_tags",
		"_comments",
		"_assign",
		"_liked_by",
		"docstatus",
		"idx",
	],

	child_table_field_list: ["parent", "parenttype", "parentfield"],

	core_doctypes_list: [
		"DocType",
		"DocField",
		"DocPerm",
		"User",
		"Role",
		"Has Role",
		"Page",
		"Module Def",
		"Print Format",
		"Report",
		"Customize Form",
		"Customize Form Field",
		"Property Setter",
		"Custom Field",
		"Client Script",
	],

	restricted_fields: [
		"name",
		"parent",
		"creation",
		"modified",
		"modified_by",
		"parentfield",
		"parenttype",
		"file_list",
		"flags",
		"docstatus",
	],

	std_fields: [
		{ fieldname: "name", fieldtype: "Link", label: __("ID") },
		{ fieldname: "owner", fieldtype: "Link", label: __("Created By"), options: "User" },
		{ fieldname: "idx", fieldtype: "Int", label: __("Index") },
		{ fieldname: "creation", fieldtype: "Datetime", label: __("Created On") },
		{ fieldname: "modified", fieldtype: "Datetime", label: __("Last Updated On") },
		{
			fieldname: "modified_by",
			fieldtype: "Link",
			label: __("Last Updated By"),
			options: "User",
		},
		{ fieldname: "_user_tags", fieldtype: "Data", label: __("Tags") },
		{ fieldname: "_liked_by", fieldtype: "Data", label: __("Liked By") },
		{ fieldname: "_comments", fieldtype: "Text", label: __("Comments") },
		{ fieldname: "_assign", fieldtype: "Text", label: __("Assigned To") },
		{ fieldname: "docstatus", fieldtype: "Int", label: __("Document Status") },
	],

	numeric_fieldtypes: ["Int", "Float", "Currency", "Percent", "Duration"],

	std_fields_table: [{ fieldname: "parent", fieldtype: "Data", label: __("Parent") }],

	table_fields: ["Table", "Table MultiSelect"],

	new_names: {},
	events: {},
	user_settings: {},

	init: function () {
		// setup refresh if the document is updated somewhere else
		frappe.realtime.on("doc_update", function (data) {
			var doc = locals[data.doctype] && locals[data.doctype][data.name];

			if (doc) {
				// current document is dirty, show message if its not me
				if (
					frappe.get_route()[0] === "Form" &&
					cur_frm.doc.doctype === doc.doctype &&
					cur_frm.doc.name === doc.name
				) {
					if (data.modified !== cur_frm.doc.modified && !frappe.ui.form.is_saving) {
						if (!cur_frm.is_dirty()) {
							cur_frm.debounced_reload_doc();
						} else {
							doc.__needs_refresh = true;
							cur_frm.show_conflict_message();
						}
					}
				} else {
					if (!doc.__unsaved) {
						// no local changes, remove from locals
						frappe.model.remove_from_locals(doc.doctype, doc.name);
					} else {
						// show message when user navigates back
						doc.__needs_refresh = true;
					}
				}
			}
		});

		// Refresh doctype icons once
		this.get_doctype_icons();
	},

	is_value_type: function (fieldtype) {
		if (typeof fieldtype == "object") {
			fieldtype = fieldtype.fieldtype;
		}
		// not in no-value type
		return frappe.model.no_value_type.indexOf(fieldtype) === -1;
	},

	is_non_std_field: function (fieldname) {
		return ![...frappe.model.std_fields_list, ...frappe.model.child_table_field_list].includes(
			fieldname
		);
	},

	get_std_field: function (fieldname, ignore = false) {
		var docfield = $.map(
			[].concat(frappe.model.std_fields).concat(frappe.model.std_fields_table),
			function (d) {
				if (d.fieldname == fieldname) return d;
			}
		);
		if (!docfield.length) {
			//Standard fields are ignored in case of adding columns as a result of groupby
			if (ignore) {
				return { fieldname: fieldname };
			} else {
				frappe.msgprint(__("Unknown Column: {0}", [fieldname]));
			}
		}
		return docfield[0];
	},

	get_from_localstorage: function (doctype) {
		if (localStorage["_doctype:" + doctype]) {
			return JSON.parse(localStorage["_doctype:" + doctype]);
		}
	},

	set_in_localstorage: function (doctype, docs) {
		try {
			localStorage["_doctype:" + doctype] = JSON.stringify(docs);
		} catch (e) {
			// if quota is exceeded, clear local storage and set item
			console.warn("localStorage quota exceeded, clearing doctype cache");
			frappe.model.clear_local_storage();
			localStorage["_doctype:" + doctype] = JSON.stringify(docs);
		}
	},

	clear_local_storage: function () {
		for (var key in localStorage) {
			if (key.startsWith("_doctype:")) {
				localStorage.removeItem(key);
			}
		}
	},

	with_doctype: function (doctype, callback, async) {
		if (locals.DocType[doctype]) {
			callback && callback();
			return Promise.resolve();
		} else {
			let cached_timestamp = null;
			let cached_doc = null;

			let cached_docs = frappe.model.get_from_localstorage(doctype);

			if (cached_docs) {
				let cached_docs = JSON.parse(localStorage["_doctype:" + doctype]);
				cached_doc = cached_docs.filter((doc) => doc.name === doctype)[0];
				if (cached_doc) {
					cached_timestamp = cached_doc.modified;
				}
			}

			return frappe.call({
				method: "frappe.desk.form.load.getdoctype",
				type: "GET",
				args: {
					doctype: doctype,
					with_parent: 1,
					cached_timestamp: cached_timestamp,
				},
				async: async,
				callback: function (r) {
					if (r.exc) {
						frappe.msgprint(__("Unable to load: {0}", [__(doctype)]));
						throw "No doctype";
					}
					if (r.message == "use_cache") {
						frappe.model.sync(cached_doc);
					} else {
						frappe.model.set_in_localstorage(doctype, r.docs);
					}
					frappe.model.init_doctype(doctype);

					if (r.user_settings) {
						// remember filters and other settings from last view
						frappe.model.user_settings[doctype] = JSON.parse(r.user_settings);
						frappe.model.user_settings[doctype].updated_on = moment().toString();
					}
					callback && callback(r);
				},
			});
		}
	},

	init_doctype: function (doctype) {
		var meta = locals.DocType[doctype];
		for (const asset_key of [
			"__list_js",
			"__custom_list_js",
			"__calendar_js",
			"__map_js",
			"__tree_js",
			"__tour_js",
		]) {
			if (meta[asset_key]) {
				new Function(meta[asset_key])();
			}
		}

		if (meta.__templates) {
			$.extend(frappe.templates, meta.__templates);
		}
	},

	with_doc: function (doctype, name, callback) {
		return new Promise((resolve) => {
			if (!name) name = doctype; // single type
			if (
				locals[doctype] &&
				locals[doctype][name] &&
				frappe.model.get_docinfo(doctype, name)
			) {
				callback && callback(name);
				resolve(frappe.get_doc(doctype, name));
			} else {
				return frappe.call({
					method: "frappe.desk.form.load.getdoc",
					type: "GET",
					args: {
						doctype: doctype,
						name: name,
					},
					callback: function (r) {
						callback && callback(name, r);
						resolve(frappe.get_doc(doctype, name));
					},
				});
			}
		});
	},

	get_docinfo: function (doctype, name) {
		return (frappe.model.docinfo[doctype] && frappe.model.docinfo[doctype][name]) || null;
	},

	set_docinfo: function (doctype, name, key, value) {
		if (frappe.model.docinfo[doctype] && frappe.model.docinfo[doctype][name]) {
			frappe.model.docinfo[doctype][name][key] = value;
		}
	},

	get_shared: function (doctype, name) {
		return frappe.model.get_docinfo(doctype, name).shared;
	},

	get_server_module_name: function (doctype) {
		var dt = frappe.model.scrub(doctype);
		var module = frappe.model.scrub(locals.DocType[doctype].module);
		var app = frappe.boot.module_app[module];
		return app + "." + module + ".doctype." + dt + "." + dt;
	},

	scrub: function (txt) {
		return txt.replace(/ /g, "_").toLowerCase(); // use to slugify or create a slug, a "code-friendly" string
	},

	unscrub: function (txt) {
		return (txt || "").replace(/-|_/g, " ").replace(/\w*/g, function (keywords) {
			return keywords.charAt(0).toUpperCase() + keywords.substr(1).toLowerCase();
		});
	},

	can_create: function (doctype) {
		return frappe.boot.user.can_create.indexOf(doctype) !== -1;
	},

	can_select: function (doctype) {
		if (frappe.boot.user) {
			return frappe.boot.user.can_select.indexOf(doctype) !== -1;
		}
	},

	can_read: function (doctype) {
		if (frappe.boot.user) {
			return frappe.boot.user.can_read.indexOf(doctype) !== -1;
		}
	},

	can_write: function (doctype) {
		return frappe.boot.user.can_write.indexOf(doctype) !== -1;
	},

	can_get_report: function (doctype) {
		return frappe.boot.user.can_get_report.indexOf(doctype) !== -1;
	},

	can_delete: function (doctype) {
		if (!doctype) return false;
		return frappe.boot.user.can_delete.indexOf(doctype) !== -1;
	},

	can_cancel: function (doctype) {
		if (!doctype) return false;
		return frappe.boot.user.can_cancel.indexOf(doctype) !== -1;
	},

	has_workflow: function (doctype) {
		return frappe.get_list("Workflow", { document_type: doctype, is_active: 1 }).length;
	},

	is_submittable: function (doctype) {
		if (!doctype) return false;
		return locals.DocType[doctype] && locals.DocType[doctype].is_submittable;
	},

	is_table: function (doctype) {
		if (!doctype) return false;
		return locals.DocType[doctype] && locals.DocType[doctype].istable;
	},

	is_single: function (doctype) {
		if (!doctype) return false;
		return frappe.boot.single_types.indexOf(doctype) != -1;
	},

	is_tree: function (doctype) {
		if (!doctype) return false;
		return locals.DocType[doctype] && locals.DocType[doctype].is_tree;
	},

	is_fresh(doc) {
		// returns true if document has been recently loaded (5 seconds ago)
		return doc && doc.__last_sync_on && new Date() - doc.__last_sync_on < 5000;
	},

	can_import: function (doctype, frm, meta = null) {
		if (meta && !meta.allow_import) return false;

		// system manager can always import
		if (frappe.user_roles.includes("System Manager")) return true;

		if (frm) return frm.perm[0].import === 1;
		return frappe.boot.user.can_import.indexOf(doctype) !== -1;
	},

	can_export: function (doctype, frm) {
		// system manager can always export
		if (frappe.user_roles.includes("System Manager")) return true;

		if (frm) return frm.perm[0].export === 1;
		return frappe.boot.user.can_export.indexOf(doctype) !== -1;
	},

	can_print: function (doctype, frm) {
		if (frm) return frm.perm[0].print === 1;
		return frappe.boot.user.can_print.indexOf(doctype) !== -1;
	},

	can_email: function (doctype, frm) {
		if (frm) return frm.perm[0].email === 1;
		return frappe.boot.user.can_email.indexOf(doctype) !== -1;
	},

	can_share: function (doctype, frm) {
		let disable_sharing = cint(frappe.sys_defaults.disable_document_sharing);

		if (disable_sharing && frappe.session.user !== "Administrator") {
			return false;
		}

		if (frm) {
			return frm.perm[0].share === 1;
		}
		return frappe.boot.user.can_share.indexOf(doctype) !== -1;
	},

	can_set_user_permissions: function (doctype, frm) {
		// system manager can always set user permissions
		if (frappe.user_roles.includes("System Manager")) return true;

		if (frm) return frm.perm[0].set_user_permissions === 1;
		return frappe.boot.user.can_set_user_permissions.indexOf(doctype) !== -1;
	},

	has_value: function (dt, dn, fn) {
		// return true if property has value
		var val = locals[dt] && locals[dt][dn] && locals[dt][dn][fn];
		var df = frappe.meta.get_docfield(dt, fn, dn);

		let ret;
		if (frappe.model.table_fields.includes(df.fieldtype)) {
			ret = false;
			$.each(locals[df.options] || {}, function (k, d) {
				if (d.parent == dn && d.parenttype == dt && d.parentfield == df.fieldname) {
					ret = true;
					return false;
				}
			});
		} else {
			ret = !is_null(val);
		}
		return ret ? true : false;
	},

	get_list: function (doctype, filters) {
		var docsdict = locals[doctype] || locals[":" + doctype] || {};
		if ($.isEmptyObject(docsdict)) return [];
		return frappe.utils.filter_dict(docsdict, filters);
	},

	get_value: function (doctype, filters, fieldname, callback) {
		if (callback) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: doctype,
					fieldname: fieldname,
					filters: filters,
				},
				callback: function (r) {
					if (!r.exc) {
						callback(r.message);
					}
				},
			});
		} else {
			if (
				["number", "string"].includes(typeof filters) &&
				locals[doctype] &&
				locals[doctype][filters]
			) {
				return locals[doctype][filters][fieldname];
			} else {
				var l = frappe.get_list(doctype, filters);
				return l.length && l[0] ? l[0][fieldname] : null;
			}
		}
	},

	set_value: function (
		doctype,
		docname,
		fieldname,
		value,
		fieldtype,
		skip_dirty_trigger = false
	) {
		/* help: Set a value locally (if changed) and execute triggers */

		var doc;
		if ($.isPlainObject(doctype)) {
			// first parameter is the doc, shift parameters to the left
			doc = doctype;
			fieldname = docname;
			value = fieldname;
		} else {
			doc = locals[doctype] && locals[doctype][docname];
		}

		let to_update = fieldname;
		let tasks = [];
		if (!$.isPlainObject(to_update)) {
			to_update = {};
			to_update[fieldname] = value;
		}

		$.each(to_update, (key, value) => {
			if (doc && doc[key] !== value) {
				if (doc.__unedited && !(!doc[key] && !value)) {
					// unset unedited flag for virgin rows
					doc.__unedited = false;
				}

				doc[key] = value;
				tasks.push(() => frappe.model.trigger(key, value, doc, skip_dirty_trigger));
			} else {
				// execute link triggers (want to reselect to execute triggers)
				if (in_list(["Link", "Dynamic Link"], fieldtype) && doc) {
					tasks.push(() => frappe.model.trigger(key, value, doc, skip_dirty_trigger));
				}
			}
		});

		return frappe.run_serially(tasks);
	},

	on: function (doctype, fieldname, fn) {
		/* help: Attach a trigger on change of a particular field.
		To trigger on any change in a particular doctype, use fieldname as "*"
		*/
		/* example: frappe.model.on("Customer", "age", function(fieldname, value, doc) {
		  if(doc.age < 16) {
		   	frappe.msgprint("Warning, Customer must atleast be 16 years old.");
		    raise "CustomerAgeError";
		  }
		}) */
		frappe.provide("frappe.model.events." + doctype);
		if (!frappe.model.events[doctype][fieldname]) {
			frappe.model.events[doctype][fieldname] = [];
		}
		frappe.model.events[doctype][fieldname].push(fn);
	},

	trigger: function (fieldname, value, doc, skip_dirty_trigger = false) {
		const tasks = [];

		function enqueue_events(events) {
			if (!events) return;

			for (const fn of events) {
				if (!fn) continue;

				tasks.push(() => {
					const return_value = fn(fieldname, value, doc, skip_dirty_trigger);

					// if the trigger returns a promise, return it,
					// or use the default promise frappe.after_ajax
					if (return_value && return_value.then) {
						return return_value;
					} else {
						return frappe.after_server_call();
					}
				});
			}
		}

		if (frappe.model.events[doc.doctype]) {
			enqueue_events(frappe.model.events[doc.doctype][fieldname]);
			enqueue_events(frappe.model.events[doc.doctype]["*"]);
		}

		return frappe.run_serially(tasks);
	},

	get_doc: function (doctype, name) {
		if (!name) name = doctype;
		if ($.isPlainObject(name)) {
			var doc = frappe.get_list(doctype, name);
			return doc && doc.length ? doc[0] : null;
		}
		return locals[doctype] ? locals[doctype][name] : null;
	},

	get_children: function (doctype, parent, parentfield, filters) {
		let doc;
		if ($.isPlainObject(doctype)) {
			doc = doctype;
			filters = parentfield;
			parentfield = parent;
		} else {
			doc = frappe.get_doc(doctype, parent);
		}

		var children = doc[parentfield] || [];
		if (filters) {
			return frappe.utils.filter_dict(children, filters);
		} else {
			return children;
		}
	},

	clear_table: function (doc, parentfield) {
		for (const d of doc[parentfield] || []) {
			delete locals[d.doctype][d.name];
		}
		doc[parentfield] = [];
	},

	remove_from_locals: function (doctype, name) {
		this.clear_doc(doctype, name);
		if (frappe.views.formview[doctype]) {
			delete frappe.views.formview[doctype].frm.opendocs[name];
		}
	},

	clear_doc: function (doctype, name) {
		var doc = locals[doctype] && locals[doctype][name];
		if (!doc) return;

		var parent = null;
		if (doc.parenttype) {
			parent = doc.parent;
			var parenttype = doc.parenttype,
				parentfield = doc.parentfield;
		}
		delete locals[doctype][name];
		if (parent) {
			var parent_doc = locals[parenttype][parent];
			var newlist = [],
				idx = 1;
			$.each(parent_doc[parentfield], function (i, d) {
				if (d.name != name) {
					newlist.push(d);
					d.idx = idx;
					idx++;
				}
				parent_doc[parentfield] = newlist;
			});
		}
	},

	get_no_copy_list: function (doctype) {
		var no_copy_list = ["name", "amended_from", "amendment_date", "cancel_reason"];

		var docfields = frappe.get_doc("DocType", doctype).fields || [];
		for (var i = 0, j = docfields.length; i < j; i++) {
			var df = docfields[i];
			if (cint(df.no_copy)) no_copy_list.push(df.fieldname);
		}

		return no_copy_list;
	},

	delete_doc: function (doctype, docname, callback) {
		let title = docname;
		const title_field = frappe.get_meta(doctype).title_field;
		if (frappe.get_meta(doctype).autoname == "hash" && title_field) {
			const value = frappe.model.get_value(doctype, docname, title_field);
			if (value) {
				title = `${value} (${docname})`;
			}
		}
		frappe.confirm_danger(__("Permanently delete {0}?", [title.bold()]), function () {
			return frappe.call({
				method: "frappe.client.delete",
				args: {
					doctype: doctype,
					name: docname,
				},
				freeze: true,
				freeze_message: __("Deleting {0}...", [title]),
				callback: function (r, rt) {
					if (!r.exc) {
						frappe.utils.play_sound("delete");
						frappe.model.clear_doc(doctype, docname);
						if (callback) callback(r, rt);
					}
				},
			});
		});
	},

	rename_doc: function (doctype, docname, callback) {
		const message = __("Merge with existing");
		const warning = __("This cannot be undone");
		const merge_label = message + " <b>(" + warning + ")</b>";

		var d = new frappe.ui.Dialog({
			title: __("Rename {0}", [__(docname)]),
			fields: [
				{
					label: __("New Name"),
					fieldname: "new_name",
					fieldtype: "Data",
					reqd: 1,
					default: docname,
				},
				{ label: merge_label, fieldtype: "Check", fieldname: "merge" },
			],
		});

		d.set_primary_action(__("Rename"), function () {
			d.hide();
			var args = d.get_values();
			if (!args) return;
			return frappe.call({
				method: "frappe.rename_doc",
				freeze: true,
				freeze_message: __("Updating related fields..."),
				args: {
					doctype: doctype,
					old: docname,
					new: args.new_name,
					merge: args.merge,
				},
				btn: d.get_primary_btn(),
				callback: function (r, rt) {
					if (!r.exc) {
						$(document).trigger("rename", [
							doctype,
							docname,
							r.message || args.new_name,
						]);
						if (locals[doctype] && locals[doctype][docname])
							delete locals[doctype][docname];

						d.hide();
						if (callback) callback(r.message);
					}
				},
			});
		});
		d.show();
	},

	round_floats_in: function (doc, fieldnames) {
		if (!fieldnames) {
			fieldnames = frappe.meta.get_fieldnames(doc.doctype, doc.parent, {
				fieldtype: ["in", ["Currency", "Float"]],
			});
		}
		for (var i = 0, j = fieldnames.length; i < j; i++) {
			var fieldname = fieldnames[i];
			doc[fieldname] = flt(doc[fieldname], precision(fieldname, doc));
		}
	},

	validate_missing: function (doc, fieldname) {
		if (!doc[fieldname]) {
			frappe.throw(
				__("Please specify") +
					": " +
					__(frappe.meta.get_label(doc.doctype, fieldname, doc.parent || doc.name))
			);
		}
	},

	get_all_docs: function (doc) {
		const all = [doc];
		for (const fieldname in doc) {
			const children = doc[fieldname];
			if (fieldname.startsWith("_") || !Array.isArray(children)) {
				continue;
			}
			all.push(...children);
		}
		return all;
	},

	get_full_column_name: function (fieldname, doctype) {
		if (fieldname.includes("`tab")) return fieldname;
		return "`tab" + doctype + "`.`" + fieldname + "`";
	},

	is_numeric_field: function (fieldtype) {
		if (!fieldtype) return;
		if (typeof fieldtype === "object") {
			fieldtype = fieldtype.fieldtype;
		}
		return frappe.model.numeric_fieldtypes.includes(fieldtype);
	},

	set_default_views_for_doctype(doctype, frm) {
		this.get_views_of_doctype(doctype).then((default_views) => {
			frm.set_df_property("default_view", "options", default_views);
		});
	},

	async get_views_of_doctype(doctype) {
		await frappe.model.with_doctype(doctype);
		const meta = frappe.get_meta(doctype);

		if (meta.issingle || meta.istable) {
			return [];
		}

		const views = ["List", "Report", "Dashboard", "Kanban"];

		if (frappe.views.calendar[doctype] || meta.is_calendar_and_gantt) {
			// Allow Calendar view if there is a standard calendar view defined,
			// or if the checkbox "Is Calendar and Gantt" is checked with customizations.
			views.push("Calendar", "Planning");
		}
		// TODO: Gantt view is not working properly if no default calendar view is defined.
		// This means it is NOT possible to have a Gantt view for custom doctypes.
		if (frappe.views.calendar[doctype]) {
			views.push("Gantt");
		}
		if (meta.is_tree) {
			views.push("Tree");
		}
		if (meta.image_field) {
			views.push("Image");
		}
		if (doctype === "Communication" && frappe.boot.email_accounts.length) {
			views.push("Inbox");
		}
		if (
			(meta.fields.find((i) => i.fieldname === "latitude") &&
				meta.fields.find((i) => i.fieldname === "longitude")) ||
			meta.fields.find((i) => i.fieldname === "location" && i.fieldtype == "Geolocation")
		) {
			views.push("Map");
		}
		return views;
	},

	/**
	 * @returns {Promise<Record<string, string>>}
	 * Returns a map of doctype icons
	 * Icons are stored in localStorage to avoid multiple requests to the server.
	 * The result is returned immediately if the icons are already in localStorage,
	 * but the server is still queried to update the icons in the background (once).
	 */
	async get_doctype_icons() {
		const KEY = "frappe.model.get_doctype_icons";
		if (!frappe.model.doctype_icons) {
			// First call, try to get icons from localStorage
			frappe.model.doctype_icons = _get_in_cache();
			const do_later =
				window.requestIdleCallback || window.requestAnimationFrame || window.setTimeout;
			do_later(_fetch_icon_updates);
		}
		return frappe.model.doctype_icons;

		async function _fetch_icon_updates() {
			const last_updated = frappe.model.doctype_icons?.__last_updated;
			const res = await frappe.call({
				method: "frappe.desk.form.load.get_doctype_icons",
				args: { last_updated },
			});
			if (res.message && Object.keys(res.message).length > 0) {
				if (typeof frappe.model.doctype_icons !== "object") {
					frappe.model.doctype_icons = {};
				}
				// Perform a partial update
				for (const [doctype, icon] of Object.entries(res.message)) {
					// NOTE: __last_updated is a special key that is also stored in localStorage
					frappe.model.doctype_icons[doctype] = icon;
				}
				_set_in_cache(frappe.model.doctype_icons);
			}
		}

		/** @param {Record<string, string>} doctype_icons */
		function _set_in_cache(doctype_icons) {
			localStorage.setItem(KEY, JSON.stringify(doctype_icons));
		}

		/** @returns {Record<string, string>} */
		function _get_in_cache() {
			try {
				return JSON.parse(localStorage.getItem(KEY) || "{}") || {};
			} catch (e) {
				return {};
			}
		}
	},
});

// legacy
frappe.get_doc = frappe.model.get_doc;
frappe.get_children = frappe.model.get_children;
frappe.get_list = frappe.model.get_list;

var getchildren = function (doctype, parent, parentfield) {
	var children = [];
	$.each(locals[doctype] || {}, function (i, d) {
		if (d.parent === parent && d.parentfield === parentfield) {
			children.push(d);
		}
	});
	return children;
};
