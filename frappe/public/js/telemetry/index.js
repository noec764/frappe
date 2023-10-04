class MockTelemetryManager {
	toString() {
		return "There is no telemetry in Dodock, but this compatibility layer might be needed for some custom apps from the Frappeverse.";
	}
	constructor() {
		this.enabled = false;
	}
	initialize() {}
	capture() {}
	disable() {}
	can_enable() {
		return false;
	}
	send_heartbeat() {}
	register_pageview_handler() {}
	should_record_session() {
		return false;
	}
}

frappe.telemetry = new MockTelemetryManager();
