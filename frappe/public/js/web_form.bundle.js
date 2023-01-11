import "./controls.bundle.js";
import "./frappe/model/create_new.js";
import "./dialog.bundle.js";
import "./lib/moment";
import "./frappe/utils/datetime.js";
import "./frappe/web_form/webform_script.js";
import "./bootstrap-4-web.bundle.js";

import Vue from "vue/dist/vue.esm.js";
import Sortable from "sortablejs";

window.Vue = Vue;
Vue.prototype.__ = window.__;
Vue.prototype.frappe = window.frappe;

window.Sortable = Sortable;
