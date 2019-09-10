<template>
	<div>
		<FullCalendar
			class='desk-calendar'
			ref="fullCalendar"
			:defaultView="defaultView"
			:header="{
				left: '',
				center: 'title',
				right: 'prev,next today',
			}"
			:plugins="calendarPlugins"
			:weekends="calendarWeekends"
			:events="getCalendarEvents"
			:locale="locale"
			:buttonText="buttonText"
			:noEventsMessage="noEventsMessage"
		/>
  </div>
</template>

<script>
import FullCalendar from '@fullcalendar/vue';
import listPlugin from '@fullcalendar/list';

export default {
	components: {
		FullCalendar
	},
	props: {
		item: {
			type: Object,
			default: {}
		}
	},
	data() {
		return {
			locale: frappe.boot.lang || 'en',
			calendarPlugins: [
				listPlugin
			],
			defaultView: 'listDay',
			calendarWeekends: true,
			calendarEvents: [],
			buttonText: {
				today: __("Today"),
				listWeek: __("Week"),
				listDay: __("Day")

			},
			noEventsMessage: __("No events to display"),
			events_method: null,
			fields_map: {}
		}
	},
	computed: {
	},
	created() {
		frappe.model.with_doctype(this.item.source_document, () => {
			const meta = frappe.get_meta(this.item.source_document);
			const calendar_options = eval(meta.__calendar_js)
			this.events_method = calendar_options.get_events_method || 'frappe.desk.doctype.event.event.get_events';
			this.fields_map = calendar_options.field_map
			this.$refs.fullCalendar.getApi().refetchEvents();
		})
	},
	methods: {
		getCalendarEvents(parameters, callback) {
			this.events_method&&frappe.xcall(this.events_method, {
				start: moment(parameters.start).format("YYYY-MM-DD"),
				end: moment(parameters.end).format("YYYY-MM-DD"),
				user: this.user
			})
			.then(result => {
				let events = []
				result.forEach(value => {
					let ev = {}
					Object.keys(this.fields_map).forEach(key => {
						ev[key] = value[this.fields_map[key]]
					})
					ev.url = `/desk#Form/${this.item.source_document}/${value.name}`;
					events.push(ev)
				})
				callback(events);
			})
		}
  }
}
</script>

<style lang='scss'>
@import 'node_modules/@fullcalendar/core/main';
@import 'node_modules/@fullcalendar/list/main';
@import 'frappe/public/scss/calendar';
.desk-calendar-top {
	margin: 0 0 3em;
}

.desk-calendar {
	margin: 0 auto;
	max-width: 900px;
}
</style>