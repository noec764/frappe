<template>
	<dialog
		:open="isVisible ? 'open' : null"
		:class="classObject"
		:style="styleObject"
		@keydown="(event) => (event.key === 'Escape') && hide()"
	>
		<div class="QAM-close-backdrop" @click="hide" :aria-label="__('Close')"></div>

		<div class="QAM-modal">
			<header style="grid-area: title; position: relative; padding: 1em; padding-bottom: 0;">
				<a href="/app" style="position: absolute;" @click="hide()" v-if="frappe.get_route() && frappe.get_route().length && frappe.get_route()[0]">
					<img style="width: 24px" :src="frappe.boot.app_logo_url" />
				</a>
				<h2 style="text-align: center; margin: 0; font-size: 1em;">
					{{ __('Quick Access') }}
				</h2>
			</header>

			<label class="QAM-filter-container my-5" style="grid-area: input;">
				<span class="sr-only visually-hidden">{{ __('Search') }}</span>
				<input
					ref="input"
					v-model="searchQuery"
					type="search"
					class="form-control"
					:placeholder="__('Search') + '...'"
					autocomplete="off"
					@keyup="(event) => (event.key === 'Enter') && onEnter()"
					@keydown="inputOnKeyDown"
				/>
				<span class="search-icon" v-html="frappe.utils.icon('search', 'md')"></span>
			</label>

			<div class="QAM-column QAM-sidebar" style="grid-area: side;">
				<!-- <h3 class="QAM-title" style="font-size: 1em; text-align: center;">{{ __('Workspace') }}</h3> -->

				<div class="QAM-scrollzone">
					<ul class="QAM-results" ref="workspaceResults" @keydown="listOnKeyDown">
						<quick-access-menu-item v-for="(item, index) in filteredItems" :key="index" :item="item" />
					</ul>
				</div>
			</div>

			<div class="QAM-column" style="grid-area: global;">
				<div class="QAM-scrollzone" ref="globalResults">
					<quick-access-menu-global-search :value="searchQuery" />
				</div>
			</div>

			<button class="QAM-close-button" @click="hide">
				<span class="sr-only visually-hidden">{{ __('Close') }}</span>
				<span v-html="frappe.utils.icon('close', 'lg')"></span>
			</button>
		</div>
	</dialog>
</template>

<script>
import { bus } from './bus'
import QuickAccessMenuItem from './QuickAccessMenuItem.vue'
import QuickAccessMenuGlobalSearch from './QuickAccessMenuGlobalSearch.vue'
import fuzzysort from './fuzzysort.min.js'

