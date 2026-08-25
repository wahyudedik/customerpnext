// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.ui.form.on("Qalcuity Payment", {
	onload(frm) {
		// Set default payment date to today for new documents
		if (frm.is_new() && !frm.doc.payment_date) {
			frm.set_value("payment_date", frappe.datetime.get_today());
		}

		// Set default currency to IDR
		if (frm.is_new() && !frm.doc.currency) {
			frm.set_value("currency", "IDR");
		}

		// Set default payment method
		if (frm.is_new() && !frm.doc.payment_method) {
			frm.set_value("payment_method", "Bank Transfer");
		}
	},

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

		// Show proof of payment image preview
		if (frm.doc.proof_of_payment && frm.fields_dict.proof_of_payment) {
			const wrapper = frm.fields_dict.proof_of_payment.$wrapper;
			// Remove existing preview to avoid duplicates
			wrapper.find(".qalcuity-proof-preview").remove();
			wrapper
				.find(".like-disabled-input, .control-input-wrapper")
				.after(
					`<div class="qalcuity-proof-preview">
						<a href="${frm.doc.proof_of_payment}" target="_blank" rel="noopener noreferrer">
							<img src="${frm.doc.proof_of_payment}"
								 alt="${__("Bukti Pembayaran")}" />
						</a>
					</div>`
				);
		}

		// Show subscription details in dashboard headline
		if (frm.doc.subscription) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Qalcuity Subscription",
					fieldname: ["customer", "plan", "status"],
					filters: { name: frm.doc.subscription },
				},
				callback(r) {
					if (r && r.message) {
						frm.dashboard.set_headline(
							__("Pelanggan: {0} | Paket: {1} | Status: {2}", [
								r.message.customer,
								r.message.plan,
								r.message.status,
							])
						);
					}
				},
				error(err) {
					console.warn("Qalcuity: Gagal memuat detail subscription", err);
				},
			});
		}

		// Set field descriptions for better UX
		if (frm.doc.status === "Rejected" && frm.doc.rejection_reason) {
			frm.fields_dict.rejection_reason.$wrapper.show();
		}
	},

	subscription(frm) {
		// Auto-fill bank details from settings when subscription is selected
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
					if (r && r.message) {
						frm.set_value("bank_account_name", r.message.bank_account_name || "");
						frm.set_value("bank_account_number", r.message.bank_account_number || "");
					}
				},
				error(err) {
					console.warn("Qalcuity: Gagal memuat data bank dari Settings", err);
				},
			});
		}
	},

	validate(frm) {
		// Validate amount is positive
		if (frm.doc.amount && frm.doc.amount <= 0) {
			frappe.msgprint({
				message: __("Jumlah pembayaran harus lebih dari 0."),
				indicator: "red",
			});
			frappe.validated = false;
		}

		// Validate payment date is not in the future
		if (frm.doc.payment_date) {
			const payment_date = frappe.datetime.str_to_obj(frm.doc.payment_date);
			const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
			if (payment_date > today) {
				frappe.msgprint({
					message: __("Tanggal pembayaran tidak boleh di masa depan."),
					indicator: "red",
				});
				frappe.validated = false;
			}
		}
	},
});
