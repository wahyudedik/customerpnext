// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.listview_settings["Qalcuity Backup"] = {
	get_indicator(doc) {
		const indicators = {
			Pending: "gray",
			Running: "orange",
			Completed: "green",
			Failed: "red",
		};
		return [
			__(doc.status),
			indicators[doc.status] || "gray",
			`status,=,${doc.status}`,
		];
	},

	formatters: {
		file_size(value) {
			if (!value) return "";
			// Format bytes to human-readable
			if (value < 1024) return value + " B";
			if (value < 1048576) return (value / 1024).toFixed(1) + " KB";
			if (value < 1073741824)
				return (value / 1048576).toFixed(1) + " MB";
			return (value / 1073741824).toFixed(2) + " GB";
		},
		started_at(value) {
			return value ? frappe.datetime.str_to_user(value) : "";
		},
		duration_seconds(value) {
			if (!value) return "";
			const mins = Math.floor(value / 60);
			const secs = value % 60;
			if (mins > 0) return `${mins}m ${secs}s`;
			return `${secs}s`;
		},
	},

	onload(listview) {
		// Default sort: newest first
		if (!listview.sort_selector) {
			listview.sort_selector = ["creation", "desc"];
		}

		// Admin menu: Trigger Manual Backup
		if (
			frappe.user.has_role([
				"System Manager",
				"Qalcuity Superadmin",
				"Qalcuity Admin",
			])
		) {
			listview.page.add_menu_item(__("Trigger Backup"), function () {
				frappe.prompt(
					{
						label: __("Backup Type"),
						fieldname: "backup_type",
						fieldtype: "Select",
						options: "Full\nDatabase\nFiles",
						default: "Full",
						reqd: 1,
					},
					function (values) {
						frappe.call({
							method: "qalcuity.qalcuity.api.backup_api.trigger_backup",
							args: {
								backup_type: values.backup_type,
							},
							freeze: true,
							freeze_message: __("Memulai backup..."),
							callback: function (res) {
								if (res && res.message) {
									frappe.show_alert({
										message: __("Backup triggered: {0}", [
											res.message.backup_name || "Success",
										]),
										indicator: "green",
									});
									listview.refresh();
								}
							},
							error: function (err) {
								frappe.show_alert({
									message: __("Backup gagal: {0}", [
										err.message || __("Error tidak diketahui"),
									]),
									indicator: "red",
								});
							},
						});
					},
					__("Pilih tipe backup"),
					__("Mulai Backup")
				);
			});

			// Menu: View Backup Stats
			listview.page.add_menu_item(__("Backup Statistics"), function () {
				frappe.call({
					method: "qalcuity.qalcuity.api.backup_api.get_backup_stats",
					callback: function (res) {
						if (res && res.message) {
							const stats = res.message;
							frappe.msgprint({
								title: __("Backup Statistics"),
								indicator: "green",
								message: `
									<table class="table table-bordered" style="margin:0;">
										<tr><td><b>Total Backups</b></td><td>${stats.total_backups || 0}</td></tr>
										<tr><td><b>Total Size</b></td><td>${stats.total_size_formatted || "0 B"}</td></tr>
										<tr><td><b>Last Backup</b></td><td>${stats.last_backup_time || "Never"}</td></tr>
										<tr><td><b>Last Status</b></td><td>${stats.last_backup_status || "N/A"}</td></tr>
										<tr><td><b>Successful</b></td><td>${stats.completed_count || 0}</td></tr>
										<tr><td><b>Failed</b></td><td>${stats.failed_count || 0}</td></tr>
									</table>
								`,
							});
						}
					},
				});
			});
		}
	},
};
