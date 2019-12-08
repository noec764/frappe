<template>
	<div :id="id"></div>
</template>

<script>
	export default {
		name: 'FrappeCharts',
		props: {
			id: {
				required: true,
				type: String,
				default: null
			},
			dataSets: {
				required: false
			},
			labels: {
				required: false,
				type: Array,
				default: () => []
			},
			startDate: {
				required: false,
				type: Date,
				default: null
			},
			endDate: {
				required: false,
				type: Date,
				default: null
			},
			dataPoints: {
				required: false,
				type: Object,
				default: () => {}
			},
			countLabel: {
				required: false,
				type: String,
				default: 'Count'
			},
			title: {
				required: false,
				type: String
			},
			height: {
				required: false,
				type: Number,
				default: 300
			},
			type: {
				required: false,
				type: String,
				default: 'bar'
			},
			yMarkers: {
				required: false,
				type: Array,
				default: () => null
			},
			yRegions: {
				required: false,
				type: Array,
				default: () => null
			},
			colors: {
				required: false,
				type: Array,
				default: () => [
					'purple', '#ffa3ef', 'light-blue'
				]
			},
			isNavigable: {
				required: false,
				type: Boolean,
				default: false
			},
			valuesOverPoints: {
				required: false,
				type: Boolean,
				default: false
			},
			lineOptions: {
				required: false,
				type: Object,
				default: () => {
					return {
						dotSize: 4,
						hideLine: 0,
						hideDots: 0,
						heatline: 0,
						regionFill: 0,
						areaFill: 0
					}
				}
			},
			axisOptions: {
				required: false,
				type: Object,
				default: () => {
					return {
						yAxisMode: '',
						xAxisMode: '',
						xIsSeries: 0
					}
				}
			},
			maxLegendPoints: {
				required: false,
				type: Number,
				default: 20
			},
			maxSlices: {
				required: false,
				type: Number,
				default: 20
			},
			barOptions: {
				required: false,
				type: Object,
				default: () => {
					return {
						height: 20,
						depth: 2,
						spaceRatio: 0.5,
						stacked: 0
					}
				}
			},
			discreteDomains: {
				required: false,
				type: Boolean,
				default: true
			},
			tooltipOptions: {
				required: false,
				type: Object,
				default: () => {
					return {
						formatTooltipX: d => (d + '').toUpperCase(),
						formatTooltipY: d => d + ' pts'
					}
				}
			}
		},
		data () {
			return {
				chart: null
			}
		},
		computed: {
			data() {
				return {
					labels: this.labels,
					datasets: this.dataSets,
					yMarkers: this.yMarkers,
					yRegions: this.yRegions
				}
			},
			heatmapData() {
				return {
					dataPoints: this.dataPoints,
					start: this.startDate,
					end: this.endDate,
					countLabel: this.countLabel
				}
			}

		},
		mounted () {
			this.startChart()
		},
		watch: {
			dataSets() {
				this.startChart()
			}
		},
		methods: {
			startChart () { 
				this.chart = new frappe.Chart(`#${this.id}`, this.getOptions())
			},
			getOptions() {
				const baseOptions = {
					type: this.type,
					discreteDomains: this.discreteDomains,
					colors: this.colors,
					height: this.height,
					title: this.title,
					isNavigable: this.isNavigable
				}
				const heatMapOptions = {
					data: this.heatmapData
				}
				const chartOptions = {
					data: this.data,
					tooltipOptions: this.tooltipOptions,
					valuesOverPoints: this.valuesOverPoints,
					barOptions: this.barOptions,
					lineOptions: this.lineOptions,
					axisOptions: this.axisOptions,
					maxLegendPoints: this.maxLegendPoints,
					maxSlices: this.maxSlices,
				}
				
				return Object.assign(
					baseOptions,
					(this.type === 'heatmap') ? heatMapOptions : chartOptions
				)
			},
			export () {
				this.chart.export()
			},
			addDataPoint (label, valueFromEachDataset, index) {
				this.chart.addDataPoint(label, valueFromEachDataset, index)
			},
			removeDataPoint (index) {
				this.chart.removeDataPoint(index)
			},
			updateDataset (datasetValues, index) {
				this.chart.updateDataset(datasetValues, index)
			},
			update (data) {
				this.chart.update(data)
			},
			unbindWindowEvents () {
				this.chart.unbindWindowEvents()
			}
		}        
	}
</script>
