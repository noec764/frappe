import Quill from "quill";
import TemplateFieldSelector from "./template_field_selector";
import ImageResize from "quill-image-resize";
import MagicUrl from "quill-magic-url";

Quill.register("modules/imageResize", ImageResize);
Quill.register("modules/magicUrl", MagicUrl);
const CodeBlockContainer = Quill.import("formats/code-block-container");
CodeBlockContainer.tagName = "PRE";
Quill.register(CodeBlockContainer, true);

// font size
let font_sizes = [
	"---",
	"8px",
	"9px",
	"10px",
	"11px",
	"12px",
	"13px",
	"14px",
	"15px",
	"16px",
	"18px",
	"20px",
	"22px",
	"24px",
	"32px",
	"36px",
	"40px",
	"48px",
	"54px",
	"64px",
	"96px",
	"128px",
];
const Size = Quill.import("attributors/style/size");
Size.whitelist = font_sizes;
Quill.register(Size, true);

// table
const Table = Quill.import("formats/table-container");
const superCreate = Table.create.bind(Table);
Table.create = (value) => {
	const node = superCreate(value);
	node.classList.add("table");
	node.classList.add("table-bordered");
	return node;
};

Quill.register(Table, true);

// link without href
var Link = Quill.import("formats/link");

class MyLink extends Link {
	static create(value) {
		let node = super.create(value);
		value = this.sanitize(value);
		node.setAttribute("href", value);
		if (value.startsWith("/") || value.indexOf(window.location.host) !== -1) {
			// no href if internal link
			node.removeAttribute("target");
		}
		return node;
	}
}

Quill.register(MyLink, true);

// Template blot
const ATTRS = {
	PARENT: "data-doctype",
	FIELDNAME: "data-value",
	REFERENCE: "data-reference",
	LABEL: "data-label",
	FUNCTION: "data-function",
	FIELDTYPE: "data-fieldtype",
};

const Embed = Quill.import("blots/embed");

class TemplateBlot extends Embed {
	static create(value) {
		const node = super.create(value);
		node.setAttribute("class", "indicator-pill no-indicator-dot");
		node.setAttribute(ATTRS.PARENT, value.parent);
		node.setAttribute(ATTRS.FIELDNAME, value.fieldname);
		node.setAttribute(ATTRS.REFERENCE, value.reference);
		node.setAttribute(ATTRS.LABEL, value.label);
		node.setAttribute(ATTRS.FUNCTION, value.function);
		node.setAttribute(ATTRS.FIELDTYPE, value.fieldtype);

		let label = value.label;
		let icon = "";
		if (value.function && value.function !== "null") {
			icon = frappe.utils.icon("uil uil-cog", "xs") + " ";
			node.classList.add("yellow");
		} else {
			const dt_icon = frappe.model.doctype_icons?.[value.parent] || "fa fa-file";
			icon = frappe.utils.icon(dt_icon, "xs") + " ";
			node.classList.add("purple");
		}
		node.innerHTML = icon;
		node.appendChild(document.createTextNode(label));
		return node;
	}

	static value(node) {
		return {
			parent: node.getAttribute(ATTRS.PARENT),
			fieldname: node.getAttribute(ATTRS.FIELDNAME),
			reference: node.getAttribute(ATTRS.REFERENCE),
			label: node.getAttribute(ATTRS.LABEL),
			function: node.getAttribute(ATTRS.FUNCTION),
			fieldtype: node.getAttribute(ATTRS.FIELDTYPE),
		};
	}
}
TemplateBlot.blotName = "template-blot";
TemplateBlot.tagName = "template-blot";

Quill.register(
	{
		"formats/template-blot": TemplateBlot,
	},
	true
);

// image uploader
const Uploader = Quill.import("modules/uploader");
Uploader.DEFAULTS.mimetypes.push("image/gif");

// inline style
const BackgroundStyle = Quill.import("attributors/style/background");
const ColorStyle = Quill.import("attributors/style/color");
const SizeStyle = Quill.import("attributors/style/size");
const FontStyle = Quill.import("attributors/style/font");
const AlignStyle = Quill.import("attributors/style/align");
const DirectionStyle = Quill.import("attributors/style/direction");
Quill.register(BackgroundStyle, true);
Quill.register(ColorStyle, true);
Quill.register(SizeStyle, true);
Quill.register(FontStyle, true);
Quill.register(AlignStyle, true);
Quill.register(DirectionStyle, true);

