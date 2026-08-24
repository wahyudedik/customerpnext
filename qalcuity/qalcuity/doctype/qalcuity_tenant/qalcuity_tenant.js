// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.ui.form.on("Qalcuity Tenant", {
	refresh(frm) {
		// Status indicator
		const status_colors = {
			Active: "green",
			Suspended: "orange",
			Terminated: "red",
		};

		if (frm.doc.status) {
			frm.page.set_indicator(
				__(frm.doc.status),
				status_colors[frm.doc.status] || "gray"
			);
		}

		// Action buttons
		if (!frm.is_new() && !frm.is_dirty()) {
			const can_manage = frappe.user.has_role([
				"System Manager",
				"Qalcuity Superadmin",
				"Qalcuity Admin",
			]);

			if (can_manage) {
				if (frm.doc.status === "Active") {
					frm.add_custom_button(
						__("Suspend"),
						function () {
							frappe.confirm(
								__("Suspend tenant '{0}'?", [frm.doc.tenant_id]),
								function () {
									frm
										.call("suspend")
										.then(() => frm.reload_doc());
								}
							);
						},
						__("Actions")
					).addClass("btn-warning");

					frm.add_custom_button(
						__("Terminate"),
						function () {
							frm
								.call("terminate")
								.then(() => frm.reload_doc());
						},
						__("Actions")
					).addClass("btn-danger");
				}

				if (frm.doc.status === "Suspended") {
					frm.add_custom_button(
						__("Reactivate"),
						function () {
							frm
								.call("reactivate")
								.then(() => frm.reload_doc());
						},
						__("Actions")
					).addClass("btn-success");
				}
			}
		}

		// Show subscription details
		if (frm.doc.subscription) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Qalcuity Subscription",
					fieldname: ["plan", "status", "end_date"],
					filters: { name: frm.doc.subscription },
				},
				callback(r) {
					if (r.message) {
						frm.dashboard.set_headline(
							__("Plan: {0} | Status: {1} | Expires: {2}", [
								r.message.plan,
								r.message.status,
								r.message.end_date || "N/A",
							])
						);
					}
				},
			});
		}

		// Show last activity
		if (frm.doc.last_activity) {
			frm.dashboard.add_comment(
				__("Last Activity: {0}", [frappe.datetime.str_to_user(frm.doc.last_activity)]),
				"gray",
				true
			);
		}
	},

	customer(frm) {
		// Auto-generate tenant_id from customer
		if (frm.doc.customer && !frm.doc.tenant_id) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Customer",
					fieldname: "customer_name",
					filters: { name: frm.doc.customer },
				},
				callback(r) {
					if (r.message) {
						const name = r.message.customer_name
							.toLowerCase()
							.replace(/[^a-z0-9]/g, "-")
							.replace(/-+/g, "-");
						frm.set_value("tenant_id", name);
					}
				},
			});
		}
	},
});
