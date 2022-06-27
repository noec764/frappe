<template>
	<li class="QuickAccessMenuItem">
		<component
			:is="href ? 'a' : 'button'"
			class="QAMI-box"
			tabindex="0"
			:href="href"
			:title="__(label)"
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

<script>
import { bus } from './bus'

export default {
	name: 'QuickAccessMenuItem',

	props: {
		item: {
			type: Object,
			required: true,
			validator: (x) => {
				if (!x.label) {
					console.warn('QuickAccessMenuItem', 'item.label is required.', 'Got item =', x)
					return false
				}
				return true
			},
		},
	},

	computed: {
		label() {
			if (typeof this.item.label === 'string') {
				return this.item.label
			}
			if (typeof this.item.title === 'string') {
				return this.item.title
			}
			if (typeof this.item.name === 'string') {
				return this.item.name
			}
		},
		href() {
			if (Array.isArray(this.item.route)) {
				return frappe.router.make_url(this.item.route)
			}
			if (typeof this.item.route === 'string') {
				return this.item.route
			}
			if (typeof this.item.href === 'string') {
				return this.item.href
			}
			return undefined
		},
	},

	methods: {
		onSelect() {
			bus.$emit('quick-access-selected', {
				item: this.item,
				allow: {
					action: true,
					href: this.item.href ? false : true, // don't repeat the link navigation action
				},
			})
		},
	}
}
</script>

<style>
.QuickAccessMenuItem {
}

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

.QAMI-label {
	/* color: var(--item-color, inherit); */
}
</style>
