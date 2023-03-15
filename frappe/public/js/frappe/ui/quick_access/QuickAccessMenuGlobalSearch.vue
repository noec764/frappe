<template>
	<form class="QAMGlobalSearchResults" role="search" onsubmit="return false;">
		<div ref="wrapperElement"></div>
		<input :value="value" type="search" style="display: none;" disabled ref="inputElement" />
	</form>
</template>

<script setup>
import { bus } from './bus'
import { ref, onMounted, watch } from 'vue'

class StubSearchDialog extends frappe.search.SearchDialog {
	constructor(opts = {}) {
		if (!(opts.inputElement instanceof HTMLElement)) {
			throw new TypeError('opts.inputElement should be an HTMLElement');
		}
		if (!(opts.wrapperElement instanceof HTMLElement)) {
			throw new TypeError('opts.wrapperElement should be an HTMLElement');
		}
		if (typeof opts.callback !== 'function') {
			throw new TypeError('opts.callback should be a function');
		}
		super({ opts });
	}

	make() {
		this.$wrapper = $(this.opts.wrapperElement).addClass(
			"search-dialog"
		);

		this.$body = this.$wrapper;

		this.$input = $(this.opts.inputElement);
		this.setup();
	}

	setup() {
		super.setup();
		this.$body.on("click", ".result", e => {
			this.opts.callback(e);
		})
	}

	set_header() {}

	init_search(keywords, search_type) {
		this.search = this.searches[search_type];

		this.get_results(keywords);
	}

	render_data(result_sets) {
		const $search_results = $('<div class="search-results"></div>');
		const $results_area = $search_results.append('<div class="results-area"></div>');

		this.modal_state = 0;
		this.full_lists = {
			"All Results": $('<div class="results-summary"></div>')
		};
		this.nav_lists = {};

		result_sets.forEach(set => {
			this.add_section_to_summary(set.title, set.results);
			this.full_lists[set.title] = this.render_full_list(
				set.title,
				set.results,
				set.fetch_type
			);
		});

		this.update($search_results.clone());

		this.$body.find(".results-area").empty().html(this.full_lists['All Results']);
	}

	add_section_to_summary(type, results) {
		let section_length = 4;
		let more_html = "";
		let get_result_html = result => this.render_result(type, result);

		// if (results.length > section_length) {
		// 	more_html = `<div>
		// 		<a class="section-more" data-category="${type}">${__("More")}</a>
		// 	</div>`;
		// }

		let $result_section = $(`<div class="col-sm-12 result-section" data-type="${type}">
			<div class="result-title">${__(type)}</div>
			<div class="result-body">
				${more_html}
			</div>
		</div>`).appendTo(this.full_lists["All Results"]);

		$result_section
			.find(".result-body")
			.prepend(results.slice(0, section_length).map(get_result_html));
	}
}

const props = defineProps({
	value: { type: String, default: '' },
})

const searchThing = ref(null)
const inputElement = ref(null)
const wrapperElement = ref(null)

onMounted(() => {
	const callback = () => bus.$emit('quick-access-selected', { item: null })
	const stub = new StubSearchDialog({
		inputElement: inputElement.value,
		wrapperElement: wrapperElement.value,
		callback,
	})

	searchThing.value = stub
	stub.init_search(props.value, 'global_search');

	bus.$on('quick-access-shown', () => searchThing.value.get_results(props.value));
})

// Watchers
watch(() => props.value, () => {
	searchThing.value.get_results(props.value);
})
</script>

<style>
.QAMGlobalSearchResults .result {
	padding: 3px !important;
	border-radius: 5px;
	box-shadow: 0 0 0 0px rgba(77, 144, 254, 0);
	transition: all 150ms ease;
	transition-property: box-shadow, background-color;
}
.QAMGlobalSearchResults .result:hover, .QAMGlobalSearchResults .result:focus-within {
	background-color: rgba(77, 144, 254, 0.1);
	box-shadow: 0 0 0 2px rgba(77, 144, 254, 1);
	text-decoration: underline;
}

.QAMGlobalSearchResults a.result-section-link {
	text-decoration: none !important;
	outline: none;
}
.QAMGlobalSearchResults button.result-section-link {
	border: none;
	background: none;
	width: 100%;
	text-align: initial;
	outline: none;
}
</style>
