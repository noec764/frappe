// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: MIT. See LICENSE

frappe.provide("frappe.ui");

frappe.ui.Slide = class Slide {
	/**
	 * @param {{
	 * 	parent_slides: frappe.ui.Slides,
	 *	parent_form: frappe.ui.form.Form,
	 * 	parent: HTMLElement|JQuery,
	 * 	title: string,
	 * 	subtitle?: string,
	 * 	help?: string,
	 * 	image_src?: string,
	 * }} settings
	 */
	constructor(settings = {}) {
		/** List of required fields */
		this.reqd_fields = [];

		/** @type {frappe.ui.Slides} */
		this.parent_slides = settings.parent_slides;

		this.parent = settings.parent;

		/** The slide was shown at least once. */
		this.seen = false;
		/** The "next" button was clicked on this slide. */
		this.done = false;

		Object.assign(this, settings);
		this.setup();
	}

	// Overridable lifecycle methods
	before_make(self) { }
	onload(self) { }
	after_load(self) { }
	before_show(self) { }
	before_hide(self) { }

	/** Called everytime a required field is updated. */
	on_slide_update(self) { }

	/**
	 * Called on refresh when `this.done` is true.
	 * `this.done` is set to true when clicking on the Next button.
	 */
	setup_done_state(self) { }

	/**
	 * Called when click on Next/Finish (going to next slide or completing slide view).
	 * Not called when going back or for random slide changes (e.g. when clicking on progress dots).
	 * @returns {Promise<boolean>|boolean} `true` if slide is valid
	 */
	validate(self) { return true }

	/**
	 * Indicates whether the slide should be skipped.
	 * @returns {boolean} `true` to skip slide
	 */
	should_skip(self) { return false }

	setup() {
		this.$wrapper = $('<div class="slide-wrapper hidden"></div>')
			.attr({ "data-slide-id": this.id, "data-slide-name": this.name })
			.appendTo(this.parent);
	}

	// Make has to be called manually, to account for on-demand use cases
	make() {
		if (this.made) {
			console.warn('frappe.ui.Slide: called make() but slide is already made, skipping.');
			return;
		}

		this.before_make&&this.before_make(this);

		const subtitle = this.subtitle&&`<h2 class="subtitle text-muted">${this.subtitle}</h2>`;

		this.$body = $(`<div class="slide-body">
			<div class="slide-title-section content text-center">
				<h1 class="title slide-title">${__(this.title)}</h1>
				${subtitle || ""}
			</div>
			<div class="form-wrapper">
				<div class="form"></div>
				<div class="add-more text-center" style="margin-top: 5px;">
					<button class="form-more-btn hide btn btn-default btn-xs">
						<span>${__("Add More")}</span>
					</button>
				</div>
			</div>
		</div>`).appendTo(this.$wrapper);

		this.$content = this.$body.find(".content");
		this.$form = this.$body.find(".form");
		this.$form_wrapper = this.$body.find(".form-wrapper");

		if (this.image_src) {
			this.$content.append($(`<img src="${this.image_src}" style="margin: 20px;">`));
		}
		if (this.help) {
			this.$content.append($(`<p class="slide-help">${__(this.help)}</p>`));
		}

		this.reqd_fields = [];

		this.setup_form();
		this.refresh();
		this.check_reqd_fields();
		this.set_form_values(this.parent_slides.values).then(() => {
			this.after_load&&this.after_load(this);
		})
		this.made = true;
	}

	refresh() {
		if (this.form && this.parent_slides.values_is_doc) {
			this.form.refresh(); // fix missing layout refresh
		}
		this.render_parent_dots();
		if (this.done) {
			this.setup_done_state&&this.setup_done_state(this);
		}
	}

	setup_form() {
		const fieldGroupOptions = {
			fields: this.parent_slides.values_is_doc ? this.fields : this.get_atomic_fields(),
			body: this.$form[0],
			no_submit_on_enter: true,
			doc: this.doc,
			values: this.parent_slides.values,
		};
		if (this.parent_form) {
			Object.assign(fieldGroupOptions, {
				frm: this.parent_form,
				doctype: this.parent_form.doctype,
				docname: this.parent_form.docname,
				doc: this.parent_form.doc,
			});
		}

		this.form = new frappe.ui.FieldGroup(fieldGroupOptions);
		this.form.make();

		if (this.add_more) {
			this.bind_more_button();
		}

		this.onload&&this.onload(this);

		this.set_reqd_fields();
		this.bind_reqd_fields_update();
	}

	set_form_values(values) {
		// bug fix: values were not correctly set
		return this.form.set_values(values).then(async () => {
			// await new Promise(f => setTimeout(f, 60));
			await this.form.set_values(values);
			this.refresh();
			this.check_reqd_fields();
		})
	}

	get_state() {
		const seen = this.seen;
		const done = this.done;
		const error = this.last_validation_result === false; // not error if undefined (unknown) or true (valid)
		const skip = Boolean(this.should_skip && this.should_skip(this));
		return { seen, done, error, skip };
	}

	// Form methods
	get_atomic_fields() {
		var fields = JSON.parse(JSON.stringify(this.fields));
		if (this.add_more) {
			this.count = 1;
			fields = fields.map((field, i) => {
				if (field.fieldname) {
					field.fieldname += '_1';
				}
				if (i === 1 && this.mandatory_entry) {
					field.reqd = 1;
				}
				if (!field.static) {
					if (field.label) field.label;
				}
				return field;
			});
		}
		return fields;
	}

	set_reqd_fields() {
		const dict = this.form.fields_dict;
		this.reqd_fields = [];
		Object.keys(dict).map(key => {
			if (dict[key].df.reqd) {
				this.reqd_fields.push(dict[key]);
			}
		});
	}

	get_values(force_get_all = false) {
		if (this.made && this.form) {
			if (force_get_all) {
				const v = {};
				for (const df of this.form.fields) {
					const n = df.fieldname;
					if (n) { v[n] = this.form.get_value(n); }
				}
				return v;
			} else {
				const ignore_form_errors = true;
				return this.form.get_values(ignore_form_errors);
			}
		}
		return {};
	}

	/**
	 * Computed getter, retrieve all values from all slides
	 */
	get values() {
		return this.parent_slides.get_values(); // return all values
	}

	get doc() {
		return this.parent_slides.doc;
	}

	has_errors(ignore_form_errors = false) {
		if (this.made && this.form) {
			const values = this.form.get_values(ignore_form_errors);
			if (values === null) {
				this.last_validation_result = false;
				return true;
			}
			if (this.validate) {
				let valid = this.validate(this);
				if (valid !== undefined && typeof valid.then === 'function') valid = true;
				this.last_validation_result = Boolean(valid);
				if (!valid) {
					return true;
				}
			}
		}
		return false;
	}

	bind_more_button() {
		this.$more = this.$body.find('.form-more-btn');
		this.$more.removeClass('hide')
			.on('click', () => {
				this.count++;
				var fields = JSON.parse(JSON.stringify(this.fields));

				this.form.add_fields(fields.map(field => {
					if (field.fieldname) field.fieldname += '_' + this.count;
					if (!field.static) {
						if (field.label) field.label;
					}
					field.reqd = 0;
					return field;
				}));

				if (this.count === this.max_count) {
					this.$more.addClass('hide');
				}
			});
	}

	bind_reqd_fields_update() {
		const me = this;
		this.reqd_fields.map((field) => {
			field.$wrapper.on('change input click', function(e) {
				me.on_reqd_field_update(field, e);
			});
			field.$wrapper.on('keydown', 'input', e => {
				if (e.key == 'Enter') {
					me.on_reqd_field_update(field, e);
				}
			});

			// fix: empty required fields are missing red border on blur
			// field.$wrapper.on('blur', 'input', e => {
			// 	if (field.has_input) setTimeout(() => field.refresh(), 200);
			// });
		});
	}

	on_reqd_field_update(field, event) {
		this.check_reqd_fields();
		this.on_slide_update&&this.on_slide_update(this);
	}

	check_reqd_fields() {
		const empty_fields = this.reqd_fields.filter((field) => {
			return !field.get_value(); // bug with checkboxes?
		});
		if (this.parent_slides.unidirectional) {
			this.parent_slides.enable_disable_action_buttons(empty_fields.length > 0);
		}
		return empty_fields;
	}

	show_slide() {
		this.seen = true;
		this.$wrapper.removeClass("hidden");
		this.before_show&&this.before_show(this);

		if (!this.done) {
			this.form.focus_on_first_input();
		}

		this.check_reqd_fields();
	}

	hide_slide() {
		this.before_hide&&this.before_hide(this);
		this.$wrapper.addClass("hidden");
	}

	get_input(fieldname) {
		return this.form.get_input(fieldname);
	}

	get_field(fieldname) {
		return this.form.get_field(fieldname);
	}

	get_value(fieldname) {
		return this.form.get_value(fieldname);
	}

	is_last_slide() {
		return !this.parent_slides.can_go_next(this.id);
	}

	is_first_slide() {
		return !this.parent_slides.can_go_prev(this.id);
	}

	destroy() {
		this.$body.remove();
		this.made = false;
	}
};

