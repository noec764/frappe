// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt
import { Calendar } from "@fullcalendar/core";
import interactionPlugin, { Draggable } from "@fullcalendar/interaction";
import adaptivePlugin from "@fullcalendar/adaptive";
import resourceTimelinePlugin from "@fullcalendar/resource-timeline";
import resourceTimeGridPlugin from "@fullcalendar/resource-timegrid";

frappe.provide("frappe.views.calendar");

const day_map = {
	Sunday: 0,
	Monday: 1,
	Tuesday: 2,
	Wednesday: 3,
	Thursday: 4,
	Friday: 5,
	Saturday: 6,
};

frappe.views.PlanningView = class PlanningView extends frappe.views.ListView {
	static load_last_view() {
		const route = frappe.get_route();
		if (route.length === 3) {
			const doctype = route[1];
			const user_settings = frappe.get_user_settings(doctype)["Calendar"] || {};
			route.push(user_settings.calendar || "default");
			frappe.set_route(route);
			return true;
		} else {
			return false;
		}
	}

	toggle_result_area() {}

	get view_name() {
		// __("Planning")
		return "Planning";
	}

	setup_page() {
		this.hide_page_form = false;
		super.setup_page();
	}

	setup_defaults() {
		super.setup_defaults();
		this.page_title = __("{0} Planning", [this.page_title]);
		this.calendar_settings = frappe.views.calendar[this.doctype] || {};
		this.calendar_name = frappe.get_route()[3];
		this.resource_section = null;
		this.resource = null;
		this.resource_label = null;
		this.setup_resources();
	}

	setup_resources() {
		frappe
			.call({
				method: "frappe.desk.calendar.get_resources_for_doctype",
				args: {
					doctype: this.doctype,
				},
			})
			.then((res) => {
				const resources = this.calendar_settings.hasOwnProperty("excluded_resources")
					? res.message.filter(
							(r) => !this.calendar_settings.excluded_resources.includes(r.id)
					  )
					: res.message;
				if (!this.resource) {
					if (
						this.calendar_settings.default_resource &&
						resources
							.map((r) => r.id)
							.includes(this.calendar_settings.default_resource)
					) {
						this.resource = this.calendar_settings.default_resource;
						this.resource_label = resources.filter(
							(r) => r.id == this.calendar_settings.default_resource
						)[0].title;
					} else {
						this.resource = resources[0].id;
						this.resource_label = resources[0].title;
					}
				}
				this.setup_dropdown_for_resources(resources);
			});
	}

	before_refresh() {
		super.before_refresh();
		if (
			this.calendar_settings.filters &&
			this.calendar_settings.filters.length > 0 &&
			Array.isArray(this.calendar_settings.filters[0])
		) {
			this.filter_area.add(this.calendar_settings.filters);
		}
	}

	setup_view() {
		this.sort_selector.wrapper.hide();
	}

	before_render() {
		super.before_render();
		this.save_view_user_settings({
			last_calendar: this.calendar_name,
		});
	}

	render() {
		if (this.calendar) {
			this.calendar.refresh();
			return;
		}

		this.load_lib
			.then(() => this.get_calendar_preferences())
			.then((options) => {
				this.calendar = new frappe.views.Planning(options);
			});
	}

	get_calendar_preferences() {
		const options = {
			doctype: this.doctype,
			parent: this.$result,
			page: this.page,
			list_view: this,
		};
		const calendar_name = this.calendar_name;

		return new Promise((resolve) => {
			if (calendar_name.toLowerCase() === "default") {
				Object.assign(options, frappe.views.calendar[this.doctype]);
				resolve(options);
			} else {
				frappe.model.with_doc("Calendar View", calendar_name, () => {
					const doc = frappe.get_doc("Calendar View", calendar_name);
					if (!doc) {
						frappe.show_alert(
							__("{0} is not a valid Calendar. Redirecting to default Planning.", [
								calendar_name.bold(),
							])
						);
						frappe.set_route("List", this.doctype, "Planning", "default");
						return;
					}
					Object.assign(options, {
						field_map: {
							id: "name",
							start: doc.start_date_field,
							end: doc.end_date_field,
							title: doc.subject_field,
							allDay: doc.all_day_field,
							status: doc.status_field,
							color: doc.color_field,
							rrule: doc.recurrence_rule_field,
						},
						calendar_defaults: {
							slots_start_time: doc.daily_minimum_time,
							slots_end_time: doc.daily_maximum_time,
							first_day: doc.first_day ? day_map[doc.first_day] : null,
							display_event_time: doc.display_event_time == 1 ? true : false,
							display_event_end: doc.display_event_end == 1 ? true : false,
						},
					});

					resolve(options);
				});
			}
		});
	}

	get required_libs() {}

	setup_dropdown_for_resources(resources) {
		if (!this.list_sidebar || this.resource_section) return;

		const views_wrapper = this.list_sidebar.sidebar.find(".views-section");

		this.resource_section = $(`<div class="sidebar-section resource-section">
			<li class="sidebar-label">${__("Group Planning By")}</li>
			<div class="current-resources">
				<li class="list-link">
					<a class="btn btn-default btn-sm list-sidebar-button"
						data-toggle="dropdown"
						aria-haspopup="true"
						aria-expanded="false"
						href="#"
					>
						<span class="selected-resource ellipsis">${__("Select a Resource")}</span>
						<span>
							<svg class="icon icon-xs">
								<use href="#icon-select"></use>
							</svg>
						</span>
					</a>
					<ul class="dropdown-menu list-resources-dropdown" role="menu">
						<div class="dropdown-search">
							<input type="text" placeholder=${__("Search")} data-element="search" class="form-control input-xs">
						</div>
						<div class="resources-result">
						</div>
					</ul>
				</li>
			</div>
		</div>`).insertAfter(views_wrapper);

		const resources_list = $(
			frappe.render_template("resource_dropdown", { resources: resources })
		).on("click", ".resources-link", (e) => {
			const value = $(e.currentTarget).attr("data-value");
			const label = $(e.currentTarget).attr("data-label");
			this.resource_section.find(".selected-resource").html(__(label));
			this.resource = value;
			this.resource_label = label;
			this.calendar.fullcalendar.setOption(
				"resourceAreaColumns",
				this.calendar.get_resource_area_columns()
			);
			this.calendar.refresh();
		});

		this.resource_section
			.find(".list-resources-dropdown .resources-result")
			.html(resources_list);
		frappe.utils.setup_search(
			this.resource_section.find(".list-resources-dropdown"),
			".resources-link",
			".resources-label"
		);
	}
};

