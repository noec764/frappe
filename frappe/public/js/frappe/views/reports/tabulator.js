import { TabulatorFull as Tabulator } from "tabulator-tables";

export default class TabulatorDataTable {
	constructor(report_wrapper, options) {
		$(report_wrapper).empty();
		this.wrapper = $('<div class="tabulator-report">').appendTo($(report_wrapper));

		const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);

		this.options = options;
		this.is_tree = options.treeView;

		this.create_data_sample(this.options.data);
		this.map_columns(this.options.columns);
		this.get_data(this.options.data);

		this.table = new Tabulator(this.wrapper[0], {
			data: this.data,
			columns: this.columns,
			minHeight: 100,
			maxHeight: vh - 100,
			debugInvalidOptions: false,
			dataTree: this.is_tree,
			resizableRows: true,
			textDirection: this.options.direction,
			dataTreeStartExpanded: this.is_tree,
		});

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
		};

		this.datamanager = {
			getColumns: (bool) => {
				return this.columns;
			},
		};
		/* */
	}

	refresh(data, columns) {
		this.create_data_sample(data);

		this.map_columns(columns);
		this.table.setColumns(this.columns);

		this.get_data(data);
		this.table.replaceData(this.data);

		this.table.getColumns().forEach((column) => {
			column.setWidth(true);
		});
	}

	create_data_sample(data) {
		this.data_sample = data.slice(50).concat(data.slice(-50));
	}

	map_columns(columns) {
		this.columns = columns.map((col) => {
			const mapped_col = Object.assign({}, col, {
				title: "docfield" in col ? col.docfield.label : col.label,
				field: "docfield" in col ? col.docfield.fieldname : col.fieldname,
				width: null,
				docfield: null,
				headerFilter: "getEditor" in this.options,
			});

			const report_columns = Object.assign(mapped_col, this.get_formatter(col));

			return Object.fromEntries(
				Object.entries(report_columns).filter(([_, v]) => v != null)
			);
		});
	}

	get_formatter(column) {
		if (!this.options.data.length || column.formatter) {
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
		this.data = [];
		if (!data.length) {
			return;
		}

		if (Array.isArray(data[0])) {
			const fields = this.columns.map((c) => c.field);
			data.forEach((dataList) => {
				let row = {};
				dataList.forEach((d, i) => {
					row[fields[i]] = d[fields[i]] || d.content;
				});

				if (row.name && !row.id) {
					row["id"] = row.name;
				} else if (!row.id) {
					row["id"] = Object.values(row).join("");
				}

				this.data.push(row);
			});
			return;
		}

		if (this.is_tree) {
			this.data = indentListToTree(data);
			return;
		} else if (!data[0].id) {
			if (data[0].name) {
				this.data = data.map((d) => {
					return Object.assign({}, d, {
						id: d.name,
					});
				});
				return;
			} else {
				this.data = data.map((d) => {
					return Object.assign({}, d, {
						id: Object.values(d).join(""),
					});
				});
				return;
			}
		} else {
			this.data = data;
			return;
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
