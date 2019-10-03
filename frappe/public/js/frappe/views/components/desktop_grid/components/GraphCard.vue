<template>
	<div>
		<frappe-charts
			v-if="showChart"
			:id="'element-' + item.name"
			:dataSets="data.datasets"
			:labels="data.labels"
			:title="title"
			:type="chartType"
			:colors="colors"
			:height="chartHeight"
			:axisOptions="axisOptions"
			:tooltipOptions="tooltipOptions"
		/>
		<div v-else class="empty-chart text-center">
			<p class="text-muted">{{ __("No data to display") }}</p>
		</div>
	</div>
</template>

<script>

import FrappeCharts from '../../../../../lib/FrappeCharts.vue';

export default {
	name: 'GraphCard',
	components: {
		FrappeCharts
	},
	props: {
		item: {
			type: Object,
			default: {}
		}
	},
	data() {
		return {
			axisOptions: {},
			colors: [this.item.chart_color],
			data: {},
			title: `${this.item.chart_name}`,
			chartHeight: parseInt(this.item.widget_height) - 50,
			settings: null,
			tooltipOptions: {
				formatTooltipX: d => (d + ''),
				formatTooltipY: d => d + ' ' + (this.item.unit || ''),
			}
		}
	},
	computed: {
		showChart() {
			return Object.keys(this.data).length
		},
		chartType() {
			const map = {"Line": "line", "Bar": "bar", "Pie": "pie", "Percentage": "percentage"}
			return map[this.item.type]
		}
	},
	mounted() {
		this.get_settings();
	},
	methods: {
		get_settings() {
			if(this.item.chart_type==="Custom" && (this.item.chart_source!="" && this.item.chart_source!=null)) {
				frappe.xcall('frappe.desk.doctype.dashboard_chart_source.dashboard_chart_source.get_config', {name: this.item.chart_source})
				.then(config => {
					const evaluated_config = frappe.dom.eval(config);
					this.settings = frappe.dashboards.chart_sources[this.item.chart_source]
					this.axisOptions = {xIsSeries: parseInt(this.settings.timeseries, 10) || 0}
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
					chart_name: this.item.chart_name,
					filters: this.item.filters,
					refresh: 1,
				}
			).then(r => this.data = r)
		}
	}
}
</script>

<style lang="scss" scoped>
.card-footer {
	height: 10%;
	.card-link {
		padding-left: 22px;
		line-height: 10pt;
	}
}

.empty-chart {
	width: 100%;
	min-height: 
	p {
		position: relative;
		top: 50%;
		transform: translateY(-50%);
	}
}

</style>