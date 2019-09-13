<template>
	<div class="grid" v-if="showGrid" :key=gridKey>
		<muuri-grid id="frappe-grid" :options="options" @gridCreated="on_grid_created">
			<grid-card
				:id="'item-' + item.name"
				v-for="(item, index) in items"
				:key="index"
				:item="item"
				@removeCard="remove_card"
			>
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
			</grid-card>
		</muuri-grid>
		<div class="empty-grid text-center" v-if="showEmptyGrid">
			<p class="text-muted">{{ __("This dashboard is empty") }}</p>
		</div>
	</div>
</template>
<script>

import MuuriGrid from "./MuuriGrid.vue";
import GridCard from './GridCard.vue';
import GraphCard from './components/GraphCard.vue';
import StatsCard from './components/StatsCard.vue';
import CalendarCard from './components/CalendarCard.vue';

export default {
	name: 'GridView',
	components: {
		MuuriGrid,
		GridCard,
		GraphCard,
		StatsCard,
		CalendarCard
	},
	props: {
		items: {
			type: Array,
			default: []
		},
		horizontal: {
			type: Boolean,
			default: false
		},
		showGrid: {
			type: Boolean,
			default: false
		},
		gridKey: {
			type: String,
			default: null
		}
	},
	data() {
		return {
			options: {
				items: ".grid-item",
				dragEnabled: frappe.is_mobile() ? false : true,
				layoutOnInit: true,
				layout: {
					fillGaps: true,
					rounding: false,
					horizontal: this.horizontal,
					alignRight: false
				}
			},
			grid: null
		}
	},
	computed: {
		showEmptyGrid() {
			return this.items.length == 0
		}
	},
	watch: {
		items(newValue, oldValue) {
			this.add_remove_cards(newValue, oldValue);
		}
	},
	methods: {
		on_grid_created(e) {
			this.grid = e;
			this.grid.on("dragReleaseEnd", (item) => {
				this.registerItemsPositions(item.getGrid().getItems())
			})
		},
		remove_card(e) {
			this.$emit("removeCard", e);
		},
		add_remove_cards(newValue, oldValue) {
			const newValueNames = newValue.length ? newValue.map(({name}) => { return name}) : []
			const oldValuesNames = oldValue.length ? oldValue.map(({name}) => { return name}) : []

			const removed = oldValue.length ? oldValue.filter(f => !newValueNames.includes(f.name)) : []
			const added = newValue.length ? newValue.filter(f => !oldValuesNames.includes(f.name)) : []

			removed.length&&removed.forEach(value => {
				const elem = document.getElementById('item-' + value.name);
				elem&&this.grid.remove(elem, {removeElements: true});
			})

			this.$nextTick()
			.then(() => {
				added.length&&added.forEach(value => {
					const elem = document.getElementById('item-' + value.name);
					elem&&this.grid.add(elem);
				})
			})
		},
		registerItemsPositions(gridItems) {
			const itemsList = gridItems.length ? gridItems.map(({_element}) => { return _element.id.replace("item-", "")}) : []

			if (itemsList.length) {
				frappe.xcall("frappe.desk.doctype.desk.desk.register_positions", {items: itemsList})
			}
		}
	}
}
</script>
<style lang='scss'>
.grid {
	width: 100%;
	position: relative;
	margin: 0 auto;
	height: 100%;
	.grid-item {
		padding: 5px;
		.item-content {
			background-color: #fff;
			border-radius: 4px;
			box-shadow: 0 1px 3px 0 #e6ebf1;
		}
	}
}

.empty-grid {
	border-radius: 4px;
	border: 1px dashed #e6ebf1;
	height: 100%;
	width: 100%;
	p {
		position: relative;
		top: 50%;
		transform: translateY(-50%);
	}
}

.remove-icon {
	float: right;
	padding: 5px;
	color: #6c7680;
	cursor:pointer;
}
</style>