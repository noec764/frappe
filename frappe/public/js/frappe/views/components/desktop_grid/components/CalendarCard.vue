<template>
	<div
		:id="id"
		class="grid-item desk-calendar-top border"
		:style="cardStyle"
	>
	<div class="item-content">
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
			:height="calendarHeight"
			:locale="locale"
			:buttonText="buttonText"
			:noEventsMessage="noEventsMessage"
			/>
			<i class="octicon octicon-trashcan remove-icon" @click="remove_card"></i>
		</div>
  </div>
</template>

<script>
import FullCalendar from '@fullcalendar/vue';
import listPlugin from '@fullcalendar/list';
import interactionPlugin from '@fullcalendar/interaction';

export default {
	components: {
		FullCalendar
	},
	props: {
		id: {
			type: [Number, String],
			default: 'desk-graph'
		},
		width: {
			type: String,
			default: '33%'
		},
		height: {
			type: String,
			default: '400'
		},
		reference: {
			type: String,
			default: 'Event'
		},
		user: {
			type: String,
			default: null
		}
	},
	data() {
		return {
			locale: frappe.boot.lang || 'en',
			calendarPlugins: [
				listPlugin,
				interactionPlugin
			],
			defaultView: 'listWeek',
			calendarWeekends: true,
			calendarEvents: [],
			calendarHeight: parseInt(this.height),
			cardHeight: parseInt(this.height) + 25 + "px",
			buttonText: {
				today: __("Today")
			},
			noEventsMessage: __("No events to display"),
			events_method: null
		}
	},
	computed: {
		cardStyle() {
			return {'width': '100%', 'max-width': this.width, 'min-width': '400px', 'height': this.cardHeight};
		}
	},
	created() {
		frappe.model.with_doctype(this.reference, () => {
			const meta = frappe.get_meta(this.reference);
			this.events_method = eval(meta.__calendar_js).get_events_method || 'frappe.desk.doctype.event.event.get_events';
		})
	},
	methods: {
		getCalendarEvents(parameters, callback) {
			this.events_method&&frappe.xcall(this.events_method, {
				start: parameters.start,
				end: parameters.end,
				user: this.user
			})
			.then(result => {
				result.forEach(value => {
					value.url = `/desk#Form/${this.reference}/${value.name}`;
				})
				callback(result);
			})
		},
		remove_card() {
			this.$emit("removeCard", this.id)
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
.remove-icon {
	float: right;
	padding: 5px;
	color: #6c7680;
	cursor:pointer;
}

</style>