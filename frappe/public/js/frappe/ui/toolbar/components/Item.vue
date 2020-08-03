<template>
	<div
		class="dodock-sidebar-item"
		@mouseenter="mouseEnter($event)"
		@touchend="touchEnd($event)"
		@click="itemClick"
	>
		<a
			class="dodock-sidebar-link"
			:href="'#workspace/' + item.name"
		>
			<i
				v-if="item.icon"
				class="dodock-sidebar-icon"
				:class="item.icon"
				:style="{color: item.color}"
			/>
			<template v-if="!isCollapsed">
				<span class="dodock-sidebar-title">{{ item.label }}</span>
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
		},
		itemClick() {
			this.$emit('itemClick');
		}
	}
}
</script>