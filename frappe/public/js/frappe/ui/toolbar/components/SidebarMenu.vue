<template>
	<div>
		<div
		class="v-sidebar-menu hidden-sm hidden-xs"
		:class="[!isCollapsed ? 'dodock-sidebar-default' : 'dodock-sidebar-collapsed', isRTL ? 'rtl': '']"
		:style="[{'width': sidebarWidth}, mobileDisplay ? {'display': 'block !important'} : '', !showBottomButton ? {'padding-bottom': '20px'} : '']"
		@mouseenter="mouseEnter"
		@mouseleave="mouseLeave"
		@wheel="onWheel"
		@scroll="onWheel"
		>
		<draggable
			class="dodock-sidebar-list"
			id="sidebard-modules-list"
			ref="sidebarList"
			tag="div"
			v-model="modules"
			v-bind="dragOptions"
			@start="drag = true"
			@end="registerItems"
		>
			<transition-group type="transition" :name="!drag ? 'flip-list' : null">
				<template v-for="(item, index) in modules">
					<item
					:key="item.name + index"
					:item="item"
					:is-collapsed="isCollapsed"
					:customize-view="customizeView"
					@itemClick="itemClick"
					/>
				</template>
			</transition-group>
		</draggable>
		<button
			v-if="!mobileDisplay && showBottomButton"
			class="collapse-btn"
			:class="goToTop ? 'up-btn' : 'down-btn'"
			@click="scrollUpDown"
		/>
		</div>
	</div>
</template>

<script>
	import Item from "./Item.vue";
	import draggable from 'vuedraggable';

	export default {
	name: "SidebarMenu",
	components: {
		Item,
		draggable
	},
	props: {
		categories: {
			type: Array,
			default: () => []
		},
		pages: {
			type: Array,
			default: () => []
		},
	},
	data() {
		return {
			modules: this.pages,
			isCollapsed: true,
			width: "200px",
			widthCollapsed: "50px",
			mobileDisplay: false,
			customizeView: false,
			goToTop: false,
			isMounted: false,
			isRTL: frappe.utils.is_rtl(),
			drag: false
		};
	},
	created() {
		frappe.sidebar_update.on("toggle_mobile_menu", () => {
			this.mobileDisplay ? this.mobileCollapse() : this.mobileExpand();
		});

		frappe.sidebar_update.on("customize_sidebar", (r) => {
			this.customizeView = r;
			this.setIsCollapsed(!r);
		});
	},
	computed: {
		sidebarWidth() {
			return this.mobileDisplay
				? "100%"
				: this.isCollapsed
				? this.widthCollapsed
				: this.width;
		},
		showBottomButton() {
			if (this.isMounted) {
				return (
					this.modules.length * 50 > this.$refs.sidebarList.clientHeight - 35
				);
			}
		},
		dragOptions() {
			return {
				animation: 200,
				group: "description",
				disabled: !this.customizeView,
				ghostClass: "ghost"
			};
		}
	},
	mounted() {
		this.isMounted = true;
		const maxLength = this.modules.reduce((acc, item) => {
			return item.label.length > acc ? item.label.length : acc;
		}, 0);
		this.width = Math.max(maxLength > 25 ? maxLength * 10 : maxLength * 12, 200) + "px";
	},
	methods: {
		mouseLeave() {
			this.setIsCollapsed(this.mobileDisplay || this.customizeView ? false : true);
		},
		mouseEnter() {
			this.setIsCollapsed(false);
		},
		mobileExpand() {
			this.setIsCollapsed(false);
			this.mobileDisplay = true;
		},
		mobileCollapse() {
			this.mobileDisplay = false;
		},
		scrollUpDown() {
			const scrollHeight = document.querySelector("#sidebard-modules-list")
				.scrollHeight;
			this.onWheel(
				{
				deltaY: this.goToTop ? -scrollHeight : scrollHeight
				},
				true
			);
			this.goToTop = !this.goToTop;
		},
		onWheel(e, smooth = false) {
			const list = this.$el.querySelector("#sidebard-modules-list");
			smooth
				? list.scrollBy({ top: e.deltaY, left: 0, behavior: "smooth" })
				: list.scrollBy(0, e.deltaY);

			this.measureScroll();
		},
		measureScroll() {
			const list = this.$el.querySelector("#sidebard-modules-list");
			if (list.clientHeight + list.scrollTop >= list.scrollHeight) {
				this.goToTop = true;
			} else {
				this.goToTop = false;
			}
		},
		itemClick() {
			this.mobileDisplay && (this.mobileDisplay = !this.mobileDisplay);
		},
		setIsCollapsed(value) {
			this.isCollapsed = value;
			document.getElementsByClassName("page-container").forEach(elem => {
				elem.style.paddingLeft = `${this.isCollapsed ? "0px" : "calc(" + this.width + " - 40px)"}`;
			})
		},
		registerItems() {
			this.drag = false;
			frappe.sidebar_update.trigger('register_sidebar_items', {items: this.modules})
		}
	}
};
</script>

<style lang="scss">
@import "./sidebar.scss";

.flip-list-move {
  transition: transform 0.5s;
}

.no-move {
  transition: transform 0s;
}

.ghost {
  opacity: 0.5;
  background: #c8ebfb;
}
</style>