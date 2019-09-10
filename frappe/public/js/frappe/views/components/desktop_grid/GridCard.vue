<template>
	<div :id="id" class="grid-item" :style="cardStyle">
		<div class="item-content border">
			<div class="item-body">
				<graph-card
					v-if="item.widget_type === 'Dashboard Chart'"
					:item="item"
				/>
				<calendar-card
					v-if="item.widget_type === 'Dashboard Calendar'"
					:item="item"
				/>
				<stats-card
					v-if="item.widget_type === 'Dashboard Card'"
					:item="item"
				/>
			</div>
			<div class="item-footer">
				<div class="row">
					<div class="col-xs-10 item-link">
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

import GraphCard from './components/GraphCard.vue';
import StatsCard from './components/StatsCard.vue';
import CalendarCard from './components/CalendarCard.vue';

export default {
	name: 'GridCard',
	components: {
		GraphCard,
		StatsCard,
		CalendarCard
	},
	props: {
		id: {
			type: [Number, String],
			default: 'desk-item'
		},
		item: {
			type: Object,
			default: {}
		}
	},
	computed: {
		cardStyle() {
			return {
				'width': '100%',
				'max-width': (this.item.widget_width + '%').toString(),
				'min-width': '280px', 'height': this.item.widget_height + "px"
			};
		}
	},
	methods: {
		remove_card() {
			this.$emit("removeCard", this.id)
		}
	}
}
</script>

<style lang="scss">
.title {
	font-weight: 600;
}

.item-content {
	max-height: 100%;
	padding: 5px;
	display: block;
}

.item-footer {
	height: 25px;
	.item-link {
		padding-left: 22px;
		line-height: 10pt;
	}
}

</style>