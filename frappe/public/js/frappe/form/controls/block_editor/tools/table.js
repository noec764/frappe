import Table from "@editorjs/table";

export default class DodockTable extends Table {
	render() {
		const wrapper = super.render();
		this._setWithJinja(this.data.withJinja);
		return wrapper;
	}

	constructor(arg) {
		super(arg);
		this.data.withJinja = arg.data.withJinja;
	}

	save() {
		const data = super.save();
		data.withJinja = Boolean(this.data.withJinja);
		return data;
	}

	_setWithJinja(v) {
		this.data.withJinja = Boolean(v);
		if (v) {
			this.container.classList.add("with-jinja");
		} else {
			this.container.classList.remove("with-jinja");
		}
	}

	_showJinjaHelp() {
		const help = new frappe.ui.Dialog({
			title: "Jinja Help",
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "help",
					options: __(
						`Use <code>{{ doc.items[i].amount }}</code>.<br> If a row contains an array access (<code>[i]</code>), it is used as a template and automatically repeated for each element of the underlying table.`
					),
				},
			],
		});
		help.show();
	}

	renderSettings() {
		let settings = super.renderSettings();
		settings = [
			...settings,
			{
				icon: frappe.utils.icon("uil uil-brackets-curly", "sm"),
				label: "With Jinja",
				isActive: this.data.withJinja,
				closeOnActivate: true,
				onActivate: () => {
					const v = !this.data.withJinja;
					this._setWithJinja(v);
					if (v) {
						this._showJinjaHelp();
					}
				},
			},
		];
		return settings;
	}
}
