// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.ui.form.on("Qalcuity Subscription", {
	refresh(frm) {
		// Status indicator
		const status_colors = {
			Draft: "orange",
			"Pending Payment": "yellow",
			Active: "green",
			Suspended: "red",
			Expired: "darkgray",
			Cancelled: "red",
		};

		if (frm.doc.status) {
			frm.page.set_indicator(
				__(frm.doc.status),
				status_colors[frm.doc.status] || "gray"
			);
		}

		// Action buttons based on status
		if (!frm.is_new() && !frm.is_dirty()) {
			if (
				frm.doc.status === "Pending Payment" &&
				frappe.user.has_role([
					"System Manager",
					"Qalcuity Superadmin",
					"Qalcuity Admin",
				])
			) {
				frm.add_custom_button(__("Activate"), function () {
					frm.call("activate").then(() => frm.reload_doc());
				}, __("Actions")).addClass("btn-success");
			}

			if (
				frm.doc.status === "Active" &&
				frappe.user.has_role([
					"System Manager",
					"Qalcuity Superadmin",
					"Qalcuity Admin",
				])
			) {
				frm.add_custom_button(__("Suspend"), function () {
					frappe.confirm(
						__("Are you sure you want to suspend this subscription?"),
						function () {
							frm.call("suspend").then(() => frm.reload_doc());
						}
					);
				}, __("Actions")).addClass("btn-warning");

				frm.add_custom_button(__("Cancel"), function () {
					frappe.confirm(
						__("Are you sure you want to cancel this subscription? This action cannot be undone."),
						function () {
							frm.call("cancel").then(() => frm.reload_doc());
						}
					);
				}, __("Actions")).addClass("btn-danger");
			}

			if (frm.doc.status === "Suspended" &&
				frappe.user.has_role([
					"System Manager",
					"Qalcuity Superadmin",
					"Qalcuity Admin",
				])
			) {
				frm.add_custom_button(__("Reactivate"), function () {
					frappe.confirm(
						__("Reactivate this subscription?"),
						function () {
							frm.call("reactivate").then(() => frm.reload_doc());
						}
					);
				}, __("Actions")).addClass("btn-success");
			}
		}

		// Show days remaining
		if (frm.doc.end_date && frm.doc.status === "Active") {
			const end = frappe.datetime.str_to_obj(frm.doc.end_date);
			const now = new Date();
			const days = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
			if (days > 0) {
				frm.dashboard.add_comment(
					__("Days remaining: {0}", [days]),
					days <= 7 ? "orange" : "green",
					true
				);
			} else {
				frm.dashboard.add_comment(
					__("Subscription has expired"),
					"red",
					true
				);
			}
		}
	},

	customer(frm) {
		// Auto-fill from customer
		if (frm.doc.customer && !frm.doc.plan) {
			frm.trigger("load Plans");
		}
	},

	plan(frm) {
		// Show plan details
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
					if (r.message) {
						frm.dashboard.set_headline(
							__("Plan: {0} | Price: {1} | Billing: {2}", [
								frm.doc.plan,
								frappe.format(r.message.price, {
									fieldtype: "Currency",
									options: r.message.currency,
								}),
								r.message.billing_period,
							])
						);
					}
				},
			});
		}
	},
});
