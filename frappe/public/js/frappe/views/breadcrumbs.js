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

	set_doctype_module: function(doctype, module) {
		localStorage["preferred_breadcrumbs:" + doctype] = module;
	},

	get_doctype_module: function(doctype) {
		return localStorage["preferred_breadcrumbs:" + doctype];
	},

	add: function(module, doctype, type) {
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

		frappe.breadcrumbs.all[frappe.breadcrumbs.current_page()] = obj;
		frappe.breadcrumbs.update();
	},

	current_page: function() {
		return frappe.get_route_str();
	},

	update: function() {
		var breadcrumbs = frappe.breadcrumbs.all[frappe.breadcrumbs.current_page()];
		let breadcrumbs_added = false;

		if(!frappe.visible_modules) {
			frappe.visible_modules = $.map(frappe.boot.allowed_modules, (m) => {
				return m.module_name;
			});
		}

		var $breadcrumbs = $("#navbar-breadcrumbs").empty();

		if(!breadcrumbs) {
			$("body").addClass("no-breadcrumbs");
			return;
		}

		if (breadcrumbs.type === 'Custom') {
			const html = `<li><a href="${breadcrumbs.route}">${__(breadcrumbs.label)}</a></li>`;
			$breadcrumbs.append(html);
			$("body").removeClass("no-breadcrumbs");
			breadcrumbs_added = true;
			return;
		}

		// get preferred module for breadcrumbs, based on sent via module
		var from_module = frappe.breadcrumbs.get_doctype_module(breadcrumbs.doctype);

		if (from_module) {
			breadcrumbs.module = from_module;
		} else if(frappe.breadcrumbs.preferred[breadcrumbs.doctype]!==undefined) {
			// get preferred module for breadcrumbs
			breadcrumbs.module = frappe.breadcrumbs.preferred[breadcrumbs.doctype];
		}

		if (!breadcrumbs_added && breadcrumbs.module) {
			if (frappe.breadcrumbs.module_map[breadcrumbs.module]) {
				breadcrumbs.module = frappe.breadcrumbs.module_map[breadcrumbs.module];
			}

			let current_module = breadcrumbs.module
			// Check if a desk page exists
			if (frappe.boot.module_page_map[breadcrumbs.module]) {
				breadcrumbs.module = frappe.boot.module_page_map[breadcrumbs.module];
			}

			if (frappe.get_module(current_module)) {
				// if module access exists
				const module_info = frappe.get_module(current_module)
				const label = module_info ? module_info.label : breadcrumbs.module;

				if(module_info && !module_info.blocked && frappe.visible_modules.includes(module_info.module_name)) {
					$(repl('<li><a href="/app/workspace/%(module)s">%(label)s</a></li>',
						{ module: breadcrumbs.module, label: __(label) }))
						.appendTo($breadcrumbs);
					breadcrumbs_added = true;
				}
			}
		}

		let set_list_breadcrumb = (doctype) => {
			if (doctype==="User"
				|| frappe.get_doc('DocType', doctype).issingle) {
				// no user listview for non-system managers and single doctypes
			} else if (breadcrumbs.doctype==="File") {
				const previous_route = frappe.route_history.length > 1 ? frappe.route_history[frappe.route_history.length - 2] : [];
				const last_folder = previous_route[previous_route.length - 1];
				const home_index = previous_route.indexOf("Home");
				const new_route = home_index ? previous_route.slice(home_index + 1) : [];
				if (new_route.length) {
					$(`<li><a href="/app/List/File/Home/${new_route.join("/")}">${__(last_folder)}</a></li>`)
						.appendTo($breadcrumbs);
				} else {
					$(`<li><a href="/app/List/File/Home">${__('Home')}</a></li>`)
						.appendTo($breadcrumbs);
				}
				breadcrumbs_added = true;
			} else {
				let route;
				const view = frappe.model.user_settings[breadcrumbs.doctype].last_view || 'Tree';
				if (view == 'Tree' && frappe.boot.treeviews.indexOf(breadcrumbs.doctype) !== -1) {
					route = view + '/' + breadcrumbs.doctype;
				} else if (view && view != 'Tree') {
					route = 'List/' + breadcrumbs.doctype + '/' + view
				} else {
					route = 'List/' + breadcrumbs.doctype;
				}
				$(`<li><a href="/app/${route}">${__(doctype)}</a></li>`)
					.appendTo($breadcrumbs);
				breadcrumbs_added = true;
			}
		}

		if (breadcrumbs.doctype && frappe.get_route()[0] === "Form") {
			set_list_breadcrumb(breadcrumbs.doctype);
		}

		if (breadcrumbs.doctype && frappe.get_route()[0] === "print") {
			set_list_breadcrumb(breadcrumbs.doctype);
			let docname = frappe.get_route()[2];
			let form_route = `Form/${breadcrumbs.doctype}/${docname}`;
			$(`<li><a href="#${form_route}">${docname}</a></li>`)
				.appendTo($breadcrumbs);
		}

		if (!breadcrumbs_added && frappe.get_prev_route() && frappe.get_prev_route()[1]) {
			const html = `<li><a href="#${frappe.get_prev_route().join("/")}">${__(frappe.get_prev_route()[1])}</a></li>`;
			$breadcrumbs.append(html);
			breadcrumbs_added = true;
			return;
		}

		$("body").removeClass("no-breadcrumbs");
	},

	rename: function(doctype, old_name, new_name) {
		var old_route_str = ["Form", doctype, old_name].join("/");
		var new_route_str = ["Form", doctype, new_name].join("/");
		frappe.breadcrumbs.all[new_route_str] = frappe.breadcrumbs.all[old_route_str];
		delete frappe.breadcrumbs.all[old_route_str];
	}

}

