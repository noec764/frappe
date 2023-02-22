frappe.provide("frappe.ui");

frappe.ui.FloatingButton = class FloatingButton {
	constructor(id, className = "") {
		if (!id) {
			throw new Error("FloatingButton: ID is required");
		}
		this.id = id;
		this.className = className;
		this.make();
	}

	make() {
		document.getElementById(this.id)?.remove();

		this.btn = $(document.body)
			.append(
				`
			<button class="btn btn-primary btn-lg btn-fab shadow-sm ${this.className}" id="${this.id}"></button>
			<style>
				.btn-fab {
					position: fixed;
					bottom: 1rem;
					left: 1rem;
					z-index: 100;
					border-radius: 999px;
					display: flex;
					align-items: center;
					justify-content: center;
					gap: 0.5rem;
				}
				.btn-fab .icon {
					margin-left: -0.5rem;
				}
			</style>
		`
			)
			.find(".btn-fab");
		this.btn.hide();
	}

	on(eventName, callback) {
		this.btn.on(eventName, callback);
		return this;
	}

	set({ label, icon }) {
		this.btn.empty();
		if (icon) {
			this.btn.append(frappe.utils.icon(icon, "lg"));
		}
		this.btn.append($("<span>").text(label));
		return this;
	}

	show() {
		this.btn.show();
		return this;
	}

	hide() {
		this.btn.hide();
		return this;
	}
};

export default frappe.ui.FloatingButton;
