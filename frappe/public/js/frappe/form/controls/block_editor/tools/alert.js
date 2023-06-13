import { BlockEditorTool } from "./tool";

export default class Alert extends BlockEditorTool {
	static get toolbox() {
		return {
			title: __("Alert"),
			icon: `<span class="uil uil-info-circle"></span>`,
		};
	}

	get fields() {
		return { contents: { type: "subeditor" } };
	}

	layout() {
		this.elements.contents = super.layout();
		this.elements.contents.classList.add("alert", "alert-info");
		return this.elements.contents;
	}

	/**
	 * Allow 'this' to be converted to/from other blocks
	 */
	// static get conversionConfig() {
	// 	does not work for subeditors
	// 	return {
	// 		import: "contents",
	// 	};
	// }
}
