<template>
	<div 
		:id="id" 
		class="grid-item border stats-item" 
		:style="cardStyle"
	>
		<div class="item-content">
			<div class="row">
				<div class="col-xs-4">
					<div class="icon-big text-center">
						<i :class="icon" :style="iconStyle"></i>
					</div>
				</div>
				<div class="col-xs-8 card-text">
					<p>{{label}}</p>
					<h4>{{data}}</h4>
				</div>
			</div>
			<hr>
			<div class="row">
				<i class="octicon octicon-trashcan remove-icon" @click="remove_card"></i>
			</div>
		</div>
  </div>
</template>

<script>

export default {
	name: 'StatsCard',
	props: {
	  	id: {
			type: [Number, String],
			default: 'desk-graph'
		},
		width: {
			type: Number,
			default: 15
		},
		height: {
			type: String,
			default: '150'
		},
		label: {
			type: String,
			default: null
		},
		cardSource: {
			type: String,
			default: null
		},
		color: {
			type: String,
			default: null
		},
		icon: {
			type: String,
			default: null
		},
		text: {
			type: String,
			default: null
		}
	},
	data() {
		return {
			cardHeight: this.height + "px",
			data: null,
			iconStyle: this.color ? `color: ${this.color}` : ""
		}
	},
	computed: {
		cardStyle() {
			return {'width': '100%', 'max-width': (this.width + "%").toString(), 'min-width': '350px', 'min-height': this.cardHeight};
		}
	},
	mounted() {
		this.get_settings();
	},
	methods: {
		get_settings() {
			if(this.cardSource!="") {
				frappe.xcall('frappe.desk.doctype.dashboard_card_source.dashboard_card_source.get_config', {name: this.cardSource})
				.then(config => {
					const evaluated_config = frappe.dom.eval(config);
					this.settings = frappe.dashboards.card_sources[this.cardSource]
				})
				.then(() => this.fetch_data());
			} else {
				this.fetch_data();
			}
		},
		fetch_data() {
			const method = this.settings ? this.settings.method
			: 'frappe.desk.doctype.dashboard_card.dashboard_card.get';

			frappe.xcall(method,
				{
					card_name: this.label,
					refresh: 0,
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
}

.icon-big {
	font-size: 3em;
	min-height: 64px;
}

.stats-item {
	padding: 15px 15px 0;
}

.card-text {
	text-align: right;
}

</style>