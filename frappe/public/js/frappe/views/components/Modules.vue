<template>
	<div class="modules-page-container">
		<div v-show="items.length" class="modules-dashboard" :key="moduleKey" :style="'min-height:' + computedHeight + 'px;'">
			<grid-view
				:gridKey="gridKey"
				:items="items"
				:horizontal="true"
				@removeCard="remove_card"
			/>
		</div>
		<module-detail
			v-if="this.route && modules_list.map(m => m.module_name).includes(route[1])"
			:module_name="route[1]"
			:sections="current_module_sections"
			:dashboard="items.length">
		</module-detail>
	</div>
</template>

<script>
import GridView from './desktop_grid/GridView.vue'
import ModuleDetail from './ModuleDetail.vue'
import { generate_route } from './utils.js'

export default {
	components: {
		ModuleDetail,
		GridView
	},
	data() {
		return {
			route: frappe.get_route(),
			gridKey: '',
			moduleKey: '',
			items: [],
			current_module_label: '',
			current_module_sections: [],
			modules_data_cache: {},
			modules_list: frappe.boot.allowed_modules.filter(
				d => (d.type === 'module' || d.category === 'Places') && !d.blocked
			)
		}
	},
	computed: {
		computedHeight() {
			return this.items.filter(f => f.widget_type == "Dashboard Chart").length ? 350 : 180;
		}
	},
	created() {
		this.update_current_module();
		this.get_module_dashboard();
		frappe.modules_dashboard.on("widget_added", () => {
			this.get_module_dashboard();
		})
	},
	mounted() {
		frappe.module_links = {}
		frappe.route.on('change', () => {
			if (frappe.get_route()[0]==='modules') {
				this.update_current_module();
				this.get_module_dashboard();
			}
		})
	},
	methods: {
		update_current_module() {
			let route = frappe.get_route()
			if (route[0] === 'modules') {
				this.route = route
				let module = this.modules_list.filter(m => m.module_name == route[1])[0]
				let module_name = module && (module.label || module.module_name)
				let title = this.current_module_label
					? this.current_module_label
					: module_name
				frappe.modules.home && frappe.modules.home.page.set_title(title)
				if (!frappe.modules.home) {
					setTimeout(() => {
					frappe.modules.home.page.set_title(title)
					}, 200)
				}
				if (module_name) {
					this.get_module_sections(module.module_name)
				}
			}
		},
		get_module_sections(module_name) {
			let cache = this.modules_data_cache[module_name]
			if (cache) {
				this.current_module_sections = cache
			} else {
				this.current_module_sections = []
				frappe.xcall('frappe.desk.moduleview.get', {
						module: module_name,
					})
					.then(r => {
						var m = frappe.get_module(module_name)
						this.current_module_sections = r.data
						this.process_data(module_name, this.current_module_sections)
						this.modules_data_cache[module_name] = this.current_module_sections
					})
			}
		},
		process_data(module_name, data) {
			frappe.module_links[module_name] = []
			data.forEach(function(section) {
				section.items.forEach(function(item) {
					item.route = generate_route(item)
				})
			})
		},
		get_module_dashboard() {
			frappe.xcall("frappe.desk.doctype.desk.desk.get_module_dashboard", {user: frappe.session.user, module: this.route[1]})
			.then(d => {
				this.moduleKey = frappe.scrub(this.route[1]) + '-module';
				return d;
			})
			.then(d => this.items = d)
			.then(() => this.gridKey = this.route[1] )
			.catch(error => console.warn(error))
		},
		remove_card(e) {
			const removed = this.items.filter(f => `item-${f.name}` == e)
			frappe.xcall('frappe.desk.doctype.desk.desk.remove_widget', {origin: this.route[1], widget: removed})
			.then(() => { this.items = this.items.filter(f => `item-${f.name}` != e) })
		}
	},
}
</script>

<style lang="less" scoped>
.modules-page-container {
	margin: 15px 0px;
}

.modules-section {
	position: relative;
	padding: 25px 0;
	text-align: right;
}

.modules-dashboard {
	margin-bottom: 20px;
}
</style>