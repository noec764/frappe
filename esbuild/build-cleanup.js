/* eslint-disable no-console */
const path = require("path");
const fs = require("fs");
const glob = require("fast-glob");

module.exports = {
	name: 'build_cleanup',
	setup(build) {
		build.onEnd(result => {
			if (result.errors.length) return;
			clean_dist_files(Object.keys(result.metafile.outputs));
		});
	},
};

function clean_dist_files(new_files) {
	new_files.forEach(
		file => {
			if (file.endsWith(".map")) return;

			const prefix_pattern = file.split(".").slice(0, -2);
			const suffix_pattern = file.split(".").slice(-1)
			const pattern = prefix_pattern.concat(["*"]).concat(suffix_pattern).join(".")
			glob.sync(pattern).forEach(
				file_to_delete => {
					console.log(file_to_delete, file_to_delete.startsWith(file))
					if (file_to_delete.startsWith(file)) return;

					fs.unlink(path.resolve(file_to_delete), err => {
						if (!err) return;

						console.error(
							`Error deleting ${file.split(path.sep).pop()}`
						);
					});
				}

			);
		}
	);
}
