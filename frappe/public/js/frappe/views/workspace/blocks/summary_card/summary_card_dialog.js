import get_dialog_constructor from "frappe/public/js/frappe/widgets/widget_dialog.js";

export default class SummaryCardEditDialog extends get_dialog_constructor() {
	make() {
		const action = this.editing ? "Edit" : "Add"; // __("Edit") __("Add")
		this.primary_action_label = __(action);

		super.make();

		this.dialog.set_secondary_action(() => {
			// Open a form to create a new Summary Card
			const docname = this.dialog.get_value("summary_card_name");
			frappe.set_route("Form", "Summary Card", docname || "new");
		});
		this.dialog.set_secondary_action_label(__("Show Full Form"));
	}

	get_title() {
		return __("Summary Card");
	}

	get_fields() {
		return [
			{
				fieldtype: "Link",
				fieldname: "summary_card_name",
				label: __("Pick an existing Summary Card"),
				options: "Summary Card",
				reqd: 1,
				translatable: 1,
			},
		];
	}
}
