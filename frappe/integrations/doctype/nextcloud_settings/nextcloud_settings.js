// Copyright (c) 2022, Dokos SAS and contributors
// For license information, please see license.txt

function nextcloud_hook_xcall(s, opts = {}) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: 'frappe.integrations.doctype.nextcloud_settings.' + s,
			args: opts.params,
			freeze: opts.freeze,
			callback: (r) => {
				resolve(r.message)
			},
			error: (r) => {
				reject(r)
			}
		})
	})
}

async function nextcloud_form_xcall(frm, s) {
	if (frm.is_dirty()) {
		frm.validate_and_save()
		const has_error = frm.is_dirty()
		if (has_error) { return false }
	}
	const res = await nextcloud_hook_xcall(s, { freeze: true })
	await frm.reload_doc()
	return res
}

function can_sync(frm) {
	return frm.doc.enabled && frm.doc.enable_sync && frm.doc.username && frm.doc.password
}

function nextcloud_add_button(frm, label, url, className) {
	frm.add_custom_button(label, () => {
		nextcloud_form_xcall(frm, url)
	}).addClass(className || 'btn-secondary')
}

frappe.ui.form.on('Nextcloud Settings', {
	refresh: function(frm) {
		frm.clear_custom_buttons()

		if (frm.doc.last_filesync_dt) {
			frm.set_df_property('last_filesync_dt', 'read_only', 1)
		}

		// frm.events.add_backup_button(frm)

		if (can_sync(frm)) {
			frm.events.add_button_sync_now(frm)
		}

		frm.events.check_server(frm)
	},

	enabled: function(frm) {
		frm.refresh()
	},

	check_server: async function(frm) {
		const s = await nextcloud_hook_xcall('nextcloud_filesync.api.check_server', {freeze: false})
		if (s.status !== 'ok' || s.error) {
			console.error(s)
		}
	},

	// Buttons
	add_button_backup: function(frm) {
		nextcloud_add_button(frm, __('Backup Now'), 'nextcloud_backups.backup_now', 'btn-primary')
	},

	add_button_sync_now: function(frm) {
		nextcloud_add_button(frm, __('Sync Now'), 'nextcloud_filesync.cron.run_cron', 'btn-primary')
	},
})
