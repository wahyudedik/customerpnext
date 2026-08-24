// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.ui.form.on("Qalcuity Plan", {
	refresh(frm) {
		// Show subscription count
		if (!frm.doc.__islocal) {
			frappe.call({
				method: "frappe.client.get_count",
				args: {
					doctype: "Qalcuity Subscription",
					filters: {
						plan: frm.doc.name,
						status: ["in", ["Active", "Pending Payment"]],
					},
				},
				callback(r) {
					if (r.message) {
						frm.dashboard.add_comment(
							__("Active Subscriptions: {0}", [r.message]),
							"green",
							true
						);
					}
				},
			});
		}

		// Deactivate button
		if (
			frm.doc.is_active &&
			!frm.is_new() &&
			frappe.user.has_role(["System Manager", "Qalcuity Superadmin"])
		) {
			frm.add_custom_button(__("Deactivate"), function () {
				frappe.confirm(
					__(
						"Are you sure you want to deactivate plan '{0}'?",
						[frm.doc.plan_name]
					),
					function () {
						frm.call("deactivate").then(() => frm.reload_doc());
					}
				);
			}).addClass("btn-danger");
		}
	},

	validate(frm) {
		if (frm.doc.price < 0) {
			frappe.msgprint(__("Price cannot be negative."));
			frappe.validated = false;
		}
	},
});
