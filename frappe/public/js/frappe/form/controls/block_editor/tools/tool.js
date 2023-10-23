import EditorJS from "@editorjs/editorjs";
import { messages } from "../messages";

export class BlockEditorTool {
	static get isReadOnlySupported() {
		return true;
	}

	static get toolbox() {
		throw new Error("Not implemented: static get toolbox()");
	}

	/**
	 * Empty 'this' is not empty Block
	 */
	static get contentless() {
		return true;
	}

	/**
	 * Allow to press Enter inside the Block
	 */
	static get enableLineBreaks() {
		return true;
	}

	/**
	 * Default placeholder for sub-editors
	 */
	static get DEFAULT_SUB_EDITOR_PLACEHOLDER() {
		return __("Click here to add content");
	}

	/**
	 * Returns all the available tools for the Block
	 * @returns {Record<string, any>}
	 */
	getToolsForSubEditor() {
		const allTools = window?.frappe?.ui?.form?.ControlBlockEditor?.tools || {};
		return { ...allTools };
	}

	/**
	 * Returns all the available tunes
	 * @returns {Array<string>}
	 */
	getTunesForSubEditor() {
		const allTunes = window?.frappe?.ui?.form?.ControlBlockEditor?.tunes || [];
		return [...allTunes];
	}

	// /**
	//  * Allow 'this' to be converted to/from other blocks
	//  */
	// static get conversionConfig() {
	// 	return {
	// 		/**
	// 		 * To create 'this' data from string, simple fill 'text' property
	// 		 */
	// 		import: 'text',

	// 		/**
	// 		 * To create string from 'this' data
	// 		 *
	// 		 * @param {Object} data
	// 		 * @returns {string}
	// 		 */
	// 		export(data) {
	// 			return data.text;
	// 		},
	// 	};
	// }

	get settings() {
		return [];
	}

	get fields() {
		return {};
	}

	_parseSubEditorData(data) {
		let contents = data.contents;
		if (typeof contents === "string") {
			try {
				contents = JSON.parse(contents);
			} catch (e) {
				contents = null;
			}
		}
		if (typeof contents !== "object") {
			contents = null;
		}
		if (!Array.isArray(contents?.blocks)) {
			contents = null;
		}
		return contents;
	}

	/**
	 * @param {import("@editorjs/editorjs").BlockToolConstructorOptions} opts
	 */
	constructor(opts) {
		this.api = opts.api;
		this.config = opts.config;
		this.readOnly = opts.readOnly;
		this.blockApi = opts.block;
		this.data = {};

		this.elements = {};
		this.subeditors = {};

		this.load(opts.data);
	}

	load(data) {
		data = data || {};
		for (const fieldname in this.fields) {
			const field = this.fields[fieldname];
			this.data[fieldname] = data[fieldname] ?? field.default ?? "";
		}
	}

