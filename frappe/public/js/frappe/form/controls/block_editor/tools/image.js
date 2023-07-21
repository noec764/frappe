import Image from "@editorjs/image";

class DodockImageUploader {
	/**
	 * @param {object} params - uploader module params
	 * @param {ImageConfig} params.config - image tool config
	 * @param {Function} params.onUpload - one callback for all uploading (file, url, d-n-d, pasting)
	 * @param {Function} params.onError - callback for uploading errors
	 */
	constructor({ config, onUpload, onError, onCancel }) {
		this.config = config;
		this.onUpload = onUpload;
		this.onError = onError;
		this.onCancel = onCancel;
	}

	/**
	 * Handle clicks on the upload file button
	 * Fires ajax.transport()
	 *
	 * @param {Function} onPreview - callback fired when preview is ready
	 */
	uploadSelectedFile({ onPreview }) {
		onPreview();

		const file_uploader = new frappe.ui.FileUploader({
			// doctype: this.frm.doctype,
			// docname: this.frm.docname,
			// frm: this.frm,
			folder: frappe.boot.attachments_folder,
			on_success: (file_doc) => {
				this.onUpload({
					success: 1,
					file: {
						url: file_doc.file_url,
					},
				});
			},
			restrictions: {},
			make_attachments_public: 1,
		});

		file_uploader.dialog.on_hide = (close_dialog) => {
			this.onCancel();
		};
	}

	uploadByFile(file) {
		return;
		// this.uploadSelectedFile({
		// 	onPreview: (src) => {
		// 		this.onUpload({
		// 			success: 1,
		// 			file: {
		// 				url: src,
		// 			},
		// 		});
		// 	},
		// });
	}
}

export default class DodockImage extends Image {
	constructor(arg) {
		super(arg);
		/**
		 * Module for file uploading
		 */
		this.uploader = new DodockImageUploader({
			config: this.config,
			onUpload: (response) => this.onUpload(response),
			onError: (error) => this.uploadingFailed(error),
			onCancel: () => this.ui.hidePreloader(),
		});
	}
}
