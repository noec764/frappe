<template>
	<div 
		:id="id" 
		class="grid-item border" 
		:style="cardStyle"
	>
		<div class="item-content">
				<frappe-charts
					v-if="showChart"
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
				<div v-else class="empty-chart text-center">
					<p class="text-muted">{{ __("No data to display") }}</p>
				</div>
				<div class="card-footer">
					<div class="row">
						<div class="col-xs-10 card-link">
						</div>
						<div class="col-xs-2">
							<span><i class="octicon octicon-trashcan remove-icon" @click="remove_card"></i></span>
						</div>
					</div>
				</div>
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
			default: '340'
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
			axisOptions: {},
			colors: [this.color],
			data: {},
			title: `${this.label}`,
			cardHeight: this.height + "px",
			chartHeight: parseInt(this.height) * 90/100,
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
			return {'width': (this.width + "%").toString(), 'min-width': '280px', 'height': this.cardHeight};
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

<style lang="scss">

.card-footer {
	height: 10%;
	.card-link {
		padding-left: 22px;
		line-height: 10pt;
	}
}

.title {
	font-weight: 600;
}

.item-content {
	height: 100%;
}

.empty-chart {
	height: 90%;
	width: 100%;
	p {
		position: relative;
		top: 50%;
		transform: translateY(-50%);
	}
}

</style>