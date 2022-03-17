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
		frm.validate_and_save()
		const has_error = frm.is_dirty()
		if (has_error) { return false }
	}
	await nextcloud_hook_xcall(s, { freeze: true })
	await frm.reload_doc()
	return true
}

function can_sync(frm) {
	return frm.doc.enabled && frm.doc.enable_sync && frm.doc.username && frm.doc.password
}

function nextcloud_add_button(frm, label, url, className) {
	frm.add_custom_button(label, () => {
		nextcloud_form_xcall(frm, url)
	}).addClass(className || 'btn-secondary');
}

frappe.ui.form.on('Nextcloud Settings', {
	refresh: function(frm) {
		frm.clear_custom_buttons();

		if (frm.doc.last_filesync_dt) {
			frm.set_df_property('last_filesync_dt', 'read_only', 1);
		}

		// frm.events.add_backup_button(frm);
		if (can_sync(frm)) {
			// frm.events.add_button_sync_migrate(frm);
			frm.events.add_button_sync_all_forced(frm);
			frm.events.add_button_sync_all(frm);
			frm.events.add_button_sync_recent(frm);
			// frm.events.add_button_sync_to_remote(frm);
		}

		// run checks
		// frm.events.check_id_of_home(frm)
		frm.events.check_server(frm)
	},

	check_server: function(frm) {
		nextcloud_hook_xcall('nextcloud_filesync.api.check_server').then((x) => {
			console.log(x)
			if (x.status === 'ok') {
				console.log('ok')
			} else if (x.error) {
				frappe.throw(x.error)
			}
		})
	},

	check_id_of_home: function(frm) {
		nextcloud_hook_xcall('nextcloud_filesync.api.check_id_of_home').then((x) => {
			if (x.type === 'error' && x.reason === 'different-ids') {
				frm.events.show_id_mismatch_dialog(frm, x.localId, x.remoteId);
			} else if (x.type === 'warn' && x.message === 'never-synced') {
				frm.events.show_dialog_never_synced(frm)
			} else if (x.type === 'ok') {
				// ok
			} else {
				console.error(x)
			}
		})
	},

	// TODO: to remove, all should be automated
	show_dialog_never_synced: function(frm) {
		const title = __('Never synced [placeholder text]', [], 'Nextcloud')
		const description = __('If you just enabled the feature, click on "Sync now"')
		frappe.msgprint(title)
	},

	// TODO: to remove, all should be automated
	// but how? the user can't just delete the Home folder
	show_id_mismatch_dialog: function(frm, localId, remoteId) {
		if (!localId && !remoteId) return;
		const title = __('The root folder appears to have changed', [], 'Nextcloud')
		const description = __('Lorem ipsum dolor', [], 'Nextcloud')
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
					nextcloud_form_xcall(frm, 'nextcloud_filesync.api.sync_from_remote_all__force')
				},
			},
			lorem: {
				label: __('Force upload to Nextcloud', 'Nextcloud'),
				onsubmit: () => {
					// force sync-upload to nextcloud
					nextcloud_form_xcall(frm, 'nextcloud_filesync.api.sync_to_remote_force')
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
				<summary>${__('Details')}</summary>
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

	// Buttons
	add_button_backup: function(frm) {
		nextcloud_add_button(frm, __('Backup Now'), 'nextcloud_backups.backup_now', 'btn-primary')
	},

	add_button_sync_migrate: function (frm) {
		frm.add_custom_button(__('Migrate Now'), function() {
			nextcloud_hook_xcall('nextcloud_filesync.api.migrate_to_nextcloud', {freeze: true});
		}).addClass('btn-primary');
	},

	add_button_sync_all_forced: function(frm) {
		nextcloud_add_button(frm, __('FORCE SYNC'), 'nextcloud_filesync.api.sync_from_remote_all__force')
	},

	add_button_sync_all: function(frm) {
		nextcloud_add_button(frm, __('Sync Now'), 'nextcloud_filesync.api.sync_from_remote_all')
	},

	add_button_sync_recent: function(frm) {
		nextcloud_add_button(frm, __('Last Update'), 'nextcloud_filesync.api.sync_from_remote_since_last_update')
	},

	add_button_sync_to_remote: function(frm) {
		nextcloud_add_button(frm, __('Sync To Remote'), 'nextcloud_filesync.api.sync_to_remote')
	},
});