export default {
	name: 'QuickAccessMenu',

	components: {
		QuickAccessMenuItem,
		QuickAccessMenuGlobalSearch,
	},

	data() {
		return {
			items: [],
			anchor: 'center',
			dx: 0,
			dy: 0,
			isVisible: false,
			searchQuery: '',
		}
	},

	computed: {
		classObject() {
			return [
				'QuickAccessMenu',
				`QuickAccessMenu--anchor-${this.anchor}`
			]
		},
		styleObject() {
			return {
				"--x": this.dx + 'px',
				"--y": this.dy + 'px',
			}
		},
		filteredItems() {
			if (this.searchQuery === '') return this.items

			const removeAccents = str => str.normalize('NFD').replace(/[\u0300-\u036F]/g, '')

			const items = this.items.map((item) => ({
				...item,
				_search: removeAccents(__(item.label)),
			}))

			return fuzzysort.go(removeAccents(this.searchQuery), items, {
				key: '_search',
				limit: 30,
				// threshold: -1000, // don't return bad results
			}).map(res => ({
				...res.obj,
				_html: fuzzysort.highlight({ ...res, target: __(res.obj.label) }, '<mark>', '</mark>'),
			}))
		},
	},

	methods: {
		show() {
			this.isVisible = true
			this.clearInput()
			this.focusInput()
			bus.$emit('quick-access-shown')
		},
		hide() {
			this.isVisible = false
		},
		clearInput() {
			this.searchQuery = ''
		},
		focusInput() {
			this.$nextTick(() => this.$refs.input?.focus())
		},
		setPosition(opts) {
			const { anchor: _anchor = 'center', dx: _dx = 0, dy: _dy = 0 } = opts

			if (typeof _anchor !== 'string' || !_anchor.match(/^(center|fixed)$/))
				console.warn('quick-access-setPosition:', '`anchor` should be a string: accepted values are "center", "fixed". Got', _anchor)
			if (typeof _dx !== 'number')
				console.warn('quick-access-setPosition:', '`dx` should be a number, got', _dx)
			if (typeof _dy !== 'number')
				console.warn('quick-access-setPosition:', '`dy` should be a number, got', _dy)

			this.anchor = _anchor
			this.dx = _dx
			this.dy = _dy
		},
		onEnter() {
			const items = this.filteredItems
			if (this.searchQuery && items.length > 0) {
				bus.$emit('quick-access-selected', { item: items[0] })
			}
		},

		getFocusableElementIn(el) {
			if (!el) return null
			const q = ':is(a,button,input,select,textarea,[tabindex]):not(:disabled)'
			if (el.matches(q))
				return el
			return el.querySelector(q)
		},

		inputOnKeyDown(event) {
			if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown')
				return // guard clause

			event.preventDefault()
			event.stopPropagation()

			const ul = this.$refs.workspaceResults
			if (!ul) return
			if (ul.childElementCount === 0) return

			const getFocusable = li => this.getFocusableElementIn(li)
			if (event.key === 'ArrowDown') {
				getFocusable(ul.firstElementChild)?.focus()
			} else if (event.key === 'ArrowUp') {
				getFocusable(ul.lastElementChild)?.focus()
			}
		},

		listOnKeyDown(event) {
			if (event.key === 'ArrowRight') {
				const el = this.getFocusableElementIn(this.$refs.globalResults)
				if (el) { el.focus() }
				return
			}

			if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') {
				if (event.key.length === 1 && event.key !== " ")  {
					// this.searchQuery += event.key
					this.focusInput()
				}
				return // guard clause
			}

			event.preventDefault()
			event.stopPropagation()

			const el = event.target // document.activeElement
			const li = el.closest('li')

			const getFocusable = li => this.getFocusableElementIn(li)

			if (event.key === 'ArrowDown') {
				const next = getFocusable(li.nextElementSibling)
				if (next) {
					return next.focus()
				}
			} else if (event.key === 'ArrowUp') {
				const prev = getFocusable(li.previousElementSibling)
				if (prev) {
					return prev.focus()
				}
			}

			this.focusInput()
		}
	},

	created() {
		bus.$on('quick-access-setItems', (data) => {
			this.items = data
		})

		bus.$on('quick-access-show', () => this.show())
		bus.$on('quick-access-hide', () => this.hide())

		bus.$on('quick-access-setPosition', (opts = {}) => {
			this.setPosition(opts)
		})

		bus.$on('quick-access-showAt', (opts = {}) => {
			this.setPosition(opts)
			this.show()
		})

		bus.$on('quick-access-setItems', (data) => { this.items = data })

		bus.$on('quick-access-selected', ({ item, allow = {} } = {}) => {
			if (item === null) return this.hide()

			if (!item || typeof item !== 'object') throw new TypeError('`item` should be an object')

			const isAllowed = (key, defaultValue) => (allow[key] === undefined || allow[key] === null) ? defaultValue : allow[key]

			const action = item.action || item.callback
			if (action && isAllowed('action', true) && typeof action === 'function') {
				action()
			}

			const route = item.href || item.route
			if (route && isAllowed('href', true)) {
				if (typeof route === 'string' && route.match('^https?://')) {
					window.location.href = route
				} else {
					frappe.router.set_route(route)
				}
			}

			this.hide()
		})
	}
}
</script>

<style>
.QuickAccessMenu {
	z-index: 1050;
	position: relative;

	background: none;
	color: inherit;
	margin: 0px;
	padding: 0px;
	border: none;
}

.QuickAccessMenu:not([open]) {
	display: none;
}

.QuickAccessMenu[open] {
	animation: fade-in 200ms ease;
}

@keyframes fade-in {
	from {
		opacity: 0;
	}
}