	/**
	 * @param {string} fieldname
	 * @param {HTMLElement} el
	 */
	_makeNestedSubeditor(fieldname, _wrapper = null) {
		// Architecture:
		// (wrapper/clickable) -> (readOnly editorjs)
		// :root -> (dialog) -> (writeable editorjs)

		const me = this;

		/** @type {frappe.ui.Dialog}} */
		let dialog = null;
		/** @type {import("@editorjs/editorjs").default} */
		let readOnlyEditor = null;
		/** @type {import("@editorjs/editorjs").default} */
		let writeableEditor = null;

		/** @type {HTMLElement} */
		const holder = _wrapper || me.elements[fieldname];
		holder.classList.add("dodock-block-editor--portal");

		holder.addEventListener("click", (e) => {
			e.stopPropagation();
			openModal();
		});

		getReadOnlyEditor();

		this.subeditors[fieldname] = {
			get modal() {
				return dialog;
			},
			get readOnlyEditor() {
				return readOnlyEditor;
			},
			get writeableEditor() {
				return writeableEditor;
			},
			destroy() {
				dialog?.hide();
				dialog = null;
				readOnlyEditor?.destroy();
				readOnlyEditor = null;
				writeableEditor?.destroy();
				writeableEditor = null;
			},
		};

		return holder;

		function getReadOnlyEditor() {
			if (!readOnlyEditor) {
				readOnlyEditor = me._makeEditorJs({
					holder,
					fieldname,
					readOnly: true,
					placeholder: __("Click here to add content"),
				});
			}
			return readOnlyEditor;
		}

		function getWriteableEditor() {
			if (!writeableEditor) {
				writeableEditor = me._makeEditorJs({
					holder: dialog.body,
					fieldname,
					readOnly: false,
					placeholder: __("Click here to add content"),
					onChange: async (data) => {
						// console.log("onChange", data);
						await readOnlyEditor?.render(data);
						me.blockApi.dispatchChange();
					},
				});
			}
			return writeableEditor;
		}

		async function openModal() {
			if (!dialog) {
				makeModal();
			}
			dialog.show();

			const editor = getWriteableEditor();
			await editor.isReady;
			if (me.data[fieldname]?.blocks?.length) {
				await editor.render(me.data[fieldname]);
			} else {
				editor.clear();
			}
		}

		function closeModal() {
			if (!dialog) {
				return;
			}
			dialog.hide();
			dialog = null;
		}

		function makeModal() {
			dialog = new frappe.ui.Dialog({
				title: "Edit",
				size: "extra-large",
			});
			dialog.show();
		}
	}

	/** @param {HTMLElement} el */
	_makeShadow(el) {
		return el;
		/*
		const shadow = el.attachShadow({ mode: "open" });

		// grab the styles from the main document
		const styles = document.querySelectorAll("style");
		styles.forEach((style) => {
			shadow.appendChild(style.cloneNode(true));
		});
		const links = document.querySelectorAll("link");
		links.forEach((link) => {
			shadow.appendChild(link.cloneNode(true));
		});

		// block all the events
		const events = [
			...new Set(
				[
					...Object.getOwnPropertyNames(document),
					...Object.getOwnPropertyNames(
						Object.getPrototypeOf(Object.getPrototypeOf(document))
					),
					...Object.getOwnPropertyNames(Object.getPrototypeOf(window)),
				]
					.filter(
						(k) =>
							k.startsWith("on") &&
							(document[k] == null || typeof document[k] == "function")
					)
					.map((k) => k.substring(2))
			),
		];
		events.forEach((event) => {
			shadow.addEventListener(event, (e) => {
				e.stopPropagation();
			});
		});

		return shadow;
		*/
	}

	/**
	 * Make a sub-editor
	 * @param {string} fieldname
	 */
	_makeSubEditor(fieldname, _wrapper = null) {
		return this._makeNestedSubeditor(fieldname, _wrapper || this.elements[fieldname]);
		/*
		const field = this.fields[fieldname];

		const shadowHost = _wrapper || this.elements[fieldname];
		const shadow = this._makeShadow(shadowHost);
		const wrapper = shadow.appendChild(document.createElement("div"));
		this.elements[fieldname] = wrapper;
		this.elements[fieldname + "__shadow"] = shadow;
		this.elements[fieldname + "__shadowHost"] = shadowHost;

		const placeholder = field.placeholder ?? this.constructor.DEFAULT_SUB_EDITOR_PLACEHOLDER;
		// const accepts = field.accepts ?? ["text", "layout", "control"];

		wrapper.classList.add("dodock-block-editor", "dodock-block-editor--sub");
		const subeditor = (this.subeditors[fieldname] = this._makeEditorJs({
			holder: wrapper,
			placeholder,
			fieldname,
			readOnly: true,
		}));
		*/
	}

