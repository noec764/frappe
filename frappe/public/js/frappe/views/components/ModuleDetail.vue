<template>
	<div>
		<div v-if="sections.length" class="sections-container" :class="dashboard ? 'top-border': ''">
			<div v-for="section in sections"
				:key="section.label"
				class="border section-box"
			>
				<h4 class="h4"> {{ section.label }} </h4>
				<module-link-item v-for="(item, index) in section.items"
					:key="index"
					:data-youtube-id="item.type==='help' ? item.youtube_id : false"
					v-bind="item"
					:open_count="item.type==='doctype' ? frappe.boot.notification_info.open_count_doctype[item.doctype] : false"
				>
				</module-link-item>
			</div>
		</div>

		<div v-else class="sections-container">
			<div v-for="n in 3" :key="n" class="skeleton-section-box"></div>
		</div>
	</div>
</template>

<script>
import ModuleLinkItem from "./ModuleLinkItem.vue";

export default {
	components: {
		ModuleLinkItem
	},
	props: ['module_name', 'sections', 'dashboard']
}
</script>
<style lang="less" scoped>
.sections-container {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
	column-gap: 15px;
	row-gap: 15px;
	padding-top: 20px;
}

.top-border {
	border-top: 1px solid #e6ebf1;
}

.section-box {
	padding: 5px 20px;
	border-radius: 4px;
	background-color: #fff;
	box-shadow: 0 1px 3px 0 #e6ebf1;
}

.skeleton-section-box {
	background-color: #f5f7fa;
	height: 250px;
	border-radius: 4px;
}

.h4 {
	font-size: 18px;
	margin-bottom: 15px;
}

</style>