frappe.views.Planning = class frappePlanning {
	constructor(options) {
		$.extend(this, options);
		this.fullcalendar = null;
		this.calendar_defaults =
			this.calendar_defaults && Object.keys(this.calendar_defaults)
				? this.calendar_defaults
				: {};
		this.sidebar_menu = this.list_view.list_sidebar?.sidebar.find(".sidebar-menu");

		this.field_map = this.field_map || {
			id: "name",
			start: "start",
			end: "end",
			allDay: "all_day",
			convertToUserTz: "convert_to_user_tz",
		};

		Object.assign(this.field_map, { resourceId: this.list_view.resource });
		this.get_default_options();
	}

	get_default_options() {
		return new Promise((resolve) => {
			let initialView = localStorage.getItem("cal_initialView");
			let weekends = localStorage.getItem("cal_weekends");
			let defaults = {
				initialView:
					initialView &&
					["timeGridDay", "timeGridWeek", "dayGridMonth"].includes(initialView)
						? initialView
								.replace("timeGrid", "resourceTimeline")
								.replace("dayGrid", "resourceTimeline")
						: "resourceTimelineMonth",
				weekends: weekends ? weekends : true,
			};
			resolve(defaults);
		}).then((defaults) => {
			Object.assign(this.calendar_defaults, defaults);
			this.make_page();
			this.setup_options(this.calendar_defaults);
			this.make();
			this.setup_view_mode_button(this.calendar_defaults);
			this.bind();
		});
	}

	make_page() {
		const me = this;

		// add links to other calendars
		me.page.clear_user_actions();
		$.each(frappe.boot.calendars, function (i, doctype) {
			if (frappe.model.can_read(doctype)) {
				me.page.add_menu_item(__(doctype), function () {
					frappe.set_route("List", doctype, "Planning");
				});
			}
		});

		$(this.parent).on("show", function () {
			me.fullcalendar.refetchEvents();
		});
	}

	make() {
		this.$wrapper = this.parent;
		this.$cal = $("<div>").appendTo(this.$wrapper);
		this.footnote_area = frappe.utils.set_footnote(
			this.footnote_area,
			this.$wrapper,
			__("Select or drag across time slots to create a new event.")
		);
		this.footnote_area.css({ "border-top": "0px" });

		this.fullcalendar = new Calendar(this.$cal[0], this.cal_options);
		this.fullcalendar.render();

		this.$wrapper.find(".fc-today-button").prepend(frappe.utils.icon("today"));
	}

	setup_view_mode_button(defaults) {
		const me = this;
		$(me.footnote_area).find(".btn-weekend").detach();
		const btnTitle = defaults.weekends ? __("Hide Weekends") : __("Show Weekends");
		const btn = `<button class="btn btn-default btn-xs btn-weekend">${btnTitle}</button>`;
		me.footnote_area.append(btn);
	}

	set_localStorage_option(option, value) {
		localStorage.removeItem(option);
		localStorage.setItem(option, value);
	}

	bind() {
		const me = this;
		// const btn_group = me.$wrapper.find(".fc-button-group");
		// btn_group.on("click", ".fc-button", function () {
		// 	const value = $(this).hasClass("fc-timeGridWeek-button")
		// 		? "timeGridWeek"
		// 		: $(this).hasClass("fc-timeGridDay-button")
		// 			? "timeGridDay"
		// 			: "dayGridMonth";
		// 	me.set_localStorage_option("cal_initialView", value);
		// });

		me.$wrapper.on("click", ".btn-weekend", function () {
			me.cal_options.weekends = !me.cal_options.weekends;
			me.fullcalendar.setOption("weekends", me.cal_options.weekends);
			me.set_localStorage_option("cal_weekends", me.cal_options.weekends);
			me.setup_view_mode_button(me.cal_options);
		});
	}

	get_system_datetime(date) {
		date._offset = moment(date).tz(frappe.sys_defaults.time_zone)._offset;
		return frappe.datetime.convert_to_system_tz(date);
	}

	setup_options(defaults) {
		const me = this;

		this.cal_options = {
			locale: frappe.get_cookie("preferred_language") || frappe.boot.lang || "en",
			plugins: [
				resourceTimelinePlugin,
				interactionPlugin,
				adaptivePlugin,
				resourceTimeGridPlugin,
			],
			schedulerLicenseKey: frappe.boot.fullcalendar_scheduler_licence_key,
			initialView: defaults.initialView,
			headerToolbar: {
				left: "resourceTimelineDay,resourceTimelineWeek,resourceTimelineMonth resourceTimeGridDay",
				center: "prev,title,next",
				right: "today",
			},
			height: "auto",
			editable: true,
			selectable: true,
			selectMirror: true,
			forceEventDuration: true,
			weekends: defaults.weekends,
			nowIndicator: true,
			resourceAreaColumns: this.get_resource_area_columns(),
			resources: function (parameters, callback) {
				return frappe
					.xcall(me.get_resources_method || "frappe.desk.calendar.get_resource_ids", {
						doctype: me.doctype,
						resource: me.list_view.resource,
					})
					.then((r) => {
						callback(r);
					});
			},
			events: function (parameters, callback) {
				return frappe
					.xcall(
						me.get_events_method || "frappe.desk.calendar.get_events",
						me.get_args(parameters.start, parameters.end)
					)
					.then((r) => {
						let events = r || [];
						events = me.prepare_events(events);
						callback(events);
					});
			},
			eventClick: function (info) {
				// edit event description or delete
				const doctype =
					info.event.doctype || info.event.extendedProps.doctype || me.doctype;
				if (frappe.model.can_read(doctype)) {
					frappe.set_route("Form", doctype, info.event.id);
				}
			},
			eventDrop: function (info) {
				me.update_event(info);
				$(info.el).tooltip("dispose");
			},
			eventResize: function (info) {
				me.update_event(info);
				$(info.el).tooltip("dispose");
			},
			select: function (selectionInfo) {
				const event = frappe.model.get_new_doc(me.doctype);

				event[me.field_map.start] = me.get_system_datetime(selectionInfo.start);

				if (me.field_map.end) {
					event[me.field_map.end] = me.get_system_datetime(selectionInfo.end);
				}

				if (me.field_map.allDay) {
					event[me.field_map.allDay] = selectionInfo.allDay;

					if (selectionInfo.allDay) {
						const last_second = moment(selectionInfo.end).subtract(1, "seconds");
						event[me.field_map.end] = me.get_system_datetime(last_second.toDate());
					}
				}

				if (me.list_view.resource) {
					event[me.list_view.resource] = selectionInfo.resource.id;
				}

				frappe.set_route("Form", me.doctype, event.name);
			},
			dateClick: function (info) {
				if (info.view.type === "resourceTimelineMonth") {
					me.fullcalendar.changeView("resourceTimelineDay");
					me.fullcalendar.gotoDate(info.date);

					// update "active view" btn
					me.$wrapper.find(".fc-dayGridMonth-button").removeClass("active");
					me.$wrapper.find(".fc-timeGridDay-button").addClass("active");
				}
				return false;
			},
			buttonText: {
				today: __("Today"),
				month: __("Month"),
				week: __("Week"),
				day: __("Day"),
				resourceTimeGridDay: __("Vertical"),
			},
			eventDidMount: function (info) {
				$(info.el).tooltip({
					title: frappe.utils.html2text(info.event.title),
					placement: "auto",
				});
			},
			eventWillUnmount: function (info) {
				$(info.el).tooltip("dispose");
			},
			firstDay: defaults.first_day ?? frappe.datetime.get_first_day_of_the_week_index(),
			slotMinTime: defaults.slots_start_time || "06:00:00",
			slotMaxTime: defaults.slots_end_time || "22:00:00",
			expandRows: true,
			refetchResourcesOnNavigate: true,
			resourceAreaWidth: "20%",
			slotMinWidth: 100,
		};

		if (this.options) {
			$.extend(this.cal_options, this.options);
		}
	}

	get_args(start, end) {
		return {
			doctype: this.doctype,
			start: this.get_system_datetime(start),
			end: this.get_system_datetime(end),
			filters: this.list_view.filter_area.get(),
			field_map: this.field_map,
			fields: [this.list_view.resource],
		};
	}

	refresh() {
		Object.assign(this.field_map, { resourceId: this.list_view.resource });
		this.fullcalendar.refetchResources();
		this.fullcalendar.refetchEvents();
	}

	prepare_events(events) {
		const me = this;
		return (events || []).map((d) => {
			d.id = d.name;
			d.editable = frappe.model.can_write(d.doctype || me.doctype);
			d.classNames = d.classNames || [];

			// do not allow submitted/cancelled events to be moved / extended
			if (d.docstatus && d.docstatus > 0) {
				d.editable = false;
			}

			$.each(me.field_map, function (target, source) {
				d[target] = d[source];
			});

			if (!me.field_map.allDay && !me.no_all_day) {
				d.allDay = true;
			}
			if (!me.field_map.convertToUserTz) d.convertToUserTz = true;

			// convert to user tz
			if (d.convertToUserTz) {
				d.start = frappe.datetime.convert_to_user_tz(d.start);
				d.end = frappe.datetime.convert_to_user_tz(d.end);
			}

			// show event on single day if start or end date is invalid
			if (!frappe.datetime.validate(d.start) && d.end) {
				d.start = frappe.datetime.add_days(d.end, -1);
			}

			if (d.start && !frappe.datetime.validate(d.end)) {
				d.end = frappe.datetime.add_days(d.start, 1);
			}

			me.fix_end_date_for_event_render(d);
			me.prepare_colors(d);

			d.title = frappe.utils.html2text(d.title);

			return d;
		});
	}

	prepare_colors(d) {
		let color;

		color = d.color;
		if (!frappe.ui.color.validate_hex(color) || !color) {
			color = color
				? frappe.ui.color.get_color_shade(color, "default")
				: undefined || frappe.ui.color.get("blue", "default");
		}
		d.backgroundColor = color;
		d.borderColor = color;
		d.textColor = frappe.ui.color.get_contrast_color(color);

		return d;
	}

	update_event(info) {
		var me = this;
		let firstEvent = info.event;
		if (info.relatedEvents && info.relatedEvents[0]) {
			// let ok = false;
			// const dialog = new frappe.ui.Dialog();
			// me.refresh();
			const maybeFirst = info.relatedEvents[0];
			if (maybeFirst.start < firstEvent.start) {
				firstEvent = maybeFirst;
			}
		}
		frappe.model.remove_from_locals(
			firstEvent.extendedProps?.doctype || me.doctype,
			firstEvent.id
		);

		const updated_args = me.get_update_args(firstEvent);
		if (this.field_map.resourceId) {
			updated_args.args[this.field_map.resourceId] =
				info.newResource?.id || info.event.extendedProps[this.field_map.resourceId];
		}

		return frappe.call({
			method: me.update_event_method || "frappe.desk.calendar.update_event",
			args: updated_args,
			callback: function (r) {
				if (r.exc) {
					frappe.show_alert(__("Unable to update event"));
					info.revert();
				} else {
					if (firstEvent.extendedProps?.rrule) {
						// Fetch some instances of the recurring event that might
						// be missing because they were out of the displayed range
						// but now should be displayed because the recurring event
						// was moved to an earlier date.
						me.refresh();
					}
				}
			},
			error: function () {
				info.revert();
			},
		});
	}

	get_update_args(event) {
		const me = this;
		let args = {
			name: event.id,
		};

		args[this.field_map.start] = me.get_system_datetime(event.start);

		if (this.field_map.allDay) args[this.field_map.allDay] = event.allDay;

		if (this.field_map.end) {
			if (!event.end) {
				event.end = event.start.add(1, "hour");
			}

			args[this.field_map.end] = me.get_system_datetime(event.end);

			if (args[this.field_map.allDay]) {
				args[this.field_map.end] = moment(event.end).subtract(1, "seconds");
			}
		}

		args.doctype = event.doctype || this.doctype;

		return { args: args, field_map: this.field_map };
	}

	fix_end_date_for_event_render(event) {
		if (event.allDay) {
			// We use inclusive end dates. This workaround fixes the rendering of events
			event.end = event.end
				? this.get_system_datetime(moment(event.end).add(1, "day"))
				: null;
		}
	}

	get_resource_area_columns() {
		return [
			{
				headerContent: __(this.list_view.resource_label),
			},
		];
	}
};
