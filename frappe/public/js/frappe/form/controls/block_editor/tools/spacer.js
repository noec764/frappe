import { BlockEditorTool } from "./tool";

export default class Spacer extends BlockEditorTool {
	static get toolbox() {
		return {
			title: __("Spacer"),
			icon: `<span class="uil uil-align-center-v"></span>`,
		};
	}

	layout() {
		return "<br><br>";
	}
}
