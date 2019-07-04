<template>
	<div
		class="vsm-item"
		:class="[{'first-item' : firstItem}]"
		@mouseenter="mouseEnter($event)"
		@touchend="touchEnd($event)"
	>
		<template>
			<a
			class="vsm-link"
			:href="item.type === 'module' ? '#modules/' + item.module_name : item.link"
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
		</template>
	</div>
</template>

<script>
import { animationMixin } from './mixin'
export default {
	mixins: [animationMixin],
	props: {
		item: {
			type: Object,
			required: true
		},
		firstItem: {
			type: Boolean,
			default: false
		},
		isCollapsed: {
			type: Boolean
		}
	},
	methods: {
		mouseEnter(event) {
			if (this.isCollapsed && this.firstItem) {
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
			if (this.isCollapsed && this.firstItem) {
				this.$parent.$emit('touchEndItem')
			}
		}
	}
}
</script>