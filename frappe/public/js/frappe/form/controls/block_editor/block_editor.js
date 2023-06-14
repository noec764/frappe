frappe.ui.form.ControlBlockEditor = class ControlBlockEditor extends frappe.ui.form.ControlInput {
	static horizontal = false;

	async make_input() {
		this._input_value = undefined;
		this._make_dom();
		this.input_area.appendChild(this.editorArea);
		this.input_area.appendChild(this.previewArea);
		this.has_input = true;

		await this._make_editor();
		this._make_preview();
	}

	_make_dom() {
		this.previewArea = document.createElement("div");
		this.previewArea.classList.add("dodock-block-editor--preview");

		// const shadow = this.input_area.attachShadow({ mode: "open" });
		// const styles = document.querySelectorAll("link,style");
		// styles.forEach((style) => shadow.appendChild(style.cloneNode(true)));
		// shadow.appendChild(this.editorArea);

		this.editorArea = document.createElement("div");
		this.editorArea.classList.add("dodock-block-editor", "dodock-block-editor--root");
	}

	async _make_editor() {
		await Promise.all([
			frappe.require("block_editor.bundle.js"),
			frappe.require("block_editor.bundle.css"),
		]);
		this._input_value = this.unparse(this.value);
		this.editor = frappe.ui.form.ControlBlockEditor.make_editorjs({
			editorArea: this.editorArea,
			initialData: this._input_value,
			onReady: () => {
				this.ready = true;
				this.refresh_input();
			},
			onChange: (outputData) => {
				// if (this.compare_changes(this._input_value, outputData)) {}
				this._input_value = outputData;
				this.parse_validate_and_set_in_model(outputData);
			},
		});
	}

	_make_preview() {
		// const shadow = this.previewArea.attachShadow({ mode: "closed" });
		const iframe = this.previewArea.appendChild(document.createElement("iframe"));
		Object.assign(iframe.style, {
			width: "100%",
			height: "80vh",
			border: "none",
			background: "#fff",
			borderRadius: "inherit",
		});

		this.preview = {
			visible: false,
			loading: false,
			element: iframe,
			button: document.createElement("a"),
		};
		if (!this.label_area) return;

		this.label_area.appendChild(this.preview.button);

		const getHref = () => {
			const href = `/api/method/frappe.utils.block_editor.block_editor_render.preview_with_random_document?json=${encodeURIComponent(
				this.value
			)}&doctype=${this.frm.doc.document_type}`;
			return href;
		};

		const refreshButton = () => {
			this.preview.button.className = "mx-2 bold";

			this.preview.button.setAttribute("href", getHref());

			let text = __("Preview");
			let icon = `<i class="fa fa-eye"></i>`;
			if (this.preview.loading && this.preview.visible) {
				icon = `<i class="fa fa-spin fa-spinner"></i>`;
			} else if (this.preview.visible) {
				icon = `<i class="fa fa-eye-slash"></i>`;
			}
			this.preview.button.innerHTML = `${text} ${icon}`;
		};

		const refreshAreas = () => {
			this.previewArea.classList.toggle("hide", !this.preview.visible);
			this.editorArea.classList.toggle("hide", this.preview.visible);
		};

		const togglePreview = async () => {
			this.preview.visible = !this.preview.visible;
			refreshAreas();
			refreshButton();
			if (this.preview.visible) {
				await fetchPreview();
				refreshAreas();
				refreshButton();
			}
		};

		let generationId = 0;
		const fetchPreview = async () => {
			this.preview.loading = true;
			refreshButton();

			const currentGenerationId = ++generationId;
			const href = getHref();
			this.preview.element.setAttribute("src", href);
			// const html = await frappe.xcall("frappe.utils.block_editor.block_editor_render.render", { json: this.value });

			if (currentGenerationId === generationId) {
				// this.preview.element.innerHTML = "<style>:host > div{all: initial;}</style><div>" + html + "</div>";
				this.preview.loading = false;
			}
		};

		this.preview.button.addEventListener("click", (e) => {
			e.preventDefault();
			togglePreview();
			return false;
		});
		this.label_area.after(this.preview.button);

		refreshAreas();
		refreshButton();
	}

	refresh_input() {
		super.refresh_input();
		if (!this.ready) return;
		const ro = Boolean(this.df.read_only);
		if (ro !== this.editor.readOnly.isEnabled) {
			this.editor.readOnly.toggle(ro);
			this.editorArea.style.pointerEvents = ro ? "none" : "auto";
		}
	}

	get_input_value() {
		return this._input_value;
	}

	_is_empty(value) {
		if (!value?.blocks?.length) {
			return true;
		}
		if (value.blocks.length === 1) {
			const block = value.blocks[0];
			if (block.type === "paragraph" && !block.data.text.trim()) {
				return true;
			}
		}
		return false;
	}

	/**
	 * @param {object} value - Blocks from the editor
	 * @returns {string} - JSON string
	 */
	parse(value) {
		if (!value) {
			return undefined;
		}
		if (typeof value === "string") {
			return value;
		}
		if (this._is_empty(value)) {
			return undefined;
		}
		if ("blocks" in value) {
			value = { blocks: value.blocks, version: value.version };
		}
		return JSON.stringify(value);
	}

	/**
	 * @param {string} value - JSON string
	 * @returns {object} - Blocks for the editor
	 */
	unparse(value) {
		if (!value) {
			return undefined;
		}
		if (typeof value === "string") {
			return JSON.parse(value);
		}
		if (this._is_empty(value)) {
			return undefined;
		}
		if ("blocks" in value) {
			value = { blocks: value.blocks, version: value.version };
		}
		return value;
	}

	validate(value) {
		return this.parse(value);
	}

	set_invalid() {
		// console.error("set_invalid");
	}

	set_focus() {
		this.editor?.focus();
	}

	set_input(value) {
		if (!this.ready) {
			return;
		}

		value = this.unparse(value);

		const is_new_value = this.compare_changes(this._input_value, value);
		// const had_blocks = this._input_value?.blocks?.length;
		const will_have_blocks = value?.blocks?.length;

		this._input_value = value;
		if (is_new_value) {
			if (will_have_blocks) {
				// this.editor.clear();
				this.editor.render(value);
			} else {
				this.editor.clear();
			}
		}
	}

	/**
	 * @param {*} left
	 * @param {*} right
	 * @returns {boolean} true if values are different
	 */
	compare_changes(left, right) {
		return this.parse(left) !== this.parse(right);
	}

	set_bold() {}

	set_input_areas() {
		super.set_input_areas();
		this.disp_area = this.input_area;
	}

	set_disp_area(value) {}
};
