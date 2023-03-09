import Block from "frappe/public/js/frappe/views/workspace/blocks/block.js";
import SummaryCardRenderer from "./summary_card_render";
import SummaryCardEditDialog from "./summary_card_dialog";

export default class SummaryCard extends Block {
	static get toolbox() {
		return {
			title: __("Summary Card"),
			icon: frappe.utils.icon("card", "sm"),
		};
	}

	static get isReadOnlySupported() {
		return true;
	}

	static _Renderer = SummaryCardRenderer;

	constructor({ data, api, config, readOnly, block }) {
		super({ data, api, config, readOnly, block });
		this.col = this.data.col ? this.data.col : "4";
		this.allow_customization = !this.readOnly;
		this.options = {
			allow_sorting: this.allow_customization,
			allow_create: this.allow_customization,
			allow_delete: this.allow_customization,
			allow_hiding: false,
			allow_edit: true,
			allow_resize: true,
			min_width: 2,
			// max_widget_count: 2,
		};
	}

	get_skeleton() {
		return `
			<div class="widget-head">
				<div class="sc-row sc-header"></div>
				<div class="widget-control"></div>
			</div>
			<div class="widget-body sc-body"></div>
			<div class="widget-footer"></div>
		`;
	}

	render() {
		this.wrapper = document.createElement("div");
		this.wrapper.classList.add("widget");
		this.wrapper.innerHTML = this.get_skeleton();
		this.wrapper.classList.add("summary-card");

		this.$wrapper = $(this.wrapper);
		this.$header = this.$wrapper.find(".sc-header");
		this.$body = this.$wrapper.find(".sc-body");
		this.$footer = this.$wrapper.find(".widget-footer");
		this.$controls = this.$wrapper.find(".widget-control");

		// Set-up controls
		if (!this.readOnly) {
			this.wrapper.classList.add("edit-mode");

			this.add_new_block_button();
			this.add_settings_button();

			frappe.utils.add_custom_button(
				frappe.utils.icon("drag", "xs"),
				null,
				"drag-handle",
				__("Drag"),
				null,
				this.$controls
			);
			frappe.utils.add_custom_button(
				frappe.utils.icon("edit", "xs"),
				() => this.edit(),
				"edit-button",
				__("Edit"),
				null,
				this.$controls
			);
		}

		this.render_body();

		return this.wrapper;
	}

	async edit() {
		const docname = this.data.summary_card_name;
		const editDialog = new SummaryCardEditDialog({
			title: __("Edit"),
			type: "summary-card",
			label: "label test",
			values: {
				summary_card_name: docname,
			},
			primary_action: (values) => {
				this.data.summary_card_name = values.summary_card_name;
				this.render_body();
			},
		});
		editDialog.make();
	}

	render_body() {
		if (!this.renderer) {
			this.renderer = new SummaryCardRenderer({
				wrapper: this.wrapper,
				$body: this.$body,
				$footer: this.$footer,
				$header: this.$header,
				summary_card_name: this.data.summary_card_name,
				set_name: (name) => {
					this.data.summary_card_name = name;
				},
			});
		}
	}

	validate(savedData) {
		return true;
	}

	save() {
		return {
			summary_card_name: this.data.summary_card_name || "",
			col: this.get_col() || 12,
			new: this.new_block_widget || "new",
		};
	}
}
