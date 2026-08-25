// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.ui.form.on("Qalcuity Subscription", {
	onload(frm) {
		// Set default status for new documents
		if (frm.is_new() && !frm.doc.status) {
			frm.set_value("status", "Draft");
		}

		// Set default currency
		if (frm.is_new() && !frm.doc.currency) {
			frm.set_value("currency", "IDR");
		}
	},

	refresh(frm) {
		// Status indicator
		const status_colors = {
			Draft: "darkgray",
			"Pending Payment": "yellow",
			Active: "green",
			Suspended: "orange",
			Expired: "red",
			Cancelled: "red",
		};

		if (frm.doc.status) {
			frm.page.set_indicator(
				__(frm.doc.status),
				status_colors[frm.doc.status] || "gray"
			);
		}

		// Action buttons based on status (admin/superadmin only)
		if (!frm.is_new() && !frm.is_dirty()) {
			const can_manage = frappe.user.has_role([
				"System Manager",
				"Qalcuity Superadmin",
				"Qalcuity Admin",
			]);

			if (can_manage) {
				// Activate from Pending Payment
				if (frm.doc.status === "Pending Payment") {
					frm.add_custom_button(
						__("Aktifkan"),
						function () {
							frappe.confirm(
								__("Aktifkan langganan ini?"),
								function () {
									frm.call("activate").then(() => frm.reload_doc());
								}
							);
						},
						__("Actions")
					).addClass("btn-success");
				}

				// Suspend & Cancel from Active
				if (frm.doc.status === "Active") {
					frm.add_custom_button(
						__("Tangguhkan"),
						function () {
							frappe.confirm(
								__("Yakin ingin menangguhkan langganan ini?"),
								function () {
									frm.call("suspend").then(() => frm.reload_doc());
								}
							);
						},
						__("Actions")
					).addClass("btn-warning");

					frm.add_custom_button(
						__("Batalkan"),
						function () {
							frappe.confirm(
								__("Yakin ingin membatalkan langganan ini? Tindakan ini tidak dapat dibatalkan."),
								function () {
									frm.call("cancel").then(() => frm.reload_doc());
								}
							);
						},
						__("Actions")
					).addClass("btn-danger");
				}

				// Reactivate from Suspended
				if (frm.doc.status === "Suspended") {
					frm.add_custom_button(
						__("Aktifkan Kembali"),
						function () {
							frappe.confirm(
								__("Aktifkan kembali langganan ini?"),
								function () {
									frm.call("reactivate").then(() => frm.reload_doc());
								}
							);
						},
						__("Actions")
					).addClass("btn-success");
				}
			}
		}

		// Show days remaining for active subscriptions
		if (frm.doc.end_date && frm.doc.status === "Active") {
			const end = frappe.datetime.str_to_obj(frm.doc.end_date);
			const now = new Date();
			const days = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
			if (days > 0) {
				frm.dashboard.add_comment(
					__("Sisa hari: {0}", [days]),
					days <= 7 ? "orange" : "green",
					true
				);
			} else {
				frm.dashboard.add_comment(
					__("Langganan telah kedaluwarsa"),
					"red",
					true
				);
			}
		}

		// Show tenant link if available
		if (frm.doc.tenant) {
			frm.dashboard.add_comment(
				__("Tenant: {0}", [frm.doc.tenant]),
				"blue",
				true
			);
		}
	},

	customer(frm) {
		// When customer is selected, show info about existing subscriptions
		if (frm.doc.customer) {
			frappe.call({
				method: "frappe.client.get_count",
				args: {
					doctype: "Qalcuity Subscription",
					filters: {
						customer: frm.doc.customer,
						status: ["in", ["Active", "Pending Payment"]],
					},
				},
				callback(r) {
					if (r && r.message && r.message > 0) {
						frappe.msgprint({
							message: __("Pelanggan ini memiliki {0} langganan aktif.", [
								r.message,
							]),
							indicator: "orange",
						});
					}
				},
			});
		}
	},

	plan(frm) {
		// Show plan details in dashboard when plan is selected
		if (frm.doc.plan) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Qalcuity Plan",
					fieldname: [
						"price",
						"currency",
						"billing_period",
						"max_users",
					],
					filters: { name: frm.doc.plan },
				},
				callback(r) {
					if (r && r.message) {
						frm.dashboard.set_headline(
							__("Paket: {0} | Harga: {1} | Penagihan: {2} | Maks Pengguna: {3}", [
								frm.doc.plan,
								frappe.format(r.message.price, {
									fieldtype: "Currency",
									options: r.message.currency,
								}),
								r.message.billing_period,
								r.message.max_users || "-",
							])
						);
					}
				},
			});
		}
	},
});
