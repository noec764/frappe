<template>
	<div 
		:id="id" 
		class="grid-item border" 
		:style="cardStyle"
	>
		<div class="item-content">
			<div class="row">
				<div class="col-xs-5">
					<div class="icon-big text-center">
						<i :class="icon"></i>
					</div>
				</div>
				<div class="col-xs-7">
					<p>{{label}}</p>
					{{text}}
				</div>
				<i class="octicon octicon-trashcan remove-icon" @click="remove_card"></i>
			</div>
		</div>
  </div>
</template>

<script>

export default {
	name: 'StatsCard',
	props: {
	  	id: {
			type: [Number, String],
			default: 'desk-graph'
		},
		width: {
			type: String,
			default: '15%'
		},
		height: {
			type: String,
			default: '150'
		},
		label: {
			type: String,
			default: null
		},
		color: {
			type: String,
			default: null
		},
		icon: {
			type: String,
			default: null
		},
		text: {
			type: String,
			default: null
		}
	},
	data() {
		return {
			cardHeight: this.height + "px"
		}
	},
	computed: {
		cardStyle() {
			return {'width': '100%', 'max-width': this.width, 'min-width': '150px', 'height': this.cardHeight};
		}
	},
	methods: {
		remove_card() {
			this.$emit("removeCard", this.id)
		}
	}
}
</script>

<style>

.remove-icon {
	float: right;
	color: #6c7680;
	cursor:pointer;
}

.icon-big {
	font-size: 3em;
	min-height: 64px;
}

</style>