<template>
	<div>
		<div
			class="v-sidebar-menu hidden-sm hidden-xs"
			:class="[!isCollapsed ? 'vsm-default' : 'vsm-collapsed']"
			:style="[{'width': sidebarWidth}, mobileDisplay ? {'display': 'block !important'} : '', !showBottomButton ? {'padding-bottom': '20px'} : '']"
			@mouseenter="mouseEnter"
			@mouseleave="mouseLeave"
			@wheel="onWheel"
			@scroll="onWheel"
		>
			<div class="vsm-list" id="sidebard-modules-list" ref="sidebarList">
				<template v-for="(item, index) in modules">
					<item
						:key="index"
						:item="item"
						:is-collapsed="isCollapsed"
					/>
				</template>
			</div>
			<button
				v-if="!mobileDisplay && showBottomButton"
				class="collapse-btn"
				:class="goToTop ? 'up-btn' : 'down-btn'"
				@click="scrollUpDown"
			/>
		</div>
		<div v-if="mobileDisplay && !isCollapsed" class="vsm-list-overlay" @click="mobileCollapse"></div>
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
			goToTop: false,
			isMounted: false,
			timer: null
		}
	},
	created() {
		frappe.sidebar_update.on('toggle_mobile_menu', () => {
			this.mobileDisplay ? this.mobileCollapse() : this.mobileExpand()
		})
	},
	computed: {
		sidebarWidth () {
			return this.isCollapsed ? this.widthCollapsed : this.width
		},
		showBottomButton() {
			if (this.isMounted) {
				return (this.modules.length * 50) > (this.$refs.sidebarList.clientHeight - 35);
			}
		}
	},
	mounted() {
		this.isMounted = true;
		this.getModules();
		this.$refs.sidebarList.addEventListener("touchstart", this.handleTouchStart, false);
		this.$refs.sidebarList.addEventListener("touchend", this.handleTouchEnd, false);
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
			frappe.xcall("frappe.desk.desktop.get_desk_sidebar_items")
			.then(r => {
				this.modules = r

				const maxLength = this.modules.reduce((acc, item) => {
					return item.label.length > acc ? item.label.length : acc;
				}, 0)

				this.width = ((maxLength > 25) ? (maxLength * 10) : (maxLength * 12)) + "px";
			});
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
		},
		handleTouchStart(evt) {
			clearTimeout(this.timer);
			this.isCollapsed = false;
		},
		handleTouchEnd(evt) {
			this.timer = setTimeout(() => {
				this.isCollapsed = true;
			}, 1000);
		}
	}
}

</script>

<style lang="scss">
@import './sidebar.scss';
</style>