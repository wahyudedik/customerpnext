// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.ui.form.on("Qalcuity Payment", {
	refresh(frm) {
		// Status indicator
		const status_colors = {
			Pending: "orange",
			Approved: "green",
			Rejected: "red",
		};

		if (frm.doc.status) {
			frm.page.set_indicator(
				__(frm.doc.status),
				status_colors[frm.doc.status] || "gray"
			);
		}

		// Action buttons for admin/superadmin
		if (
			!frm.is_new() &&
			frm.doc.status === "Pending" &&
			frappe.user.has_role([
				"System Manager",
				"Qalcuity Superadmin",
				"Qalcuity Admin",
			])
		) {
			frm.add_custom_button(
				__("Approve"),
				function () {
					frappe.confirm(
						__("Approve payment {0}?", [frm.doc.name]),
						function () {
							frm.call("approve").then(() => frm.reload_doc());
						}
					);
				},
				__("Actions")
			).addClass("btn-success");

			frm.add_custom_button(
				__("Reject"),
				function () {
					frappe.prompt(
						{
							fieldname: "reason",
							label: __("Rejection Reason"),
							fieldtype: "Small Text",
							reqd: 1,
						},
						function (values) {
							frm
								.call("reject", { reason: values.reason })
								.then(() => frm.reload_doc());
						},
						__("Reject Payment"),
						__("Submit")
					);
				},
				__("Actions")
			).addClass("btn-danger");
		}

		// Show proof of payment image
		if (frm.doc.proof_of_payment) {
			frm.fields_dict.proof_of_payment.$wrapper
				.find(".like-disabled-input")
				.after(
					`<div style="margin-top: 8px;">
                        <a href="${frm.doc.proof_of_payment}" target="_blank">
                            <img src="${frm.doc.proof_of_payment}"
                                 style="max-width: 300px; border: 1px solid #ddd; border-radius: 4px;"
                                 alt="Proof of Payment" />
                        </a>
                    </div>`
				);
		}

		// Show subscription details
		if (frm.doc.subscription) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Qalcuity Subscription",
					fieldname: ["customer", "plan", "status"],
					filters: { name: frm.doc.subscription },
				},
				callback(r) {
					if (r.message) {
						frm.dashboard.set_headline(
							__("Customer: {0} | Plan: {1} | Status: {2}", [
								r.message.customer,
								r.message.plan,
								r.message.status,
							])
						);
					}
				},
			});
		}
	},

	subscription(frm) {
		// Auto-fill bank details from settings
		if (frm.doc.subscription && !frm.doc.bank_account_name) {
			frappe.call({
				method: "frappe.client.get_single_value",
				args: {
					doctype: "Qalcuity Settings",
					fieldname: [
						"bank_name",
						"bank_account_name",
						"bank_account_number",
					],
				},
				callback(r) {
					if (r.message) {
						frm.set_value("bank_account_name", r.message.bank_account_name || "");
						frm.set_value("bank_account_number", r.message.bank_account_number || "");
					}
				},
			});
		}
	},
});
