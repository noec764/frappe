import { TabulatorFull as Tabulator } from "tabulator-tables";

export default class TabulatorDataTable {
	constructor(report_wrapper, options) {
		$(report_wrapper).empty();
		this.wrapper = $('<div class="tabulator-report">').appendTo($(report_wrapper));

		const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);

		this.options = options;
		this.original_data = this.options.data;
		this.is_tree = options.treeView;

		const route = frappe.get_route();
		this.report_view = false;
		if (route.length === 3 && route[2].toLowerCase() == "report") {
			this.report_view = true;
		}

		this.create_data_sample(this.original_data);
		this.map_columns(this.options.columns);
		this.data = this.get_data(this.original_data);

		const tabulator_options = Object.assign(
			{
				data: this.data,
				columns: this.columns,
				minHeight: 100,
				maxHeight: vh - 100,
				debugInvalidOptions: false,
				dataTree: this.is_tree,
				resizableRows: true,
				textDirection: this.options.direction,
				dataTreeStartExpanded: this.is_tree,
				selectable: this.report_view,
			},
			this.options.tabulator_options || {}
		);

		this.table = new Tabulator(this.wrapper[0], tabulator_options);

		/* Frappe Datatable parameters */
		this.bodyScrollable = {
			style: {
				removeProperty: (prop) => {},
				height: null,
			},
		};

		this.rowmanager = {
			collapseAllNodes: () => {
				this.table.getRows().forEach((r) => {
					r.treeCollapse();
				});
			},
			expandAllNodes: () => {
				this.table.getRows().forEach((r) => {
					r.treeExpand();
				});
			},
			setTreeDepth: (depth) => {
				// TODO
			},
			getCheckedRows: () => {
				return this.table.getSelectedData();
			},
		};

		this.datamanager = {
			getColumns: (bool) => {
				return this.columns;
			},
			rowViewOrder: [],
		};

		this.bodyRenderer = {
			visibleRowIndices: [],
		};
		/* */

		this.table.on("tableBuilt", () => {
			Object.assign(this.datamanager, {
				rowViewOrder: this.report_view
					? this.table.getData().map((d, index) => index)
					: this.original_data.map((d, index) => index),
			});

			this.set_data_idx_by_id();

			Object.assign(this.bodyRenderer, {
				visibleRowIndices: this.report_view
					? this.table.getData().map((d, index) => index)
					: this.original_data.map((d, index) => index),
			});
		});

		this.table.on("rowClick", () => {
			this.update_visible_row_indices();
		});

