<template>
	<div 
		:id="id" 
		class="grid-item border" 
		:style="cardStyle"
	>
		<div class="item-content">
			<div v-if="showChart">
				<frappe-charts
					:id="id + '-chart'"
					:dataSets="data.datasets"
					:labels="data.labels"
					:title="title"
					:type="chartType"
					:colors="colors"
					:height="chartHeight"
					:axisOptions="axisOptions"
					:tooltipOptions="tooltipOptions"
				/>
				<i class="octicon octicon-trashcan remove-icon" @click="remove_card"></i>
			</div>
		</div>
  </div>
</template>

<script>

import FrappeCharts from '../../../../../lib/frappe-charts/FrappeCharts.vue';

export default {
	name: 'GraphCard',
	components: {
		FrappeCharts
	},
	props: {
	  	id: {
			type: [Number, String],
			default: 'desk-graph'
		},
		width: {
			type: Number,
			default: '30'
		},
		height: {
			type: String,
			default: '400'
		},
		label: {
			type: String,
			default: null
		},
		chartSource: {
			type: String,
			default: null
		},
		color: {
			type: String,
			default: null
		},
		type: {
			type: String,
			default: 'Line'
		},
		unit: {
			type: String,
			default: ''
		},
		last_synced: {
			type: String,
			default: null
		}
	},
	data() {
		return {
			axisOptions: {xIsSeries: 1},
			colors: [this.color],
			data: {},
			title: `<b>${this.label}</b>`,
			cardHeight: this.height + "px",
			chartHeight: parseInt(this.height) * 60/100,
			settings: null,
			tooltipOptions: {
				formatTooltipX: d => (d + ''),
				formatTooltipY: d => d + ' ' + this.unit,
			}
		}
	},
	computed: {
		showChart() {
			return Object.keys(this.data).length
		},
		cardStyle() {
			return {'width': '100%', 'max-width': (this.width + "%").toString(), 'min-width': '350px', 'height': this.cardHeight};
		},
		chartType() {
			const map = {"Line": "line", "Bar": "bar", "Pie": "pie", "Percentage": "percentage"}
			return map[this.type]
		}
	},
	mounted() {
		this.get_settings();
	},
	methods: {
		get_settings() {
			if(this.chartSource!="") {
				frappe.xcall('frappe.desk.doctype.dashboard_chart_source.dashboard_chart_source.get_config', {name: this.chartSource})
				.then(config => {
					const evaluated_config = frappe.dom.eval(config);
					this.settings = frappe.dashboards.chart_sources[this.chartSource]
				})
				.then(() => this.fetch_data());
			} else {
				this.fetch_data();
			}
		},
		fetch_data() {
			const method = this.settings ? this.settings.method
			: 'frappe.desk.doctype.dashboard_chart.dashboard_chart.get';

			frappe.xcall(method,
				{
					chart_name: this.label,
					filters: this.filters,
					refresh: 1,
				}
			).then(r => this.data = r)
		},
		remove_card() {
			this.$emit("removeCard", this.id)
		}
	}
}
</script>

<style>

.remove-icon {
	float: right;
	color: #6c7680;
	cursor:pointer;
	padding-right: 5px;
}

</style>