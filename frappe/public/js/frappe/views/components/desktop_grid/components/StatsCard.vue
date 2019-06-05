<template>
	<div 
		:id="id" 
		class="grid-item border stats-item" 
		:style="cardStyle"
	>
		<div class="item-content">
			<div class="row">
				<div class="panel panel--styled">
					<div class="panel-body">
						<div class="col-xs-3">
								<div class="icon-big text-center">
									<i :class="icon" :style="iconStyle"></i>
								</div>
							</div>
						<div class="col-xs-9 card-text">
							<p>{{label}}</p>
							<h2>{{data}}</h2>
						</div>
					</div>
				</div>
				<div class="card-footer">
					<div class="row">
						<div class="col-xs-10 card-link">
							<span class="card-link-header text-muted" v-if="timespan && timespan!='Preregistered'">{{ __(timespan) }}</span><br>
							<span class="card-link-body text-muted" v-if="last_synced">{{ __("Last synced:") }} {{ frappe.datetime.str_to_user(last_synced) }}</span>
						</div>
						<div class="col-xs-2">
							<span><i class="octicon octicon-trashcan remove-icon" @click="remove_card"></i></span>
						</div>
					</div>
				</div>
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
		},
		timespan: {
			type: String,
			default: null
		},
		last_synced: {
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

<style lang="scss">

.card-text {
	h2 {
		font-weight: 600;
	}
	p {
		text-overflow: ellipsis;
    	white-space: nowrap;
    	overflow: hidden;
	}
}

.icon-big {
	i {
		font-size: 64px;
	}
}

.card-footer {
	padding: 0 5px 5px 0;
	height: 40px;
}

.stats-item {
	padding: 15px 15px 0;
	min-height: 200px !important;
}

.card-text {
	text-align: right;
}

.card-footer {
	.card-link {
		padding-left: 22px;
		line-height: 10pt;
	}
	.card-link-header {
		font-size: 8pt;
	}
	.card-link-body {
		font-size: 8pt;
	}
}

</style>