import "./controls.bundle.js";
import "./frappe/model/create_new.js";
import "./dialog.bundle.js";
import "./lib/moment";
import "./frappe/utils/datetime.js";
import "./frappe/web_form/webform_script.js";
import "./bootstrap-4-web.bundle.js";

window.SetVueGlobals = (app) => {
	app.config.globalProperties.__ = window.__;
	app.config.globalProperties.frappe = window.frappe;
};

import Sortable from "sortablejs";

window.Sortable = Sortable;
