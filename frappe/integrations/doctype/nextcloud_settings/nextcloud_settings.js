// Copyright (c) 2022, Dokos SAS and contributors
// For license information, please see license.txt

function nextcloud_hook_xcall(s, opts = {}) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: 'frappe.integrations.doctype.nextcloud_settings.' + s,
			args: opts.params,
			freeze: opts.freeze,
			callback: (r) => {
				resolve(r.message);
			},
			error: (r) => {
				reject(r.message);
			}
		});
	});
}

async function nextcloud_form_xcall(frm, s) {
	if (frm.is_dirty()) {
		await frm.save()
	}
	await nextcloud_hook_xcall(s, { freeze: true })
	await frm.reload_doc()
}

frappe.ui.form.on('Nextcloud Settings', {
	refresh: function(frm) {
		frm.clear_custom_buttons();
		// frm.events.add_migrate_button(frm);
		// frm.events.add_backup_button(frm);
		frm.events.add_sync_all_button(frm);
		frm.events.add_sync_recent_button(frm);
		// frm.events.add_sync_to_remote_button(frm);

		if (frm.doc.last_filesync_dt) {
			frm.set_df_property('last_filesync_dt', 'read_only', 1);
		}

		// frappe.model.with_doc('File', 'Home').then(console.log)

		if (frm.doc.enabled && frm.doc.enable_sync) {
			nextcloud_hook_xcall('nextcloud_filesync.hooks.check_id_of_home').then((x) => {
				if (x.type === 'error' && x.reason === 'different-ids') {
					frm.events.showIdMismatchDialog(frm, x.localId, x.remoteId);
				}
			})
		}
	},

	showIdMismatchDialog: function(frm, localId, remoteId) {
		if (!localId && !remoteId) return;
		const title = __('The root folder appears to have changed.', 'Nextcloud')
		const description = __('', 'Nextcloud')
		const actions = {
			ignore: {
				label: __('Ignore and disable sync', 'Nextcloud'),
				onsubmit: () => {
					cur_frm.set_value('enable_sync', false);
				},
			},
			merge: {
				label: __('Force sync from Nextcloud', 'Nextcloud'),
				onsubmit: () => {
					// force sync from nextcloud
					nextcloud_form_xcall(frm, 'nextcloud_filesync.hooks.sync_from_remote_all')
				},
			},
			lorem: {
				label: __('Force upload to Nextcloud', 'Nextcloud'),
				onsubmit: () => {
					// force sync-upload to nextcloud
					nextcloud_form_xcall(frm, 'nextcloud_filesync.hooks.sync_to_remote_force')
				},
			},
		}

		const dialog = new frappe.ui.Dialog({
			title: title,
			fields: [{
				fieldname: '_html',
				fieldtype: 'HTML',
			}],

			primary_action: actions.merge.onsubmit,
			primary_action_label: actions.merge.label,

			secondary_action: actions.ignore.onsubmit,
			secondary_action_label: actions.ignore.label,
		});

		dialog.add_custom_action(actions.lorem.label, actions.lorem.onsubmit);
		dialog.fields_dict._html.wrapper.textContent = description
		dialog.fields_dict._html.wrapper.innerHTML += `
			<details open>
				<summary>${__('More information')}</summary>
				<div style="font-family: monospace;">
					<b>Remote root directory id:</b> ${remoteId}<br/>
					<b>Local stored expected id:</b> ${localId}
				</div>
			</details>
		`
		dialog.show();
	},

	enabled: function(frm) {
		frm.refresh();
	},

	add_migrate_button: function (frm) {
		if (frm.doc.enabled && frm.doc.username && frm.doc.password) {
			frm.add_custom_button(__('Migrate Now'), function() {
				nextcloud_hook_xcall('nextcloud_filesync.hooks.migrate_to_nextcloud', {freeze: true});
			}).addClass('btn-primary');
		}
	},

	add_backup_button: function(frm) {
		if (frm.doc.enabled && frm.doc.username && frm.doc.password) {
			frm.add_custom_button(__('Backup Now'), function() {
				nextcloud_form_xcall(frm, 'nextcloud_backups.backup_now')
			}).addClass('btn-primary');
		}
	},

	add_sync_all_button: function(frm) {
		if (frm.doc.enabled && frm.doc.username && frm.doc.password) {
			frm.add_custom_button(__('Sync Now'), function() {
				nextcloud_form_xcall(frm, 'nextcloud_filesync.hooks.sync_from_remote_all')
			}).addClass('btn-secondary');
		}
	},

	add_sync_recent_button: function(frm) {
		if (frm.doc.enabled && frm.doc.username && frm.doc.password) {
			frm.add_custom_button(__('Last Update'), function() {
				nextcloud_form_xcall(frm, 'nextcloud_filesync.hooks.sync_from_remote_since_last_update')
			}).addClass('btn-secondary');
		}
	},

	add_sync_to_remote_button: function(frm) {
		if (frm.doc.enabled && frm.doc.username && frm.doc.password) {
			frm.add_custom_button(__('Sync To Remote'), function() {
				nextcloud_form_xcall(frm, 'nextcloud_filesync.hooks.sync_to_remote')
			}).addClass('btn-secondary');
		}
	},
});
