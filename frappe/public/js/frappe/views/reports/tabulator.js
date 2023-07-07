import { TabulatorFull as Tabulator } from "tabulator-tables";

export default class TabulatorDataTable {
	constructor(report_wrapper, options) {
		$(report_wrapper).empty();
		this.wrapper = $('<div class="tabulator-report">').appendTo($(report_wrapper));

		const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);

		this.options = options;
		this.is_tree = false;

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
		};
		/* */
	}

	refresh(data, columns) {
		this.create_data_sample(data);
		this.map_columns(columns);
		this.table.setColumns(this.columns);
		this.get_data(data);
		this.table.updateOrAddData(this.data);
	}

	create_data_sample(data) {
		this.data_sample = data.slice(50).concat(data.slice(-50));
	}

	map_columns(columns) {
		this.columns = columns.map((col) => {
			const mapped_col = Object.assign({}, col, {
				title: col.label,
				field: col.fieldname,
				width: null,
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
				const cellRowCells = row.getCells();

				if (!cellValue) {
					return null;
				}

				return column.format(cellValue, cellRowCells, column, cellRowData);
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

	get_data() {
		if (!this.options.data.length) {
			this.data = [];
			return;
		}

		this.is_tree = Boolean(this.data_sample.filter((d) => d.indent).length);

		if (this.is_tree) {
			this.data = indentListToTree(this.options.data);
			return;
		} else if (!this.options.data[0].id) {
			if (this.options.data[0].name) {
				this.data = this.options.data.map((d) => {
					return Object.assign({}, d, {
						id: d.name,
					});
				});
				return;
			} else {
				this.data = this.options.data.map((d) => {
					return Object.assign({}, d, {
						id: Object.values(d).join(""),
					});
				});
				return;
			}
		} else {
			this.data = this.options.data;
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

window.DataTable = TabulatorDataTable;
