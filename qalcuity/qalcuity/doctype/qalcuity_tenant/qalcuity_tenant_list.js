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
		// Bulk suspend action
		if (
			frappe.user.has_role([
				"System Manager",
				"Qalcuity Superadmin",
			])
		) {
			listview.page.add_menu_item(__("Bulk Suspend"), function () {
				const selected = listview.get_checked_items();
				if (!selected.length) {
					frappe.msgprint(__("Please select tenants to suspend."));
					return;
				}
				frappe.confirm(
					__("Suspend {0} tenant(s)?", [selected.length]),
					function () {
						selected.forEach(function (item) {
							frappe.call({
								method: "frappe.client.set_value",
								args: {
									doctype: "Qalcuity Tenant",
									name: item.name,
									fieldname: "status",
									value: "Suspended",
								},
							});
						});
						listview.refresh();
					}
				);
			});
		}
	},
};
