// Copyright (c) 2023, Dokos SAS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Summary Card", {
	setup(frm) {
		frm.set_query("dt", function () {
			return {
				filters: {
					istable: 0,
					issingle: 0,
				},
			};
		});
	},

	refresh(frm) {
		frm.trigger("update_view_options");

		if (!frm.doc.__islocal) {
			frm.trigger("render_block");
		}
	},

	dt(frm) {
		frm.trigger("update_view_options");
	},

	async update_view_options(frm) {
		if (!frm.doc.dt) {
			return;
		}
		const views = await frappe.model.get_views_of_doctype(frm.doc.dt);
		if (!views?.length) {
			return;
		}
		frm.set_df_property("button_view", "options", ["", ...views]);
	},

	render_fallback(frm) {
		frm.call("get_data").then((r) => {
			frm.set_intro("");
			let html = "";
			for (const section of r.message.sections) {
				html += "<b>" + (section.label || section.type || "") + "</b>";
				html += "<ul>";
				for (const row of section.items) {
					const inner = __("{0}: {1}", [row.label, row.badge]);
					html += "<li>" + inner + "</li>";
				}
				html += "</ul>";
			}
			frm.set_intro(html);
		});
	},

	async render_block(frm) {
		const Renderer = frappe?.workspace_block?.blocks?.summary_card?._Renderer;

		if (!Renderer) {
			frm.trigger("render_fallback");
			return;
		}

		frm.set_intro("");

		const id = "summary-card-" + frm.doc.name;
		const existing = document.getElementById(id);
		if (existing) {
			existing.remove();
		}

		const skeleton = document.createElement("div");
		skeleton.innerHTML = `
			<div class="widget summary-card" id="${id}">
				<div class="widget-head">
					<div class="sc-row sc-header"></div>
					<div class="widget-control"></div>
				</div>
				<div class="widget-body sc-body"></div>
				<div class="widget-footer"></div>
			</div>
		`;
		const wrapper = skeleton.firstElementChild;
		Object.assign(wrapper.style, {
			width: "max-content",
			height: "max-content",
		});

		const $wrapper = $(wrapper);
		const $header = $wrapper.find(".sc-header");
		const $body = $wrapper.find(".sc-body");
		const $footer = $wrapper.find(".widget-footer");
		const $controls = $wrapper.find(".widget-control");
		const renderer = new Renderer({
			wrapper,
			$header,
			$body,
			$footer,
			$controls,
			summary_card_name: frm.doc.name,
			set_name: () => {},
		});
		await renderer.render();

		// frm.set_intro(wrapper.innerHTML);
		frm.fields_dict.preview_html.$wrapper.html(wrapper);
	},
});
