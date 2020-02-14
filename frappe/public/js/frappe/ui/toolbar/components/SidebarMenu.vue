<template>
	<div>
		<div
			class="v-sidebar-menu hidden-sm hidden-xs"
			:class="[!isCollapsed ? 'vsm-default' : 'vsm-collapsed']"
			:style="[{'width': sidebarWidth}, mobileDisplay ? {'display': 'block !important'} : '']"
			@mouseenter="mouseEnter"
			@mouseleave="mouseLeave"
			@wheel="onWheel"
			@scroll="measureScroll"
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
			<button
				class="collapse-btn"
				:class="goToTop ? 'up-btn' : 'down-btn'"
				@click="scrollUpDown"
			/>
		</div>
		<div v-if="mobileDisplay" class="vsm-list-overlay" @click="mobileCollapse"></div>
	</div>
</template>

<script>
import Item from './Item.vue'
export default {
	name: 'SidebarMenu',
	components: {
		Item
	},
	data () {
		return {
			isCollapsed: true,
			modules: [],
			width: '250px',
			widthCollapsed: '50px',
			mobileDisplay: false,
			goToTop: false
		}
	},
	created() {
		frappe.sidebar_update.on('toggle_mobile_menu', () => {
			this.mobileDisplay ? this.mobileCollapse() : this.mobileExpand()
		})

		frappe.sidebar_update.on('close_mobile_menu', () => {
			this.mobileCollapse()
		})
	},
	computed: {
		sidebarWidth () {
			return this.isCollapsed ? this.widthCollapsed : this.width
		}
	},
	mounted() {
		this.getModules();
	},
	methods: {
		mouseLeave () {
			this.isCollapsed = this.mobileDisplay ? false : true;
		},
		mouseEnter () {
			this.isCollapsed = false;
		},
		mobileExpand () {
			this.isCollapsed = false;
			this.mobileDisplay = true;
		},
		mobileCollapse() {
			this.mobileDisplay = false;
		},
		getModules() {
			this.modules = frappe.boot.allowed_modules.sort(dynamicSort("label"));

			const maxLength = this.modules.reduce((acc, item) => {
				return item.label.length > acc ? item.label.length : acc;
			}, 0)

			this.width = ((maxLength > 25) ? (maxLength * 10) : (maxLength * 11)) + "px";
		},
		scrollUpDown() {
			const scrollHeight = document.querySelector("#sidebard-modules-list").scrollHeight
			this.onWheel({
				deltaY: this.goToTop ? -scrollHeight : scrollHeight
			}, true)
			this.goToTop = !this.goToTop
		},
		onWheel(e, smooth=false) {
			const list = this.$el.querySelector("#sidebard-modules-list")
			smooth ? list.scrollBy({top: e.deltaY, left: 0, behavior: 'smooth'}) :
				list.scrollBy(0, e.deltaY)

			this.measureScroll()
		},
		measureScroll() {
			const list = this.$el.querySelector("#sidebard-modules-list")
			if (list.clientHeight + list.scrollTop >= list.scrollHeight) {
				this.goToTop = true
			} else {
				this.goToTop = false
			}
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