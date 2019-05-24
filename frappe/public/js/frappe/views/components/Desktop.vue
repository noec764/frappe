<template>
	<div class="desktop-page-container">
		<div class="desktop-section">
			<a
				class="btn-show-hide text-muted text-medium"
				@click="edit_desktop"
			>
			<i class="octicon octicon-pencil"></i>
				{{ __('Edit Desktop') }}
			</a>
		</div>
		<grid-view
			:showGrid="showGrid"
			:items="items"
			@removeCard="remove_card"
		/>
	</div>
</template>

<script>
import GridView from './desktop_grid/GridView.vue'

export default {
	name: "Desktop",
	components: {
		GridView
	},
	data() {
		return {
			showGrid: false,
			items: []
		};
	},
	created() {
		this.get_desk();
	},
	methods: {
		get_desk() {
			frappe.db.exists("Desk", frappe.session.user)
			.then(e => {
				if (e === false) {
					this.create_desk();
				} else {
					this.get_desk_dashboard();
				}
			}).then(() => {
				this.showGrid = true;
			})
		},
		get_desk_dashboard() {
			frappe.xcall("frappe.desk.doctype.desk.desk.get_desk", {user: frappe.session.user})
			.then(d => { this.items = d })
			.catch(error => console.warn(error))
		},
		create_desk() {
			frappe.xcall("frappe.desk.doctype.desk.desk.create_user_desk", {user: frappe.session.user})
			.then(d => { this.items = d.desk_items })
			.catch(error => console.warn(error))
		},
		edit_desktop() {
			//TODO: Commonify with modules
			const fields = get_fields()
			const d = new frappe.ui.Dialog({
				title: __('Add a widget'),
				fields: fields,
				primary_action_label: __('Add'),
				primary_action: (values) => {
					const { widget_type, ...args } = values;
					frappe.xcall('frappe.desk.doctype.desk.desk.add_widget', {origin: "Desk", widget_type: values.widget_type, args})
					.then(() => this.get_desk())
					d.hide();
				}
			});

			d.show();

			function get_fields() {
				return [
					{
						label: __("Widget type"),
						fieldname: "widget_type",
						fieldtype: 'MultiCheck',
						options: [
							{ label: __("Calendar"), value: "Dashboard Calendar" },
							{ label: __("Chart"), value: "Dashboard Chart" },
							{ label: __("Statistics"), value: "Dashboard Stats" }
						],
						columns: 3,
						reqd: 1,
						on_change: function(value) {
							const widget_type = d.fields_dict.widget_type
							const checked = widget_type.get_checked_options()
							if (checked && checked.length > 1) {
								const index = widget_type.selected_options.indexOf(checked[0]);
								if(index > -1) {
									widget_type.selected_options.splice(index, 1);
								}
								widget_type.refresh_input();
							}
						}
					},
					{
						label: __("User"),
						fieldname: "user",
						fieldtype: 'Link',
						options: "User",
						default: frappe.session.user,
						depends_on: "eval:doc.widget_type=='Dashboard Calendar'"
					},
					{
						label: __("Reference Document"),
						fieldname: "reference",
						fieldtype: 'Link',
						options: "DocType",
						depends_on: "eval:doc.widget_type=='Dashboard Calendar'",
						filters: { name: ["in", frappe.boot.calendars] }
					},
					{
						label: __("Chart"),
						fieldname: "chart",
						fieldtype: 'Link',
						options: "Dashboard Chart",
						depends_on: "eval:doc.widget_type=='Dashboard Chart'"
					},
					{
						label: __("Card"),
						fieldname: "card",
						fieldtype: 'Link',
						options: "Dashboard Card",
						depends_on: "eval:doc.widget_type=='Dashboard Stats'"
					}
				]
			}
		},
		remove_card(e) {
			const removed = this.items.filter(f => `card-${f.name}` == e)
			frappe.xcall('frappe.desk.doctype.desk.desk.remove_widget', {origin: "Desk", widget: removed})
			.then(() => { this.items = this.items.filter(f => `card-${f.name}` != e) })
		}
	}
}
</script>

<style lang="less" scoped>
.desktop-page-container {
	margin-top: 40px;
	margin-bottom: 30px;
	@media (max-width: 767px) {
		padding-left: 50px;
	}
}
.desktop-section {
	position: relative;
	padding: 25px 0;
	text-align: right;
}
</style>
