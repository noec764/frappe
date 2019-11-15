import { RRule } from '../lib/rrule/rrule-tz.min.js';

// 'en' is implied, don't add it to this array
const availableLanguages = ['de']
frappe.CalendarRecurrence = class {
	constructor(frm) {
		this.frm = frm;
		this.currentRule = {}
		this.start_day = moment(this.frm.doc.start_on)

		if (availableLanguages.includes(frappe.boot.lang)) {
			frappe.require(`/assets/frappe/js/lib/rrule/locales/${frappe.boot.lang}.js`)
		} 
		this.parse_rrule()
		this.make()
	}

	parse_rrule() {
		if (this.frm.doc.rrule) {
			const rule = RRule.fromString(this.frm.doc.rrule)
			this.currentRule = rule.origOptions
		}
	}

	gettext(id) {
		if (availableLanguages.includes(frappe.boot.lang) && RRULE_STRINGS){
			return RRULE_STRINGS[id] || id;
		}
		return id
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
		if (this.currentRule.byweekday && this.currentRule.byweekday.length) {
			const selectedDays = this.currentRule.byweekday.map(v => v.weekday)
			return selectedDays.includes(map[day].weekday) ? 1 : 0
		}
		return 0;
	}

	get_by_day_label() {
		const date_day = this.start_day.date()
		return __("Monthly on day {}", [date_day])
	}

	get_by_pos_label() {
		const ordinals = ["", __("first"), __("second"), __("third"), __("fourth"), __("fifth")];
		const occurence = ordinals[this.get_by_pos_count()]
		return __("Monthly on the {0} {1}", [occurence, this.start_day.format("dddd")])
	}

	get_by_pos_count() {
		return Math.ceil(this.start_day.date()/7)
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
					fieldname: "monthly_options",
					label: __("Options"),
					fieldtype: "Select",
					depends_on: "eval:doc.freq=='monthly'",
					options: [
						{label: me.get_by_day_label(), value: 'by_day'},
						{label: me.get_by_pos_label(), value: 'by_pos'},
					],
					default: 'by_day'
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
					freq: me.get_frequency(values.freq)
				}

				if (values.interval) {
					Object.assign(rule_obj, {interval: values.interval})
				}

				const weekdays_values = me.get_by_weekday(values)
				if (weekdays_values && weekdays_values.length) {
					Object.assign(rule_obj, {byweekday: weekdays_values})
				}

				if (values.until) {
					Object.assign(rule_obj, {until: moment(values.until).toDate()})
				}

				if (values.freq == 'monthly' && values.monthly_options) {
					if (values.monthly_options == "by_day") {
						Object.assign(rule_obj, {bymonthday: [moment(me.frm.doc.starts_on).date()]})
					} else {
						const weekday_map = me.weekday_map()
						Object.assign(rule_obj, {
							byweekday: weekday_map[me.start_day.format("dddd").toLowerCase()],
							bymonthday: [me.get_by_pos_count()]
						})
					}
				}

				const rule = new RRule(rule_obj)
				this.frm.doc.rrule = rule.toString()
				this.frm.doc.repeat = rule.toText(id => {
					return me.gettext(id);
				}, (typeof RRULE_DATES === undefined) ? ENGLISH : RRULE_DATES)
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