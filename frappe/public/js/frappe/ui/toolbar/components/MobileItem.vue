<template>
  <div
	v-if="item"
	class="vsm-item mobile-item"
	:class="[{'active-item' : active}]"
  >
	  <a
		class="vsm-link"
		:href="item.type === 'module' ? '#modules/' + item.module_name : item.link"
	  >
		<i
			v-if="item.icon"
			class="vsm-icon"
			:class="item.icon"
		/>
		{{ item.label }}
	  </a>
  </div>
</template>

<script>
export default {
	props: {
		item: {
			type: Object,
			default: null
		}
	},
	data() {
		return {
			active: false
		}
	},
	watch: {
		item () {
			this.active = true
		}
	}
}
</script>