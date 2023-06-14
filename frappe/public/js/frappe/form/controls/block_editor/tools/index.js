import Delimiter from "@editorjs/delimiter";
import Header from "@editorjs/header";
import InlineCode from "@editorjs/inline-code";
import List from "@editorjs/list";
import Marker from "@editorjs/marker";
import Paragraph from "@editorjs/paragraph";
import Raw from "@editorjs/raw";
import Underline from "@editorjs/underline";

import Columns from "./columns";
import Image from "./image";
import NumberCard from "./numberCard";
import Spacer from "./spacer";
import Table from "./table";

/** @type {import("@editorjs/editorjs").EditorConfig["tools"]} */
export const tools = {
	// Text
	header: {
		class: Header,
		inlineToolbar: true,
		config: {
			levels: [1, 2, 3],
			defaultLevel: 1,
		},
	},
	paragraph: {
		class: Paragraph,
		inlineToolbar: true,
		config: {
			preserveBlank: true, // keep empty paragraphs
		},
	},

	// Layout
	delimiter: Delimiter,
	spacer: Spacer,
	columns: Columns,

	// Widgets
	image: Image,
	table: Table,
	list: List,
	numberCard: NumberCard,

	// Special
	raw: Raw,

	// Formatting
	inlineCode: InlineCode,
	marker: Marker,
	underline: Underline,
};

export const tunes = [];
