import { BlockEditorTool } from "./tool";

export default class Columns extends BlockEditorTool {
	static get toolbox() {
		return {
			title: "Columns",
			icon: `<span class="uil uil-columns"></span>`,
		};
	}

	get fields() {
		const out = { n_cols: { type: "hidden" } };
		for (let i = 0; i < this.data.n_cols; i++) {
			out[`col${i}`] = {
				type: "subeditor",
				placeholder: __("Column {0}", [i + 1]),
			};
		}
		return out;
	}

	layout() {
		this.elements.container = super.layout();
		this.elements.container.classList.add("be-block--columns");

		for (let i = 0; i < this.data.n_cols; i++) {
			const col = this.makeColumnElement(i);
			this.elements.container.appendChild(col);
		}
		return this.elements.container;
	}

	setColumnProperties(index, col) {
		col.classList.add("be-block--column");
	}

	makeColumnElement(index) {
		const col = document.createElement("div");
		this.setColumnProperties(index, col);
		this.elements[`col${index}`] = col;
		return col;
	}

	load(data) {
		this.data.n_cols = Math.max(+data.n_cols || 0, 2);
		for (let i = 0; i < this.data.n_cols; i++) {
			this.data[`col${i}`] = data[`col${i}`] || undefined;
		}
	}

	renderSettings() {
		const wrapper = document.createElement("div");
		wrapper.classList.add("be-settings");

		const me = this;
		const control = frappe.ui.form.make_control({
			parent: wrapper,
			df: {
				fieldtype: "Int",
				label: __("Columns"),
				fieldname: "n_cols",
				min: 2,
				max: 6,
				onchange() {
					me.data.n_cols = Math.max(+this.value || 0, 2);
					me.update();
				},
			},
			render_input: true,
		});
		control.value = this.data.n_cols;
		control.refresh_input();

		return wrapper;
	}

	update() {
		const currentColumns = this.elements.container.children.length;
		if (currentColumns < this.data.n_cols) {
			for (let i = currentColumns; i < this.data.n_cols; i++) {
				this.elements.container.appendChild(this.makeColumnElement(i));
				this._makeSubEditor(`col${i}`, this.elements[`col${i}`]);
			}
		} else if (currentColumns > this.data.n_cols) {
			for (let i = this.data.n_cols; i < currentColumns; i++) {
				this.elements.container.removeChild(this.elements[`col${i}`]);
				this.subeditors[`col${i}`].destroy();
			}
		}
		for (let i = 0; i < this.data.n_cols; i++) {
			this.setColumnProperties(i, this.elements[`col${i}`]);
		}
	}
}
