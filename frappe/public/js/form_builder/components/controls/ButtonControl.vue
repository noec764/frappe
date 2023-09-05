<!-- Used as Button & Heading Control -->
<script setup>
import { computed } from 'vue';
import { useStore } from '../../store';
import { show_configuration_dialog } from '../../../frappe/doctype/configuration';

const props = defineProps(["df", "value"]);

const isConfigurationButton = computed(() => {
	return props.df.fieldname == "configuration_button" && props.df.parent === "DocField" && props.df.parentfield === "fields"
});
const openConfigurationModal = () => {
	const store = useStore()
	const field = store.form.selected_field;
	show_configuration_dialog(field, (new_config) => {
		field.configuration = new_config;
	})
	// const store = useStore()
	// const { doctype, name } = store.form.selected_field;
	// cur_frm.trigger("configuration_button", doctype, name);
}
</script>

<template>
	<button v-if="isConfigurationButton" class="btn btn-xs btn-primary-light" @click="openConfigurationModal">
		{{ df.label }}
	</button>
	<div
	v-else
		class="control frappe-control editable"
		:data-fieldtype="df.fieldtype"
	>
		<!-- label -->
		<div class="field-controls">
			<h4 v-if="df.fieldtype == 'Heading'">
				<slot name="label" />
			</h4>
			<button v-else class="btn btn-xs btn-default">
				<slot name="label" />
			</button>
			<slot name="actions" />
		</div>

		<!-- description -->
		<div v-if="df.description" class="mt-2 description" v-html="df.description" />
	</div>
</template>

<style lang="scss" scoped>
h4 {
	margin-bottom: 0px;
}

</style>
