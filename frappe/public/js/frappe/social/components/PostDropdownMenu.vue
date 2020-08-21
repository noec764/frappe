<template>
	<div>
		<span class="caret cursor-pointer dropdown-toggle" data-toggle="dropdown"></span>
		<div class="dropdown-menu dropdown-menu-right">
			<a class="dropdown-item" @click="option.action" v-for="option in options" :key="option.label">{{option.label}}</a>
		</div>
	</div>
</template>
<script>
export default {
	props: ['options'],
}
</script>
<style lang="less" scoped>
.dropdown-menu {
	a {
		padding: 12px;
		font-size: 10px;
	}
}
</style>

