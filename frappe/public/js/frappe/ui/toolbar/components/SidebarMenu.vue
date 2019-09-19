<template>
	<div
		class="v-sidebar-menu"
		:class="[!isCollapsed ? 'vsm-default' : 'vsm-collapsed']"
		:style="{'width': sidebarWidth}"
		@mouseleave="mouseLeave"
		@wheel="onWheel"
	>
		<div class="vsm-list" id="sidebard-modules-list">
			<template v-for="(item, index) in modules">
				<item
					:key="index"
					:item="item"
					:first-item="true"
					:is-collapsed="isCollapsed"
				/>
			</template>
		</div>
		<div
			v-if="isCollapsed"
			:style="[{'position' : 'absolute'}, {'top' : `${mobileItemPos}px`}, {'left' : '0px'}, {'z-index' : 30}, {'width' : width}]"
		>
			<mobile-item :item="mobileItem" />
			<transition name="slide-animation">
				<div
				v-if="mobileItem"
				class="vsm-mobile-bg"
				:style="[{'position' : 'absolute'}, {'left' : '0px'}, {'right' : '0px'}, {'top' : '0px'}, {'height' : `${mobileItemHeight}px`}]"
				/>
			</transition>
		</div>
		<button
			class="collapse-btn"
			@click="toggleCollapse"
		/>
	</div>
	
</template>

<script>
import Item from './Item.vue'
import MobileItem from './MobileItem.vue'
import { animationMixin } from './mixin'
export default {
	name: 'SidebarMenu',
	components: {
		Item,
		MobileItem
	},
	mixins: [animationMixin],
	props: {
		widthCollapsed: {
			type: String,
			default: '50px'
		}
	},
	data () {
		return {
			isCollapsed: true,
			closeTimeout: null,
			activeShow: null,
			modules: [],
			mobileItem: null,
			mobileItemPos: null,
			mobileItemHeight: null,
			width: '250px'
		}
	},
	computed: {
		sidebarWidth () {
			return this.isCollapsed ? this.widthCollapsed : this.width
		}
	},
	watch: {
		collapsed (val) {
			this.isCollapsed = val
		}
	},
	created () {
		this.$on('mouseEnterItem', (val) => {
			this.mobileItem = null
			this.$nextTick(() => {
				this.mobileItem = val.item;
				this.mobileItemPos = val.pos;
				this.mobileItemHeight = val.height;
			})
		})

		this.$on('touchEndItem', () => {
			setTimeout(() => {
				this.mobileItem=null
			}, 1000);
		})
	},
	mounted() {
		this.getModules();
	},
	methods: {
		mouseLeave () {
			this.mobileItem = null
		},
		toggleCollapse () {
			this.isCollapsed = !this.isCollapsed
			frappe.sidebar_update.trigger('collapse', this.sidebarWidth);
		},
		onItemClick (event, item) {
			this.$emit('itemClick', event, item)
		},
		getModules() {
			this.modules = frappe.boot.allowed_modules.sort(dynamicSort("label"));

			let maxLength = 0
			this.modules.forEach(item => {
				maxLength = item.label.length > maxLength ? item.label.length : maxLength;
			})

			this.width = (maxLength * 10) + "px";
		},
		onWheel(e) {
			const list = this.$el.querySelector("#sidebard-modules-list")
			list.scrollBy(0, e.deltaY)
		}
	}
}

function dynamicSort(property) {
	var sortOrder = 1;

	if(property[0] === "-") {
		sortOrder = -1;
		property = property.substr(1);
	}

	return function (a,b) {
		if(sortOrder == -1){
			return b[property].localeCompare(a[property]);
		}else{
			return a[property].localeCompare(b[property]);
		}
	}
}
</script>

<style lang="scss">
@import './sidebar.scss';
</style>