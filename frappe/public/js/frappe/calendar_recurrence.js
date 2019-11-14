import { RRule } from '../lib/rrule/rrule-tz.min.js';

frappe.CalendarRecurrence = class {
	constructor(frm) {
		this.frm = frm;
		this.currentRule = {}
		this.parse_rrule()
		this.make()
	}

	parse_rrule() {
		if (this.frm.doc.rrule) {
			const rule = RRule.fromString(this.frm.doc.rrule)
			this.currentRule = rule.origOptions
		}
	}

	frequency_map() {
		return {
			'daily': RRule.DAILY,
			'weekly': RRule.WEEKLY,
			'monthly': RRule.MONTHLY,
			'yearly': RRule.YEARLY
		}
	}

	get_frequency(value) {
		const map = this.frequency_map()
		return map[value];
	}

	get_default_frequency(value) {
		const map = dict_reverse(this.frequency_map())
		return map[value];
	}

	weekday_map() {
		return {
			'monday': RRule.MO,
			'tuesday': RRule.TU,
			'wednesday': RRule.WE,
			'thursday': RRule.TH,
			'friday': RRule.FR,
			'saturday': RRule.SA,
			'sunday': RRule.SU
		}
	}

	get_by_weekday(values) {
		const map = this.weekday_map()

		const result = Object.keys(map)
		.filter(day => values[day] === 1)
		.map(day => map[day])
		return result
	}

	get_default_by_weekday(day) {
		const map = this.weekday_map()
		const selectedDays = this.currentRule.byweekday.map(v => v.weekday)
		return selectedDays.includes(map[day].weekday) ? 1 : 0
	}

	make() {
		const me = this;
		this.dialog = new frappe.ui.Dialog({
			title: __('Custom recurrence'),
			fields: [
				{
					fieldname: "freq",
					label: __("Frequency"),
					fieldtype: "Select",
					options: [
						{label: __('Daily'), value: 'daily'},
						{label: __('Weekly'), value: 'weekly'},
						{label: __('Monthly'), value: 'monthly'},
						{label: __('Yearly'), value: 'yearly'}
					]
				},
				{
					fieldname: "until",
					label: __("Repeat until"),
					fieldtype: "Date"
				},
				{
					fieldname: "interval",
					label: __("Frequency interval"),
					fieldtype: "Int",
					default: 1
				},
				{
					fieldname: "day_col",
					fieldtype: "Column Break"
				},
				{
					fieldname: "monday",
					label: __("Monday"),
					fieldtype: "Check",
					depends_on: "eval:doc.freq=='weekly'",
					default: me.get_default_by_weekday("monday")
				},
				{
					fieldname: "tuesday",
					label: __("Tuesday"),
					fieldtype: "Check",
					depends_on: "eval:doc.freq=='weekly'",
					default: me.get_default_by_weekday("tuesday")
				},
				{
					fieldname: "wednesday",
					label: __("Wednesday"),
					fieldtype: "Check",
					depends_on: "eval:doc.freq=='weekly'",
					default: me.get_default_by_weekday("wednesday")
				},
				{
					fieldname: "thursday",
					label: __("Thursday"),
					fieldtype: "Check",
					depends_on: "eval:doc.freq=='weekly'",
					default: me.get_default_by_weekday("thursday")
				},
				{
					fieldname: "friday",
					label: __("Friday"),
					fieldtype: "Check",
					depends_on: "eval:doc.freq=='weekly'",
					default: me.get_default_by_weekday("friday")
				},
				{
					fieldname: "saturday",
					label: __("Saturday"),
					fieldtype: "Check",
					depends_on: "eval:doc.freq=='weekly'",
					default: me.get_default_by_weekday("saturday")
				},
				{
					fieldname: "sunday",
					label: __("Sunday"),
					fieldtype: "Check",
					depends_on: "eval:doc.freq=='weekly'",
					default: me.get_default_by_weekday("sunday")
				}
			],
			primary_action_label: __('Save'),
			primary_action:(values) => {
				const rule_obj = {
					freq: me.get_frequency(values.freq),
					interval: values.interval,
					byweekday: me.get_by_weekday(values)
				}

				if (values.until) {
					rule_obj.push({until: moment(values.until).toDate()})
				}

				const rule = new RRule(rule_obj)
				this.frm.doc.rrule = rule.toString()
				this.frm.doc.repeat = rule.toText()
				this.dialog.hide()
				this.frm.refresh_fields("repeat")
			}
		})
		this.init_dialog()
		this.dialog.show()
	}

	init_dialog() {
		const me = this;
		const field_default_values = {
			'freq': me.get_default_frequency(me.currentRule.freq),
			'until': me.currentRule.until ? moment(me.currentRule.until).format('YYYY-MM-DD') : null,
			'interval': me.currentRule.interval,
			'monday': me.get_default_by_weekday("monday"),
			'tuesday': me.get_default_by_weekday("tuesday"),
			'wednesday': me.get_default_by_weekday("wednesday"),
			'thursday': me.get_default_by_weekday("thursday"),
			'friday': me.get_default_by_weekday("friday"),
			'saturday': me.get_default_by_weekday("saturday"),
			'sunday': me.get_default_by_weekday("sunday")
		}
		this.dialog.set_values(field_default_values);
	}
}

function dict_reverse(obj) {
	const new_obj = {}
	const rev_obj = Object.keys(obj).reverse();
	rev_obj.forEach(function(i, j) { 
		new_obj[obj[i]] = i;
	})
	return new_obj;
}