.QuickAccessMenu--anchor-fixed {
	position: fixed;
	left: var(--x, 0px);
	top: var(--y, 0px);
}

.QuickAccessMenu--anchor-center {
	position: fixed;

	display: grid;
	align-items: center;
	justify-content: center;

	top: 0px;
	left: 0px;
	width: 100%;
	height: 100%;
	background: none;

	align-items: flex-start;
	margin-top: calc(100vh / 6);
}

.QAM-modal {
	overflow: hidden;
	position: relative;

	background: var(--modal-bg, white);
	color: var(--text-color, black);
	box-shadow: var(--modal-shadow, 1px 0 3px 2px rgba(0, 0, 0, 0.1));

	/* border: 1px solid var(--text-muted, black); */
	border-radius: 9px;

	max-width: 96vw;
	width: 700px;
	max-height: 60vh; /* fixed height */
	height: 600px;

	display: grid;
	grid-template-columns: 1fr 1fr 1fr;
	grid-template-rows: auto auto 1fr;
	gap: 0px 0px;
	grid-auto-flow: row;
	grid-template-areas:
		"title title title"
		"input input input"
		"side global global";
}

.QAM-column {
	display: flex;
	flex-direction: column;
	/* justify-content: flex-start;
	align-items: flex-start; */
	max-height: 100%;
	min-height: 100%;
}


.QAM-title {
	min-height: 48px;
	display: block;
	text-align: left;
	font-weight: 600;
	margin: 0;
	padding: 1em;
}


.QAM-scrollzone {
	overflow-x: hidden;
	overflow-x: clip;
	overflow-y: auto;
	overscroll-behavior: contain;
	flex: 1;
	position: relative;
}
.QAM-scrollzone::after {
	display: block;
	content: ' ';
	position: sticky;
	left: 0;
	bottom: 0;
	width: 100%;
	height: 16px;
	background: linear-gradient(0deg, var(--modal-bg, white), transparent);
}

.QAM-results {
	display: flex;
	flex-direction: column;
	justify-content: flex-start;
	align-items: stretch;
	flex-wrap: nowrap;
	gap: 2px;

	margin: 0;
	padding: 8px;
	list-style: none;
}
.QAM-results > li {
	margin: 0;
	padding: 0;
	display: block;
}

.QAM-filter-container {
	display: block;
	margin: 0;
	padding: 1rem;
	position: relative
}
.QAM-filter-container input {
	padding: 1rem;
	padding-left: 3rem;
	line-height: 1;
	font-size: 1.4rem !important;
	width: 100%;
	height: auto;
}
.QAM-filter-container .search-icon {
	position: absolute;
	top: 0;
	left: 1rem;
	width: 3rem;
	height: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
}


.QAM-close-button {
	background: none;
	border: none;
	color: inherit;

	position: absolute;
	top: 0;
	right: 0;
	width: 48px;
	height: 48px;
}
.QAM-close-backdrop {
	position: fixed;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	background: black;
	pointer-events: all;
	opacity: 0.3;
	transition: opacity 600ms ease;
}

.QuickAccessMenu--anchor-fixed .QAM-close-backdrop {
	opacity: 0.2;
}


@media screen and (max-width: 768px), (pointer: coarse) {
	.QuickAccessMenu {
		position: fixed;

		display: grid;
		align-items: center;
		justify-content: center;

		top: 0px;
		left: 0px;
		width: 100%;
		height: 100%;
		background: none;

		align-items: flex-start;
		margin: 0px;
	}

	.QAM-modal {
		margin-top: 2vw; /* the VW unit is intentional */
		max-height: 96vh;
		height: 96vh;

		display: block;
		overflow-y: scroll;
		overscroll-behavior: contain;
	}

	.QAM-sidebar {
		border-right: none;
	}

	.QAM-scrollzone {
		overflow: visible;
	}

	.QAM-scrollzone::after {
		display: none;
	}

	.QAM-column {
		min-height: unset;
		max-height: unset;
	}

	.QAM-column:not(:last-of-type) {
		margin-bottom: 1em;
	}

	.QAM-title {
		display: none;
	}
}
</style>
