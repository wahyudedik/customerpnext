// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.ui.form.on("Qalcuity Plan", {
	onload(frm) {
		// Set default currency to IDR for new plans
		if (frm.is_new() && !frm.doc.currency) {
			frm.set_value("currency", "IDR");
		}

		// Set default billing period
		if (frm.is_new() && !frm.doc.billing_period) {
			frm.set_value("billing_period", "Monthly");
		}

		// Set default is_active to true for new plans
		if (frm.is_new()) {
			frm.set_value("is_active", 1);
		}
	},

	refresh(frm) {
		// Show active subscription count
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
					if (r && r.message) {
						frm.dashboard.add_comment(
							__("Langganan Aktif: {0}", [r.message]),
							"green",
							true
						);
					}
				},
			});
		}

		// Status indicator
		if (frm.doc.is_active) {
			frm.page.set_indicator(__("Aktif"), "green");
		} else {
			frm.page.set_indicator(__("Nonaktif"), "darkgray");
		}

		// Deactivate button (Superadmin only)
		if (
			frm.doc.is_active &&
			!frm.is_new() &&
			frappe.user.has_role(["System Manager", "Qalcuity Superadmin"])
		) {
			frm.add_custom_button(
				__("Nonaktifkan"),
				function () {
					frappe.confirm(
						__(
							"Yakin ingin menonaktifkan paket '{0}'?",
							[frm.doc.plan_name]
						),
						function () {
							frm.call("deactivate").then(() => frm.reload_doc());
						}
					);
				},
				__("Actions")
			).addClass("btn-danger");
		}

		// Reactivate button for inactive plans
		if (
			!frm.doc.is_active &&
			!frm.is_new() &&
			frappe.user.has_role(["System Manager", "Qalcuity Superadmin"])
		) {
			frm.add_custom_button(
				__("Aktifkan Kembali"),
				function () {
					frm.set_value("is_active", 1);
					frm.save();
				},
				__("Actions")
			).addClass("btn-success");
		}
	},

	validate(frm) {
		// Validate price is not negative
		if (frm.doc.price < 0) {
			frappe.msgprint({
				message: __("Harga tidak boleh negatif."),
				indicator: "red",
			});
			frappe.validated = false;
		}

		// Validate max_users is positive
		if (frm.doc.max_users && frm.doc.max_users < 1) {
			frappe.msgprint({
				message: __("Maksimum pengguna harus minimal 1."),
				indicator: "red",
			});
			frappe.validated = false;
		}

		// Validate plan_name is not empty
		if (!frm.doc.plan_name || frm.doc.plan_name.trim() === "") {
			frappe.msgprint({
				message: __("Nama paket tidak boleh kosong."),
				indicator: "red",
			});
			frappe.validated = false;
		}
	},
});