// direction class
const DirectionClass = Quill.import("attributors/class/direction");
Quill.register(DirectionClass, true);

// replace font tag with span
const Inline = Quill.import("blots/inline");

class CustomColor extends Inline {
	constructor(domNode, value) {
		super(domNode, value);
		this.domNode.style.color = this.domNode.color;
		domNode.outerHTML = this.domNode.outerHTML
			.replace(/<font/g, "<span")
			.replace(/<\/font>/g, "</span>");
	}
}

CustomColor.blotName = "customColor";
CustomColor.tagName = "font";

Quill.register(CustomColor, true);

frappe.ui.form.ControlTextEditor = class ControlTextEditor extends frappe.ui.form.ControlCode {
	make_wrapper() {
		super.make_wrapper();
	}

	make_input() {
		this.has_input = true;
		this.Quill = Quill; // for template field selector
		this.make_quill_editor();
	}

	make_quill_editor() {
		if (this.quill) return;

		this.quill_container = $("<div>").appendTo(this.input_area);
		if (this.df.max_height) {
			$(this.quill_container).css({ "max-height": this.df.max_height, overflow: "auto" });
		}

		const options = this.get_quill_options();
		if (options.theme === "snow") {
			options.modules.toolbar = this.make_toolbar_from_template();
		}
		this.quill = new Quill(this.quill_container[0], options);

		this.make_template_editor();

		this.bind_events();
	}

	make_toolbar_from_template() {
		// @dokos: Need to provide a HTML toolbar because of tooltips + translations.
		const show_template = this.df?.options == "Template" ? true : false;
		return $(
			frappe.render_template("text_editor", {
				...this.get_tooltips(),
				showtemplate: show_template,
				font_sizes: font_sizes,
			})
		)
			.prependTo(this.input_area)
			.get(0);
	}

	get_tooltips() {
		// @dokos
		return {
			header: __("Text Size"),
			size: __("Font Size"),
			bold: __("Bold"),
			italic: __("Add italic text <cmd+i>"),
			underline: __("Underline"),
			blockquote: __("Quote"),
			codeblock: __("Code"),
			link: __("Link"),
			image: __("Image"),
			orderedlist: __("Ordered list"),
			bulletlist: __("Bullet list"),
			checklist: __("Check list"),
			align: __("Align"),
			indent: __("Indent"),
			table: __("Add a table"),
			clean: __("Remove formatting"),
			templateblot: __("Add a variable"),
			direction: __("Direction"),
			strike: __("Strike"),
		};
	}

	make_template_editor() {
		// @dokos: insert template blot
		// race condition exists with rendering the icons in the blots
		frappe.model.get_doctype_icons?.();

		const toolbar = this.quill.getModule("toolbar");
		toolbar.addHandler("template-blot", () => {
			const inferred_doctype =
				this.frm?.doc?.ref_doctype ||
				this.frm?.doc?.reference_doctype ||
				this.frm?.doc?.ref_dt ||
				this.frm?.doc?.reference_dt;
			if (!this.field_selector) {
				this.field_selector = new TemplateFieldSelector({
					default_doctype: inferred_doctype,
					editor: this,
				});
			} else {
				this.field_selector.make_dialog();
			}
		});
	}

	bind_events() {
		this.quill.on(
			"text-change",
			frappe.utils.debounce((delta, oldDelta, source) => {
				if (!this.is_quill_dirty(source)) return;

				const input_value = this.get_input_value();
				this.parse_validate_and_set_in_model(input_value);
			}, 300)
		);

		$(this.quill.root).on("keydown", (e) => {
			const key = frappe.ui.keys && frappe.ui.keys.get_key(e);
			if (["ctrl+b", "meta+b"].includes(key)) {
				e.stopPropagation();
			}
		});

		$(this.quill.root).on("drop", (e) => {
			e.stopPropagation();
		});

		// table commands
		this.$wrapper.on("click", ".ql-table .ql-picker-item", (e) => {
			const $target = $(e.currentTarget);
			const action = $target.data().value;
			e.preventDefault();

			const table = this.quill.getModule("table");
			if (action === "insert-table") {
				table.insertTable(2, 2);
			} else if (action === "insert-row-above") {
				table.insertRowAbove();
			} else if (action === "insert-row-below") {
				table.insertRowBelow();
			} else if (action === "insert-column-left") {
				table.insertColumnLeft();
			} else if (action === "insert-column-right") {
				table.insertColumnRight();
			} else if (action === "delete-row") {
				table.deleteRow();
			} else if (action === "delete-column") {
				table.deleteColumn();
			} else if (action === "delete-table") {
				table.deleteTable();
			}

			if (action !== "delete-row") {
				table.balanceTables();
			}

			e.preventDefault();
		});

		// font size dropdown
		let $font_size_label = this.$wrapper.find(".ql-size .ql-picker-label:first");
		let $default_font_size = this.$wrapper.find(".ql-size .ql-picker-item:first");

		if ($font_size_label.length) {
			$font_size_label.attr("data-value", "---");
			$default_font_size.attr("data-value", "---");
		}
	}

	is_quill_dirty(source) {
		if (source === "api") return false;
		let input_value = this.get_input_value();
		return this.value !== input_value;
	}

	get_quill_options() {
		return {
			modules: {
				toolbar: Object.keys(this.df).includes("get_toolbar_options")
					? this.df.get_toolbar_options()
					: this.get_toolbar_options(),
				table: true,
				imageResize: {},
				magicUrl: true,
				mention: this.get_mention_options(),
			},
			theme: this.df.theme || "snow",
			readOnly: this.disabled,
			bounds: this.quill_container[0],
			placeholder: this.df.placeholder || "",
		};
	}

	get_mention_options() {
		if (!this.enable_mentions && !this.df.enable_mentions) {
			return null;
		}
		let me = this;
		return {
			allowedChars: /^[A-Za-z0-9_]*$/,
			mentionDenotationChars: ["@"],
			isolateCharacter: true,
			source: frappe.utils.debounce(async function (search_term, renderList) {
				let method =
					me.mention_search_method || "frappe.desk.search.get_names_for_mentions";
				let values = await frappe.xcall(method, {
					search_term,
				});

				let sorted_values = me.prioritize_involved_users_in_mention(values);
				renderList(sorted_values, search_term);
			}, 300),
			renderItem(item) {
				let value = item.value;
				return `${value} ${item.is_group ? frappe.utils.icon("users") : ""}`;
			},
		};
	}

	prioritize_involved_users_in_mention(values) {
		const involved_users =
			this.frm?.get_involved_users() || // input on form
			cur_frm?.get_involved_users() || // comment box / dialog on active form
			[];

		return values
			.filter((val) => involved_users.includes(val.id))
			.concat(values.filter((val) => !involved_users.includes(val.id)));
	}

	get_toolbar_options() {
		return [
			[{ header: [1, 2, 3, false] }],
			[{ size: font_sizes }],
			["bold", "italic", "underline", "strike", "clean"],
			[{ color: [] }, { background: [] }],
			["blockquote", "code-block"],
			// Adding Direction tool to give the user the ability to change text direction.
			[{ direction: "rtl" }],
			["link", "image"],
			[{ list: "ordered" }, { list: "bullet" }, { list: "check" }],
			[{ align: [] }],
			[{ indent: "-1" }, { indent: "+1" }],
			[
				{
					table: [
						"insert-table",
						"insert-row-above",
						"insert-row-below",
						"insert-column-right",
						"insert-column-left",
						"delete-row",
						"delete-column",
						"delete-table",
					],
				},
			],
		];
	}

	parse(value) {
		if (value == null) {
			value = "";
		}
		return frappe.dom.remove_script_and_style(value);
	}

	set_formatted_input(value) {
		if (!this.quill) return;
		if (value === this.get_input_value()) return;
		if (!value) {
			// clear contents for falsy values like '', undefined or null
			this.quill.setText("");
			return;
		}

		// set html without triggering a focus
		const delta = this.quill.clipboard.convert({ html: value, text: "" });
		this.quill.setContents(delta);
	}

	get_input_value() {
		let value = this.quill ? this.quill.root.innerHTML : "";
		// hack to retain space sequence.
		value = value.replace(/(\s)(\s)/g, " &nbsp;");

		try {
			if (!$(value).find(".ql-editor").length) {
				value = `<div class="ql-editor read-mode">${value}</div>`;
			}
		} catch (e) {
			value = `<div class="ql-editor read-mode">${value}</div>`;
		}

		return value;
	}

	set_focus() {
		this.quill.focus();
	}
};
