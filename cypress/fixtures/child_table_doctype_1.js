export default {
	name: "Child Table Doctype 1",
	actions: [],
	custom: 1,
	autoname: "format: Test-{####}",
	creation: "2022-02-09 20:15:21.242213",
	doctype: "DocType",
	editable_grid: 1,
	engine: "InnoDB",
	fields: [
		{
			fieldname: "data",
			fieldtype: "Data",
			in_list_view: 1,
			label: "Data"
		},
		{
			fieldname: "barcode",
			fieldtype: "Barcode",
			in_list_view: 1,
			label: "Barcode"
		},
		{
			fieldname: "check",
			fieldtype: "Check",
			in_list_view: 1,
			label: "Check"
		},
		{
			fieldname: "rating",
			fieldtype: "Rating",
			in_list_view: 1,
			label: "Rating"
		},
		{
			fieldname: "duration",
			fieldtype: "Duration",
			in_list_view: 1,
			label: "Duration"
		},
		{
			fieldname: "date",
			fieldtype: "Date",
			in_list_view: 1,
			label: "Date"
		}
	],
	links: [],
	istable: 1,
	modified: "2022-02-10 12:03:12.603763",
	modified_by: "Administrator",
	module: "Custom",
	naming_rule: "By fieldname",
	owner: "Administrator",
	permissions: [],
	sort_field: 'modified',
	sort_order: 'ASC',
	track_changes: 1
};
