import "./jquery-bootstrap";
import Vue from "vue/dist/vue.esm.js";
import "./lib/moment";
import io from "socket.io-client/dist/socket.io.slim.js";
import Sortable from "./lib/Sortable.min";
import "./lib/leaflet/leaflet.js"
import "./lib/leaflet/leaflet.draw.js"
import "./lib/leaflet/L.Control.Locate.js"
import "./lib/leaflet/easy-button.js"
// TODO: esbuild
// Don't think jquery.hotkeys is being used anywhere. Will remove this after being sure.
// import "./lib/jquery/jquery.hotkeys.js";

window.Vue = Vue;
window.Sortable = Sortable;
window.io = io;
