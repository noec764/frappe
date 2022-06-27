<template>
	<form class="QAMGlobalSearchResults" role="search" onsubmit="return false;">
		<!-- <div class="input-group search-bar">
			<input
				ref="input"
				:id="searchBarId"
				type="text"
				class="form-control"
				:placeholder="__('Search or type a command (Ctrl + G)')"
				aria-haspopup="true"
			/>
			<span class="search-icon">
				<svg class="icon icon-sm"><use xlink:href="#icon-search"></use></svg>
			</span>
		</div> -->

		<div ref="wrapper"></div>

		<input :value="value" type="search" style="display: none;" disabled ref="input" />
	</form>
</template>

<script>
class SearchThing extends frappe.search.SearchDialog {
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
		window.z = this
	}

	make() {
		// this.search_dialog = new frappe.ui.Dialog({
		// 	minimizable: true,
		// 	size: "large"
		// });
		// this.set_header();
		this.$wrapper = $(this.opts.wrapperElement).addClass(
			"search-dialog"
		);
		// this.$body = $(this.search_dialog.body);
		// this.$body = this.$wrapper.append('<div>Body</div>');
		this.$body = this.$wrapper;
		// this.$input = this.$wrapper.find(".search-input");
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
		// this.$input.attr("placeholder", __(this.search.input_placeholder));
		this.get_results(keywords);
		// this.search_dialog.show();
		// this.$input.val(keywords);
		// setTimeout(() => this.$input.select(), 500);
	}

	__parse_results(result_sets, keyword) {
		result_sets = result_sets.filter(function(set) {
			return set.results.length > 0;
		});
		// if (result_sets.length > 0) {
			this.render_data(result_sets);
		// } else {
		// 	this.put_placeholder(this.search.no_results_status(keyword));
		// }
	}

	render_data(result_sets) {
		const $search_results = $('<div class="search-results"></div>');
		const $results_area = $search_results.append('<div class="results-area"></div>');
		// let $search_results = $(frappe.render_template("search")).addClass("hide");
		// let $sidebar = $search_results.find(".search-sidebar").empty();
		// let sidebar_item_html =
		// 	'<li class="search-sidebar-item standard-sidebar-item list-link" data-category="{0}">' +
		// 	'<a><span class="ellipsis">{1}</span></a></li>';

		this.modal_state = 0;
		this.full_lists = {
			"All Results": $('<div class="results-summary"></div>')
		};
		this.nav_lists = {};

		result_sets.forEach(set => {
			// $sidebar.append($(__(sidebar_item_html, [set.title, __(set.title)])));
			this.add_section_to_summary(set.title, set.results);
			this.full_lists[set.title] = this.render_full_list(
				set.title,
				set.results,
				set.fetch_type
			);
		});

		// if (result_sets.length > 1) {
		// 	$sidebar.prepend($(__(sidebar_item_html, ["All Results", __("All Results")])));
		// }

		this.update($search_results.clone());
		// this.$body
		// 	.find(".list-link")
		// 	.first()
		// 	.trigger("click");

		this.$body.find(".results-area").empty().html(this.full_lists['All Results']);
	}

	add_section_to_summary(type, results) {
		let section_length = 4;
		let more_html = "";
		let get_result_html = result => this.render_result(type, result);

		/* if (results.length > section_length) {
			more_html = `<div>
				<a class="section-more" data-category="${type}">${__("More")}</a>
			</div>`;
		} */

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


import { bus } from './bus'

export default {
	name: 'QuickAccessMenuSearchBarAlt',
	
	props: {
		value: { type: String, default: '' },
	},

	data() {
		const searchBarId = "search-bar-" + Math.random().toString(16).substring(2)
		return {
			searchBarId,
			// awesomeBar: new frappe.search.AwesomeBar(),
			searchThing: null,
		}
	},

	watch: {
		value() {
			this.searchThing.get_results(this.value);
		},
	},

	mounted() {
		const inputElement = this.$refs.input
		const wrapperElement = this.$refs.wrapper
		const callback = () => bus.$emit('quick-access-selected', { item: null })
		this.searchThing = new SearchThing({ inputElement, wrapperElement, callback })
		this.searchThing.init_search(this.value, 'global_search');
		this.$nextTick(() => this.searchThing.get_results(''))

		// this.awesomeBar.setup("#" + this.searchBarId)

		bus.$on('quick-access-shown', () => this.searchThing.get_results(this.value));
	},
}
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
