// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

frappe.breadcrumbs = {
	all: {},

	preferred: {
		"File": "",
		"User": "Users",
		"Dashboard": "Customization",
		"Dashboard Chart": "Customization",
		"Dashboard Chart Source": "Customization",
		"Dashboard Card": "Customization",
		"Dashboard Card Source": "Customization"
	},

	module_map: {
		'Core': 'Settings',
		'Email': 'Settings',
		'Custom': 'Settings',
		'Workflow': 'Settings',
		'Printing': 'Settings',
		'Setup': 'Settings',
		'Event Streaming': 'Tools',
		'Automation': 'Tools',
		'Desk': 'Tools'
	},

	set_doctype_module(doctype, module) {
		localStorage["preferred_breadcrumbs:" + doctype] = module;
	},

	get_doctype_module(doctype) {
		return localStorage["preferred_breadcrumbs:" + doctype];
	},

	add(module, doctype, type) {
		let obj;
		if (typeof module === 'object') {
			obj = module;
		} else {
			obj = {
				module:module,
				doctype:doctype,
				type:type
			}
		}

		this.all[frappe.breadcrumbs.current_page()] = obj;
		this.update();
	},

	current_page() {
		return frappe.get_route_str();
	},

	update() {
		var breadcrumbs = this.all[frappe.breadcrumbs.current_page()];

		this.clear();
		if(!breadcrumbs) return this.toggle(false);

		if (breadcrumbs.type === 'Custom') {
			this.set_custom_breadcrumbs(breadcrumbs);
		} else {
			// workspace
			this.set_workspace_breadcrumb(breadcrumbs);

			// form / print
			const view = frappe.get_route()[0].toLowerCase();
			if (breadcrumbs.doctype && ["print", "form"].includes(view)) {
				this.set_list_breadcrumb(breadcrumbs);
				this.set_form_breadcrumb(breadcrumbs, view);
			}
		}

		this.toggle(true);
	},

	set_custom_breadcrumbs(breadcrumbs) {
		const html = `<li><a href="${breadcrumbs.route}">${breadcrumbs.label}</a></li>`;
		this.$breadcrumbs.append(html);
	},

	set_workspace_breadcrumb(breadcrumbs) {
		// get preferred module for breadcrumbs, based on sent via module

		if (!breadcrumbs.workspace) {
			this.set_workspace(breadcrumbs);
		}

		if (breadcrumbs.workspace) {
			if(!breadcrumbs.module_info.blocked && frappe.visible_modules.includes(breadcrumbs.module_info.module_name)) {
				$(repl('<li><a href="/app/space/%(module)s">%(label)s</a></li>',
					{ module: breadcrumbs.workspace, label: __(breadcrumbs.workspace) }))
					.appendTo(this.$breadcrumbs);
			}
		}

	},

	set_workspace(breadcrumbs) {
		// try and get module from doctype or other settings
		// then get the workspace for that module

		this.setup_modules();
		var from_module = this.get_doctype_module(breadcrumbs.doctype);

		if (from_module) {
			breadcrumbs.module = from_module;
		} else if(this.preferred[breadcrumbs.doctype]!==undefined) {
			// get preferred module for breadcrumbs
			breadcrumbs.module = this.preferred[breadcrumbs.doctype];
		}

		if (breadcrumbs.module) {
			if (this.module_map[breadcrumbs.module]) {
				breadcrumbs.module = this.module_map[breadcrumbs.module];
			}

			breadcrumbs.module_info = frappe.get_module(breadcrumbs.module);

			// set workspace
			if (breadcrumbs.module_info && frappe.boot.module_page_map[breadcrumbs.module]) {
				breadcrumbs.workspace = frappe.boot.module_page_map[breadcrumbs.module];
			}
		}
	},

	set_list_breadcrumb(breadcrumbs) {
		const doctype = breadcrumbs.doctype;
		if ((doctype==="User" && !frappe.user.has_role('System Manager'))
			|| frappe.get_doc('DocType', doctype).issingle) {
			// no user listview for non-system managers and single doctypes
		} else {
			let route;
			const doctype_route = frappe.router.slug(frappe.router.doctype_layout || doctype);
			if (frappe.boot.treeviews.indexOf(doctype) !== -1) {
				let view = frappe.model.user_settings[doctype].last_view || 'Tree';
				route = `${doctype_route}/view/${view}`;
			} else {
				route = doctype_route;
			}
			$(`<li><a href="/app/${route}">${doctype}</a></li>`)
				.appendTo(this.$breadcrumbs)
		}
	},

	set_form_breadcrumb(breadcrumbs, view) {
		const doctype = breadcrumbs.doctype;
		const docname = frappe.get_route()[2];
		let form_route = `/app/${frappe.router.slug(doctype)}/${docname}`;
		$(`<li><a href="${form_route}">${docname}</a></li>`)
			.appendTo(this.$breadcrumbs);

		if (view === "form") {
			let last_crumb = this.$breadcrumbs.find('li').last();
			last_crumb.addClass('disabled');
			last_crumb.css("cursor", "copy");
			last_crumb.click((event) => {
				event.stopImmediatePropagation();
				frappe.utils.copy_to_clipboard(last_crumb.text());
			});
		}
	},

	setup_modules() {
		if(!frappe.visible_modules) {
			frappe.visible_modules = $.map(frappe.boot.allowed_modules, (m) => {
				return m.module_name;
			});
		}
	},

	rename(doctype, old_name, new_name) {
		var old_route_str = ["Form", doctype, old_name].join("/");
		var new_route_str = ["Form", doctype, new_name].join("/");
		this.all[new_route_str] = this.all[old_route_str];
		delete frappe.breadcrumbs.all[old_route_str];
		this.update();
	},

	clear() {
		this.$breadcrumbs = $("#navbar-breadcrumbs").empty();
	},

	toggle(show) {
		if (show) {
			$("body").addClass("no-breadcrumbs");
		} else {
			$("body").removeClass("no-breadcrumbs");
		}
	}

}

