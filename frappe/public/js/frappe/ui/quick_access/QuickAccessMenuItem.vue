<template>
	<li class="QuickAccessMenuItem">
		<component
			:is="href ? 'a' : 'button'"
			class="QAMI-box"
			tabindex="0"
			:href="href"
			:title="__(item.title)"
			@click="onSelect()"
			:style="{'--item-color': item.color}"
		>
			<span
				class="QAMI-icon"
				:item-icon="item.icon || 'folder-normal'"
				:style="item.color && ('--icon-fill:' + item.color)"
				v-html="frappe.utils.icon(item.icon || 'folder-normal', 'md')"
			></span>

			<span v-if="item._html" class="QAMI-label" v-html="item._html"></span>
			<span v-else class="QAMI-label">{{ __(label) }}</span>
		</component>
	</li>
</template>

<script setup>
import { bus } from './bus'

const props = defineProps({
	item: {
		type: Object,
		required: true,
		validator: (x) => {
			if (!x.title) {
				console.warn('QuickAccessMenuItem', 'item.title is required.', 'Got item =', x)
				return false
			}
			return true
		},
	},
})

const label = computed(() => {
	if (typeof props.item.title === 'string') {
		return props.item.title
	}
	if (typeof props.item.name === 'string') {
		return props.item.name
	}
})

const href = computed(() => {
	if (Array.isArray(props.item.route)) {
		return frappe.router.make_url(props.item.route)
	}
	if (typeof props.item.route === 'string') {
		return props.item.route
	}
	if (typeof props.item.href === 'string') {
		return props.item.href
	}
	return undefined
})

const onSelect = () => {
	bus.$emit('quick-access-selected', {
		item: props.item,
		allow: {
			action: true,
			href: props.item.href ? false : true, // don't repeat the link navigation action
		},
	})
}
</script>

<style>
.QAMI-box {
	display: flex;
	flex-direction: row;
	justify-content: flex-start;
	align-items: center;
	gap: 0.25em;

	border-radius: 5px;
	padding: 3px;
	margin: 0px;

	box-shadow: 0 0 0 0px rgba(77, 144, 254, 0);

	transition: all 150ms ease;
	transition-property: box-shadow, background-color;
}

button.QAMI-box {
	border: none;
	background: none;
	width: 100%;
	text-align: initial;
	outline: none;
}

a.QAMI-box {
	text-decoration: none !important;
	outline: none;
}

.QuickAccessMenuItem:focus-within > .QAMI-box,
.QuickAccessMenuItem:hover > .QAMI-box {
	text-decoration: none;
	/* background-color: var(--fg-hover-color); */
	background-color: rgba(77, 144, 254, 0.1);

	/* box-shadow: 0 0 0 2px currentColor; */
	/* box-shadow: var(--checkbox-focus-shadow); */
	box-shadow: 0 0 0 2px rgba(77, 144, 254, 1);
}

.QuickAccessMenuItem:focus-within > .QAMI-box > .QAMI-label,
.QuickAccessMenuItem:hover > .QAMI-box > .QAMI-label {
	text-decoration: underline;
}
</style>
