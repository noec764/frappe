import NumberCard from "../../../../views/workspace/blocks/number_card";

export default class NumberCardBlockEditor extends NumberCard {
	add_settings_button() {
		return;
	}

	add_new_block_button() {
		return;
	}

	rendered(wrapper) {
		if (wrapper) {
			this.wrapper = wrapper;
		}
	}

	save() {
		return {
			number_card_name: this.data.number_card_name,
			// label: data.number_card_name,
			// label: this.block_widget?.widgets?.label ?? data.number_card_name,
		};
	}

	dispatchChange() {
		this.api.blocks.update(this.save());
		this.block.dispatchChange();
	}

	on_edit(val) {
		super.on_edit(val);
		this.data.number_card_name = val.name;
		this.dispatchChange();

		// Re-render
		const oldDiv = this.wrapper;
		const newDiv = this.render();
		oldDiv.replaceWith(newDiv);
		this.wrapper = newDiv;
	}

	new(...args) {
		super.new(...args);
		const callback = this.dialog.primary_action.bind(this.dialog);
		this.dialog.primary_action = (values, ...rest) => {
			this.data.number_card_name = values?.number_card_name;
			callback(values, ...rest);
			this.dispatchChange();
		};
		if (!this.readOnly && this.dialog.dialog) {
			this.dialog.dialog.on_hide = () => {
				if (!this.data.number_card_name) {
					this.api.blocks.delete();
				}
			};
		}
	}

	constructor(arg) {
		super(arg);

		this.col = 12;
		this.options = {
			allow_sorting: false,
			allow_create: true,
			allow_delete: true,
			allow_hiding: false,
			allow_edit: true,
			allow_resize: false,
			for_workspace: false,
		};

		this.data = Object.assign({}, this.data || arg.data);
		this.data.title = this.data.label ?? __(this.data.number_card_name) ?? __("Number Card");
		this.data.color = this.data.color ?? "#ff00ff";
	}

	make(block, block_name, widget_type = block) {
		let block_data = this.data;
		if (!block_data) return false;
		this.wrapper.innerHTML = "";
		block_data.in_customize_mode = !this.readOnly;
		this.block_widget = new frappe.widget.SingleWidgetGroup({
			container: this.wrapper,
			type: widget_type,
			class_name: block == "chart" ? "widget-charts" : "",
			options: this.options,
			widgets: block_data,
			api: this.api,
			block: this.block,
		});
		this.wrapper.setAttribute(block + "_name", block_name);
		if (!this.readOnly) {
			this.block_widget.customize();
		}
		return true;
	}

	render() {
		let wrapper = super.render();
		if (!wrapper) {
			wrapper = document.createElement("div");
		}
		return wrapper;
	}

	validate() {
		return Boolean(this.data.number_card_name);
	}
}
