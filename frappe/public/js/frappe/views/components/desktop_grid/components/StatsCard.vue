<template>
	<div class="stats-section row">
		<div class="col-sm-3 hidden-xs">
				<div class="icon-big text-center">
					<i :class="item.icon" :style="iconStyle"></i>
				</div>
			</div>
		<div class="col-xs-12 col-sm-9 card-text">
			<p>{{item.card_name}}</p>
			<h2>{{data}}</h2>
		</div>
	</div>
</template>

<script>

export default {
	name: 'StatsCard',
	props: {
	  	item: {
			type: Object,
			default: {}
		}
	},
	data() {
		return {
			data: null,
			iconStyle: this.item.card_color ? `color: ${this.item.card_color}` : "",
			hover: false
		}
	},
	mounted() {
		this.get_settings();
	},
	methods: {
		get_settings() {
			if(this.item.card_type==="Custom" && (this.item.card_source!="" && this.item.card_source!=null)) {
				frappe.xcall('frappe.desk.doctype.dashboard_card_source.dashboard_card_source.get_config', {name: this.item.card_source})
				.then(config => {
					const evaluated_config = frappe.dom.eval(config);
					this.settings = frappe.dashboards.card_sources[this.item.card_source]
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
					card_name: this.item.card_name
				}
			).then(r => {
				this.data = r
			})
		}
	}
}
</script>

<style lang="scss">

.stats-section {
	padding: 15px;
	p {
		text-overflow: ellipsis;
		white-space: nowrap;
		overflow: hidden;
	}
}

.card-text {
	text-align: right;
	h2 {
		font-weight: 600;
	}
}

.icon-big {
	i {
		font-size: 64px;
	}
}
</style>