import Vue from "vue";

if (!window.Vue) {
	Vue.prototype.__ = window.__;
	Vue.prototype.frappe = window.frappe;
	window.Vue = Vue;
	window.createApp = (...args) => {
		const app = Vue.createApp(...args);
		app.config.globalProperties.__ = window.__;
		app.config.globalProperties.frappe = window.frappe;
		return app;
	};
}
