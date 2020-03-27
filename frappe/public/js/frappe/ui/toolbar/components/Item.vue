<template>
	<div
		class="vsm-item first-item"
		@mouseenter="mouseEnter($event)"
		@touchend="touchEnd($event)"
	>
		<a
			class="vsm-link"
			:href="'#workspace/' + item.name"
		>
			<i
				v-if="item.icon"
				class="vsm-icon"
				:class="item.icon"
				:style="{color: item.color}"
			/>
			<template v-if="!isCollapsed">
				<span class="vsm-title">{{ item.label }}</span>
			</template>
		</a>
	</div>
</template>

<script>
export default {
	props: {
		item: {
			type: Object,
			required: true
		},
		isCollapsed: {
			type: Boolean
		}
	},
	methods: {
		mouseEnter(event) {
			if (this.isCollapsed) {
				this.$parent.$emit('mouseEnterItem', {
					item: this.item,
					pos:
						event.currentTarget.getBoundingClientRect().top -
						this.$parent.$el.getBoundingClientRect().top,
						height: this.$el.offsetHeight
				})
			}
		},
		touchEnd(event) {
			if (this.isCollapsed) {
				this.$parent.$emit('touchEndItem')
			}
		}
	}
}
</script>