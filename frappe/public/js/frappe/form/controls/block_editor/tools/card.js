import { BlockEditorTool } from "./tool";

export default class Card extends BlockEditorTool {
	static _FIELDS = {
		title: {
			type: "contenteditable",
			placeholder: __("Title..."),
			default: "",
		},
		subtitle: {
			type: "contenteditable",
			placeholder: __("Subtitle..."),
			default: "",
		},
		contents: {
			type: "subeditor",
			placeholder: __("Contents..."),
		},
	};

	static get toolbox() {
		return {
			icon: `<span class="uil uil-document-layout-left"></span>`,
			title: "Card",
			data: {},
		};
	}

	get fields() {
		return Card._FIELDS;
	}

	get settings() {
		const shadows = [
			{
				name: "md",
				label: __("Shadow: Normal"),
				uil: "uil-layer-group",
			},
			{
				name: "sm",
				label: __("Shadow: Small"),
				uil: "uil-layers",
			},
			{
				name: "",
				label: __("Shadow: None"),
				uil: "uil-layers-slash",
			},
		];
		return shadows.map((s) => ({
			name: s.name,
			label: s.label,
			icon: `<span class="uil ${s.uil}"></span>`,
			isActive: (tool) => tool.data.shadow === s.name,
			onActivate: (tool) => {
				tool.data.shadow = s.name;
				tool.elements.container.style.boxShadow = s.name ? `var(--shadow-${s.name})` : "";
			},
			closeOnActivate: true,
		}));
	}

	layout() {
		const div = super.layout();
		div.innerHTML = `
		<div class="card">
			<div class="card-body">
				<h3 class="card-title mt-0"></h3>
				<div class="card-subtitle text-lg mt-0 font-italic"></div>
				<p class="card-text"></p>
			</div>
		</div>`;

		this.elements.container = div.querySelector(".card");
		this.elements.title = div.querySelector(".card-title");
		this.elements.subtitle = div.querySelector(".card-subtitle");
		this.elements.contents = div.querySelector(".card-text");

		// Detach container from div
		div.removeChild(this.elements.container);
		div.remove();

		return this.elements.container;
	}
}