frappe.ui.Slides = class Slides {
	/**
	 * @param {{
	 *	parent: HTMLElement|JQuery,
	 *	slides: any[],
	 *	values?: Record<String, any>,
	 *	doc?: Record<String, any>,
	 *	values_is_doc?: boolean,
	 *	starting_slide?: Number,
	 *	unidirectional?: boolean,
	 *	unidirectional_allow_back?: boolean,
	 *	clickable_progress_dots?: boolean,
	 *	done_state?: boolean,
	 *	parent_form?: frappe.ui.form.Form,
	 *	slide_class?: frappe.ui.Slide,
	 * }}
	 */
	constructor({
		parent,
		slides,
		values,
		doc,
		starting_slide = 0,
		unidirectional = false,
		unidirectional_allow_back = true,
		clickable_progress_dots = false,
		done_state = false,
		parent_form = undefined,
		slide_class = frappe.ui.Slide,
		...settings
	}) {
		this.parent = parent;
		this.slide_settings = slides;
		this.current_id = Math.min(slides.length - 1, cint(starting_slide) || 0);
		this.unidirectional = Boolean(unidirectional);
		this.clickable_progress_dots = Boolean(clickable_progress_dots);
		this.done_state = Boolean(done_state);

		/* Always allow_back if not unidirectional (because user can click next on invalid slides). */
		this.allow_back = unidirectional ? Boolean(unidirectional_allow_back) : true;

		this.parent_form = parent_form;

		this.slide_class = slide_class;

		this.text_prev_btn = __("Previous");
		this.text_next_btn = __("Next");
		this.text_complete_btn = __("Submit");
		this.text_in_progress = __("In progress");

		if (doc && values) {
			console.warning('[Slides]: cannot call constructor with both `doc` and `values` settings, ignoring `values`')
		}
		if (doc) {
			this.values = doc // link to doc
			/** true to assume .values is a document, will enable .doc getter */
			this.values_is_doc = true
		} else if (values) {
			this.values = values // set initial values
			this.values_is_doc = false
		} else {
			this.values = {} // no initial values
			this.values_is_doc = false
		}

		Object.assign(this, settings);

		/** @type {frappe.ui.Slide[]} */
		this.slide_instances = [];

		this.make();
	}

	// Overridable lifecycle methods
	before_load() { }
	after_load() { }
	slide_on_update() { }
	on_complete() { }

	make() {
		if (!this.$container) this.$container = $('<div class="mx-auto slides-default-style">').appendTo(this.parent);
		if (!this.$header) this.$header = $('<div>').insertBefore(this.$container);
		if (!this.$body) this.$body = $('<div>').appendTo(this.$container);
		if (!this.$footer) this.$footer = $('<div>').appendTo(this.$container);

		this.$container.addClass('slides-wrapper');
		this.$header.addClass('slide-header');
		this.$body.addClass('slide-container');
		this.$footer.addClass('slide-footer');

		if (!this.$slide_progress) this.$slide_progress = $('<div class="text-center">').appendTo(this.$header);
		this.$slide_progress.addClass('slides-progress');

		this.render_progress_dots();
		this.make_prev_next_buttons();

		this.on_keydown = this.on_keydown.bind(this);
		// this.setup_keyboard_nav();

		if (this.before_load) { this.before_load(this); }

		// can be on demand
		this.setup();

		if (this.after_load) { this.after_load(this); }

		// can be on demand
		this.show_slide(this.current_id || 0);
	}

	setup() {
		this.slide_settings.forEach((settings, id) => {
			if (!this.slide_instances[id]) {
				this.slide_instances[id] = new (this.slide_class)({
					...settings,
					parent: this.$body,
					parent_form: this.parent_form,
					render_parent_dots: this.render_progress_dots.bind(this),
					parent_slides: this,
					id: id,
				});
			} else {
				if (this.slide_instances[id].made) {
					this.slide_instances[id].destroy();
					this.slide_instances[id].make();
				}
			}
		});
	}

	make_all_slides() {
		for (const s of this.slide_instances) {
			if (!s.made) { s.make(); }
		}
	}

	refresh(id) {
		this.render_progress_dots();
		this.make_prev_next_buttons();
		this.show_hide_prev_next(id);
		this.current_slide && this.current_slide.refresh();
	}

	// Events and callbacks
	setup_keyboard_nav() {
		$('body').on('keydown', this.on_keydown);
	}
	disable_keyboard_nav() {
		$('body').off('keydown', this.on_keydown);
	}
	on_keydown(/** @type {KeyboardEvent} */e) {
		if (e.key === 'Enter') {
			const $target = $(e.target);
			if ($target.hasClass('prev-btn')) {
				$target.trigger('click');
			} else if ($target.closest('.slides-wrapper')) {
				this.$next_btn.trigger('click');
				e.preventDefault();
			}
		}
	}

	/**
	 * Depends on this.unidirectional and this.done_state
	 * Can be called by a slide
	 */
	render_progress_dots(no_active = false) {
		if (this.slide_instances.length <= 1) {
			this.$slide_progress.empty();
			return;
		}

		const shouldRemakeAll = (this.$slide_progress.find('.slide-step').length !== this.slide_instances.length);
		if (shouldRemakeAll) {
			this.$slide_progress.empty();
		}

		const states = [];
		const counts = {
			completed: 0,
			total: 0,
		};

		this.slide_instances.forEach((slide, id) => {
			const isCurrent = (id === this.current_id) && !no_active;
			const state = slide.get_state();
			states[id] = state;

			let $dot
			if (!shouldRemakeAll) {
				$dot = this.$slide_progress.find(`.slide-step[data-step-id="${id}"]`).first();
				$dot.removeClass('active step-success step-skip step-error');
			}
			if (!$dot || $dot.length === 0) {
				$dot = $(`<div class="slide-step">
					<div class="slide-step-indicator"></div>
					<div class="slide-step-complete">${frappe.utils.icon('tick', 'xs')}</div>
				</div>`).attr({ 'data-step-id': id });
				this.$slide_progress.append($dot);
			}

			if (isCurrent) {
				$dot.addClass('active');
			}

			if (state.skip) {
				$dot.addClass('step-skip');
				$dot.prop('title', __('This slide is skipped', null, 'Slide View'));
			} else if (state.seen) {
				if (state.error) {
					$dot.addClass('step-error');
				} else if (this.done_state && state.done) {
					$dot.addClass('step-success');
				}
			}

			/**
			 * `count.completed / (count.total - 1)` should represent the percentage of progression in the slides.
			 *
			 * Should we ignore skipped slides altogether? Should a skipped slide be counted in the total if it's before the current slide?
			 */
			if (!state.skip) {
				counts.total++;
				if (state.done) { counts.completed++; }
			}
		})

		if (this.on_update) {
			this.on_update(counts.completed, counts.total);
		}

		if (this.clickable_progress_dots && shouldRemakeAll) {
			this.bind_progress_dots();
		}
	}

	make_prev_next_buttons() {
		this.$footer.empty();

		const $buttons = $(`<div class="flex flex-row">
			<div class="col-sm-6 text-left prev-div">
				<button class="btn btn-secondary prev-btn" tabindex="0">${this.text_prev_btn}</button>
			</div>
			<div class="col-sm-6 text-right next-div">
				<button class="btn btn-primary next-btn" tabindex="0">${this.text_next_btn}</button>
				<button class="btn btn-primary complete-btn" tabindex="0">${this.text_complete_btn}</button>
			</div>
		</div>`).appendTo(this.$footer);

		this.$prev_btn = $buttons.find('.prev-btn')
			.on('click', () => this.show_previous_slide());

		this.$next_btn = $buttons.find('.next-btn')
			.addClass('action')
			.on('click', () => this.on_next_click());

		this.$complete_btn = $buttons.find('.complete-btn')
			.addClass('action')
			.on('click', () => this.on_complete_click());
	}

	enable_disable_action_buttons(disable) {
		const $btns = this.$footer.find('.btn.action');
		if (disable) {
			$btns.attr('disabled', true);
		} else {
			$btns.attr('disabled', false);
		}
	}

	async check_validation_async() {
		if (this.current_slide && this.current_slide.validate) {
			const promiseOrValue = this.current_slide.validate(this.current_slide);
			if (promiseOrValue !== undefined && typeof promiseOrValue.then === 'function') {
				this.set_in_progress();
				const isValid = await promiseOrValue;
				this.remove_in_progress();
				return Boolean(isValid);
			} else {
				return Boolean(promiseOrValue);
			}
		}
		return true; // valid if no validator
	}

	async on_next_click() {
		const isValid = await this.check_validation_async();
		if (!isValid) { return; }

		if (this.done_state && this.current_slide) {
			this.current_slide.done = true;
		}

		const ignore_form_errors = Boolean(this.current_slide && this.current_slide.ignore_form_errors);
		this.show_next_slide(ignore_form_errors);
	}

	async on_complete_click() {
		const isValid = await this.check_validation_async();
		if (!isValid) { return; }

		if (this.done_state && this.current_slide) {
			this.current_slide.done = true;
		}

		this.complete();
	}

	complete() {
		const ignore_form_errors = true;
		const hasErrors = this.current_slide.has_errors(ignore_form_errors);
		const stopBecauseErrors = this.unidirectional ? hasErrors : false;
		if (stopBecauseErrors) { return; }

		this.update_values();

		const no_active = true;
		this.render_progress_dots(no_active);
		this.on_complete && this.on_complete(this);
	}

	set_in_progress() {
		this.$container.addClass('state-loading');
		this.$next_btn.attr("disabled", true);
		this.$next_btn.text(this.text_in_progress);
		this.$complete_btn.attr("disabled", true);
		this.$complete_btn.text(this.text_in_progress);
	}

	remove_in_progress() {
		this.$container.removeClass('state-loading');
		this.$next_btn.attr("disabled", false);
		this.$next_btn.text(this.text_next_btn);
		this.$complete_btn.attr("disabled", false);
		this.$complete_btn.text(this.text_complete_btn);
	}

	bind_progress_dots() {
		const me = this;
		this.$slide_progress.find('.slide-step')
			.addClass('link')
			.off('click')
			.on('click', function () {
				const id = this.getAttribute('data-step-id');

				const skipped = $(this).hasClass('step-skip')
				if (skipped) { return; }

				if (me.unidirectional && (+id) >= (+me.current_id)) { return; }

				const hasErrors = me.current_slide.has_errors(true);
				if (!hasErrors && me.current_slide) {
					me.current_slide.last_validation_result = true;
					if (me.done_state) {
						me.current_slide.done = true;
					}
				}

				me.show_slide(id);
			});
	}

	show_previous_slide() {
		// const prev_id = this.current_id - 1;
		const prev_id = this.find_next_nonskipped_slide(-1);
		if (prev_id >= 0) {
			this.show_slide(prev_id);
		}
	}

	show_next_slide(ignore_form_errors) {
		const hasErrors = this.current_slide.has_errors(ignore_form_errors);
		const stopBecauseErrors = this.unidirectional ? hasErrors : false;
		if (stopBecauseErrors) { return; }

		this.update_values();

		// const next_id = this.current_id + 1;
		const next_id = this.find_next_nonskipped_slide(+1);
		if (next_id >= 0 && next_id < this.slide_instances.length) {
			this.show_slide(next_id);
		} else if (next_id === -1) {
			this.complete(); // complete because was last slide
		}
	}

	/**
	 * Returns the index of the next/previous non-skipped slide,
	 * or returns -1 if the slides cannot move in the given direction (first/last non-skipped slide).
	 * @param {Number} direction +1 or -1
	 * @returns {Number} -1 if not found
	 */
	find_next_nonskipped_slide(direction = +1, curr_id = undefined) {
		if (curr_id === undefined) {
			curr_id = this.current_id;
		}
		let id = curr_id + direction
		while (id < this.slide_instances.length && id >= 0) {
			const s = this.slide_instances[id];
			const skip = (typeof s.should_skip === 'function' ? s.should_skip(s) : Boolean(s.should_skip));

			if (!skip) { return id; }

			id += direction;
		}
		// not found, cannot go in this direction
		return -1;
	}

	/**
	 * Function called before changing slide.
	 * @returns {boolean} Block slide change
	 *	- `true` if the slide should not change
	 * 	- `false`/falsey to allow slide change (normal behavior)
	 */
	before_show_slide(id) { return false; }

	show_slide(id) {
		id = cint(id);
		if (this.before_show_slide(id) || (this.current_slide && this.current_id === id)) {
			return;
		}

		if (id >= this.slide_instances.length) {
			return;
		}

		if (this.current_slide) {
			this.current_slide.hide_slide();
		}

		this.current_id = id;
		this.current_slide = this.slide_instances[id];

		if (!this.slide_instances[id].made) {
			this.slide_instances[id].make();
		}

		this.current_slide.show_slide();

		this.refresh(id);
	}

	destroy_slide(id) {
		if (this.slide_instances[id]) {
			this.slide_instances[id].destroy();
		}
	}

	can_go_next(id) {
		const next_id = this.find_next_nonskipped_slide(+1, id);
		return (next_id !== -1);
	}

	can_go_prev(id) {
		const prev_id = this.find_next_nonskipped_slide(-1, id);
		return (prev_id !== -1);
	}

	show_hide_prev_next(id) {
		if (this.can_go_prev(id) && this.allow_back) {
			this.$prev_btn.show();
		} else {
			this.$prev_btn.hide();
		}

		if (this.can_go_next(id)) {
			this.$next_btn.show();
			this.$complete_btn.hide();
		} else {
			this.$next_btn.hide();
			this.$complete_btn.show();
		}
	}

	get doc() {
		return this.values_is_doc ? this.values : null;
	}

	/**
	 * Side effect: updates this.values (without reassignment)
	 */
	get_values(force = false) {
		const force_get_all = force || !this.values_is_doc;
		this.slide_instances.forEach((slide) => {
			const slideValues = slide.get_values(force_get_all);
			Object.assign(this.values, slideValues);
		});
		return this.values;
	}

	update_values() {
		return this.get_values(!this.values_is_doc);
	}

	has_errors() {
		const hasErrors = this.slide_instances.some((slide) => slide.has_errors());
		return hasErrors;
	}

	on_update(completed, total) { }

	reset() {
		this.slide_instances.forEach(slide => {
			if (slide.made && slide.form) {
				slide.form.clear();
			}
		})
	}
};
