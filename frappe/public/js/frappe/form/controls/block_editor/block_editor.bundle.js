import EditorJS from "@editorjs/editorjs";
import { tools, tunes } from "./tools";
import { messages } from "./messages";

frappe.ui.form.ControlBlockEditor.tools = tools;
frappe.ui.form.ControlBlockEditor.tunes = tunes;
frappe.ui.form.ControlBlockEditor.make_editorjs = ({
	editorArea,
	initialData,
	onReady,
	onChange,
}) => {
	return new EditorJS({
		holder: editorArea,
		tools: frappe.ui.form.ControlBlockEditor.tools,
		tunes: frappe.ui.form.ControlBlockEditor.tunes,
		i18n: {
			direction: document.dir || "ltr",
			messages: messages,
		},

		autofocus: false,
		readOnly: false,
		logLevel: "ERROR",

		data: initialData,

		placeholder: __("Click here to add content"),
		minHeight: 150,

		onReady: onReady,

		onChange: (api, event) => {
			api.saver.save().then((outputData) => {
				onChange(outputData);
			});
		},
	});
};