		this.table.on("dataChanged", () => {
			this.update_visible_row_indices();
		});
	}

	update_visible_row_indices() {
		const selected_data = this.table.getSelectedData().length
			? this.table.getSelectedData()
			: this.table.getData("active");
		Object.assign(this.bodyRenderer, {
			visibleRowIndices: this.report_view
				? selected_data.map((d) => this.data_idx_by_id[d.id])
				: this.original_data.map((d, index) => index),
		});
	}

	set_data_idx_by_id() {
		const data = this.report_view ? this.table.getData() : this.original_data;
		this.data_idx_by_id = Object.assign(
			{},
			...data.map((d, index) => {
				return {
					[d.id]: index,
				};
			})
		);
	}

	destroy() {
		// Frappe parameter
	}

	refreshRow(new_row, rowIndex) {
		const rowdata = this.get_data(new_row);
		this.table.updateData(rowdata).then(() => {
			this.set_data_idx_by_id();
		});
	}

	refresh(data, columns) {
		this.original_data = data;

		this.create_data_sample(data);

		this.map_columns(columns);
		this.table.setColumns(this.columns);

		this.data = this.get_data(data);
		this.table.replaceData(this.data).then(() => {
			this.set_data_idx_by_id();
		});

		this.table.getColumns().forEach((column) => {
			column.setWidth(true);
		});
	}

	create_data_sample(data) {
		this.data_sample = data.slice(50).concat(data.slice(-50));
	}

	map_columns(columns) {
		const me = this;

		this.columns = columns.map((col) => {
			const mapped_col = Object.assign({}, col, {
				title: "docfield" in col ? __(col.docfield.label) : col.label,
				field: "docfield" in col ? col.docfield.fieldname : col.fieldname,
				width: null,
				docfield: null,
				headerMenu: [
					{
						label: __("Hide Column"),
						action: function (e, column) {
							column.hide();
						},
					},
				],
				minWidth: col.width,
				visible: !col.hidden || col.hidden === "0",
			});

			if (this.report_view) {
				let fieldtype =
					col.docfield.fieldname != "name" ? col.docfield.fieldtype || "Data" : "Data";
				const editor_type = this.get_editor_type(fieldtype);

				Object.assign(mapped_col, {
					headerFilter: "input",
					editor: editor_type,
					editorParams: this.get_editor_params(col, fieldtype, editor_type),
					cellEdited: function (cell) {
						return me.cell_edited_func(cell, fieldtype);
					},
				});
			}

			const report_columns = Object.assign(mapped_col, this.get_formatter(col));

			return Object.fromEntries(
				Object.entries(report_columns).filter(([_, v]) => v != null)
			);
		});

		if (this.report_view) {
			this.columns.unshift({
				formatter: "rowSelection",
				titleFormatter: "rowSelection",
				hozAlign: "center",
				headerSort: false,
				cellClick: function (e, cell) {
					cell.getRow().toggleSelect();
				},
			});
		}
	}

	get_editor_type(fieldtype) {
		switch (fieldtype) {
			case "Text":
				return "textarea";
			case "Small Text":
				return "textarea";
			case "Int":
				return "number";
			case "Float":
				return "number";
			case "Currency":
				return "number";
			case "Percent":
				return "number";
			case "Duration":
				return "number";
			case "Check":
				return "tickCross";
			case "Rating":
				return "star";
			case "Date":
				return "date";
			case "Time":
				return "time";
			case "Datetime":
				return "datetime";
			case "Link":
				return "list";
			case "Select":
				return "list";
			default:
				return "input";
		}
	}

	get_editor_params(column, fieldtype, editor_type) {
		const me = this;

		switch (editor_type) {
			case "list":
				if (fieldtype == "Select") {
					let options = column.docfield.options;
					if (typeof column.docfield.options == "string") {
						options = column.docfield.options.split("\n").map((v) => {
							return { label: __(v), value: v };
						});
					}

					return {
						values: options,
					};
				} else {
					return {
						autocomplete: true,
						placeholderLoading: __("Loading..."),
						placeholderEmpty: __("No Result"),
						valuesLookup: function (cell, filterTerm) {
							const args = {
								txt: filterTerm,
								doctype: column.docfield.options,
								ignore_user_permissions: false,
								reference_doctype: me.get_reference_doctype() || "",
							};
							const values = new Promise((resolve, reject) => {
								return frappe
									.call({
										type: "POST",
										method: "frappe.desk.search.search_link",
										no_spinner: true,
										args: args,
									})
									.then((r) => {
										resolve(
											r.results.map((res) => {
												return Object.assign(res, { label: res.value });
											})
										);
									});
							});
							return values;
						},
						filterRemote: true,
						listOnEmpty: true,
						allowEmpty: true,
						clearable: true,
					};
				}
			default:
				return null;
		}
	}

	cell_edited_func(cell, fieldtype) {
		const cellData = cell.getData();
		const fieldname = cell.getColumn()?.getDefinition()?.field;
		const docname = cellData.id || cellData.name;
		const doctype = cellData.doctype;
		const value = cell.getValue();

		return new Promise((resolve, reject) => {
			frappe.db
				.set_value(doctype, docname, { [fieldname]: value })
				.then((r) => {
					if (r.message) {
						resolve(r.message);
					} else {
						reject();
					}
				})
				.fail(reject);
		});
	}

	get_reference_doctype() {
		// this is used to get the context in which link field is loaded
		if (this.doctype) return this.doctype;
		else {
			return frappe.get_route && frappe.get_route()[0] === "List"
				? frappe.get_route()[1]
				: null;
		}
	}

	get_formatter(column) {
		if (!this.original_data.length || column.formatter) {
			return {};
		}

		return {
			formatter: function (cell, formatterParams, onRendered) {
				const cellValue = cell.getValue();
				const row = cell.getRow();
				const cellRowData = row.getData();

				if (!cellValue) {
					return null;
				}

				return column.format(cellValue, cellRowData, column, cellRowData);
			},
		};

		/* TODO:Implement standard formatters
		// if (column.fieldtype == "Currency") {
		// 	const currency = frappe.get_doc(":Currency", column.options)

		// 	if (!currency) {
		// 		return {}
		// 	}

		// 	const currency_format = currency.number_format.split("#").filter(f => f != "")
		// 	return {
		// 		formatter: "money",
		// 		formatterParams:{
		// 			decimal: currency_format.length > 1 ? currency_format[1] : currency_format[0],
		// 			thousand: currency_format.length > 1 ? currency_format[0] : "",
		// 			symbol: currency.symbol,
		// 			symbolAfter: currency.symbol_on_right,
		// 			negativeSign: true,
		// 			precision: 2,
		// 		}
		// 	}
		// } else if (column.fieldtype == "HTML" || this.data_sample.filter(d => frappe.utils.is_html(d[column.fieldname])).length) {
		// 	return {
		// 		formatter: "html"
		// 	}
		// }

		// return {}
		*/
	}

	get_data(data) {
		let formatted_data = [];
		if (!data.length) {
			return formatted_data;
		}

		if (Array.isArray(data[0])) {
			const fields = this.columns.map((c) => c.field);
			data.forEach((dataList) => {
				let row = {};
				dataList.forEach((d, i) => {
					row[fields[i]] = d[fields[i]] || d.content;
				});

				if (dataList[0].doctype) {
					row["doctype"] = dataList[0].doctype;
				}

				if (row.name && !row.id) {
					row["id"] = row.name;
				} else if (!row.id) {
					row["id"] = Object.values(row).join("");
				}

				formatted_data.push(row);
			});
			return formatted_data;
		}

		if (this.is_tree) {
			formatted_data = indentListToTree(data);
			return formatted_data;
		} else if (!data[0].id) {
			if (data[0].name) {
				formatted_data = data.map((d) => {
					return Object.assign({}, d, {
						id: d.name,
					});
				});
				return formatted_data;
			} else {
				formatted_data = data.map((d) => {
					return Object.assign({}, d, {
						id: Object.values(d).join(""),
					});
				});
				return formatted_data;
			}
		} else {
			formatted_data = data;
			return formatted_data;
		}
	}
}

function indentListToTree(rows) {
	const parents = [{ _children: [] }]; // fake root node

	for (const row of rows) {
		const level = row.indent | 0; // integer truncation
		const parent = parents[level];

		parent._children = parent._children || [];
		parent._children.push(row);
		parents[level + 1] = row;
	}

	return parents[0]._children;
}

$(document).ready(function () {
	if (frappe.sys_defaults.use_tabulator) {
		window.DataTable = TabulatorDataTable;
	}
});