	_makeEditorJs({ holder, placeholder, fieldname, readOnly, narrow, onChange }) {
		const editorjs = new EditorJS({
			holder,
			tools: this.getToolsForSubEditor(),
			tunes: this.getTunesForSubEditor(),
			i18n: {
				direction: document.dir || "ltr",
				messages: messages,
			},

			// readOnly: readOnly || false,

			autofocus: false,
			logLevel: "ERROR",

			data: this.data[fieldname] || undefined,

			placeholder,
			minHeight: 24,

			onReady: () => {
				if (narrow) {
					editorjs.ui.nodes.wrapper.classList.add("codex-editor--narrow");
				}
			},

			onChange: (api, event) => {
				// console.log("onChange2", api, event);
				api.saver.save().then((subData) => {
					// const key = JSON.stringify(subData.blocks);
					// const lastKey = this._lastData;
					// console.log("key", key, lastKey);
					// if (key === lastKey) {
					// 	console.info("skippp")
					// 	return;
					// }

					this.data[fieldname] = { blocks: subData.blocks, version: subData.version };
					// this._lastData = key;
					this.blockApi.dispatchChange();
					if (onChange) {
						onChange(subData);
					}
				});
			},
		});
		return editorjs;
	}

	_makeContentEditable(fieldname, _wrapper = null) {
		const field = this.fields[fieldname];
		const wrapper = _wrapper || this.elements[fieldname];
		const placeholder = field.placeholder ?? "";

		wrapper.setAttribute("contenteditable", true);
		wrapper.setAttribute("data-placeholder", placeholder);
		wrapper.innerHTML = this.data[fieldname] || "";
		wrapper.addEventListener("input", () => {
			this.data[fieldname] = wrapper.innerHTML;
		});
	}

	layout() {
		return document.createElement("div");
	}

	hydrate(root) {
		for (const fieldname in this.fields) {
			const field = this.fields[fieldname];

			if (field.type === "hidden") {
				continue;
			}

			let wrapper = this.elements[fieldname];

			if (!wrapper) {
				console.warn(`No wrapper for field ${fieldname}`); // eslint-disable-line no-console
				wrapper = document.createElement("div");
				root.appendChild(wrapper);
			}

			if (field.type === "subeditor") {
				this._makeSubEditor(fieldname, wrapper);
			} else if (field.type === "contenteditable") {
				this._makeContentEditable(fieldname, wrapper);
			} else {
				this._makeContentEditable(fieldname, wrapper);
			}
		}
	}

	/**
	 * Create Tool container
	 *
	 * @returns {Element}
	 */
	render() {
		try {
			const root = this.resolveLayout(this.layout());
			this.hydrate(root);
			return root;
		} catch (e) {
			console.error(e); // eslint-disable-line no-console
			return document.createElement("div");
		}
	}

	resolveLayout(root) {
		if (!root) {
			throw new Error("BlockEditorTool: layout() must return an Element");
		}
		if (typeof root === "string") {
			root = document.createElement("div");
			root.innerHTML = this.layout();
		}
		return root;
	}

	/**
	 * Extract data from wrapper element
	 *
	 * @param {HTMLDivElement} el - element to save
	 * @returns {Object}
	 */
	save() {
		for (const fieldname in this.fields) {
			const field = this.fields[fieldname];
			if (field.type === "contenteditable") {
				// Get value from DOM
				this.data[fieldname] = this.elements[fieldname].innerHTML;
			}
		}
		return this.data;
	}

	/**
	 * Sanitizer rules
	 */
	static get sanitize() {
		const all = {
			br: true,
			span: true,
			div: true,
			a: {
				href: true,
			},
			img: {
				src: true,
				alt: true,
			},
		};
		const sanitize = {};
		for (const fieldname in this.fields) {
			let s;
			if (this.fields[fieldname].type === "subeditor") {
				s = all;
			} else if (this.fields[fieldname].type === "contenteditable") {
				s = all;
			} else {
				s = all;
			}
			// sanitize[fieldname] = s;
		}
		return sanitize;
	}

	/**
	 * @returns {HTMLElement | import("@editorjs/editorjs/types/tools").TunesMenuConfig}
	 */
	renderSettings() {
		return this.settings.map((item) => ({
			icon: item.icon,
			isActive: item.isActive?.(this, item) ?? false,
			label: item.label,
			onActivate: () => item.onActivate(this, item),
			closeOnActivate: item.closeOnActivate ?? true,
		}));
	}
}
