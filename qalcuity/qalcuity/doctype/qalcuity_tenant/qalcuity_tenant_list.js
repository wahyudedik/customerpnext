// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.listview_settings["Qalcuity Tenant"] = {
	get_indicator(doc) {
		const indicators = {
			Active: "green",
			Suspended: "orange",
			Terminated: "red",
		};
		return [
			__(doc.status),
			indicators[doc.status] || "gray",
			`status,=,${doc.status}`,
		];
	},

	formatters: {
		storage_used_gb(value) {
			if (value) {
				return `${value} GB`;
			}
			return "0 GB";
		},
	},

	onload(listview) {
		// Default filter: show active tenants
		listview.filter_area.add([[listview.doctype, "status", "=", "Active"]]);

		// Set page length
		listview.page_length = 20;

		// Bulk suspend action (Superadmin only)
		if (
			frappe.user.has_role([
				"System Manager",
				"Qalcuity Superadmin",
			])
		) {
			listview.page.add_menu_item(__("Tangguhkan Massal"), function () {
				const selected = listview.get_checked_items();
				if (!selected.length) {
					frappe.msgprint({
						message: __("Pilih minimal satu tenant untuk ditangguhkan."),
						indicator: "orange",
					});
					return;
				}
				frappe.confirm(
					__("Tangguhkan {0} tenant?", [selected.length]),
					function () {
						let completed = 0;
						const total = selected.length;

						selected.forEach(function (item, index) {
							frappe.call({
								method: "frappe.client.set_value",
								args: {
									doctype: "Qalcuity Tenant",
									name: item.name,
									fieldname: "status",
									value: "Suspended",
								},
								callback: function () {
									completed++;
									if (completed === total) {
										frappe.msgprint({
											message: __("Berhasil menangguhkan {0} tenant.", [
												completed,
											]),
											indicator: "green",
										});
										listview.refresh();
									}
								},
								error: function () {
									completed++;
									if (completed === total) {
										frappe.msgprint({
											message: __("Proses selesai dengan beberapa error."),
											indicator: "orange",
										});
										listview.refresh();
									}
								},
							});
						});
					}
				);
			});
		}
	},
};
