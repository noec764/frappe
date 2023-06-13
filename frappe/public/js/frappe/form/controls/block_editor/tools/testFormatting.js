export class Lorem {
	static isInline = true;
	static title = "Lorem";

	get toolboxIcon() {
		return `<span class="uil uil-info-circle"></span>`;
	}

	get shortcut() {
		return "CMD+D";
	}

	static tag = "SPAN";
	static className = "text-danger";

	// static get sanitize() {
	// 	return {
	// 		[Lorem.tag]: {
	// 			class: Lorem.className,
	// 		},
	// 	};
	// }
	constructor({ api }) {
		/** @type {import("@editorjs/editorjs").API} */
		this.api = api;

		/** @type {HTMLElement|null} */
		this.button = null;

		this.iconClasses = {
			base: this.api.styles.inlineToolButton,
			active: this.api.styles.inlineToolButtonActive,
		};

		this.tag = Lorem.tag;
		this.className = Lorem.className;
	}

	render() {
		this.button = document.createElement("button");
		this.button.type = "button";
		this.button.classList.add(this.iconClasses.base);
		this.button.innerHTML = this.toolboxIcon;
		return this.button;
	}

	// renderActions() {
	// 	const input = document.createElement("input");
	// 	input.placeholder = "Enter a URL...";
	// 	return input;
	// }
	clear() {
		console.log("clear");
	}

	surround(range) {
		if (!range) {
			console.log("no range");
			return;
		}

		const wrapElement = this.findInSelection();

		if (wrapElement) {
			this.unwrap(wrapElement);
		} else {
			this.wrap(range);
		}
	}

	/** @param {Range} range */
	wrap(range) {
		const wrapElement = document.createElement(this.tag);
		wrapElement.classList.add(this.className);

		wrapElement.appendChild(range.extractContents());
		range.insertNode(wrapElement);

		// re-select the range
		this.api.selection.expandToTag(wrapElement);
		return wrapElement;
	}

	/** @param {HTMLElement} wrapElement */
	unwrap(wrapElement) {
		this.api.selection.expandToTag(wrapElement);

		const sel = window.getSelection();
		const range = sel.getRangeAt(0);

		const unwrappedContent = range.extractContents();

		// Remove empty term-tag parent node
		wrapElement.parentNode.removeChild(wrapElement);

		// Insert extracted content
		range.insertNode(unwrappedContent);

		// Restore selection
		sel.removeAllRanges();
		sel.addRange(range);
	}

	checkState() {
		const found = this.findInSelection();
		console.log("found", found);
		const exists = Boolean(found);
		this.button.classList.toggle(this.api.styles.inlineToolButtonActive, exists);
		return exists;
	}

	findInSelection() {
		return this.api.selection.findParentTag(this.tag, this.className);
	}
}
