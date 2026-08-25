// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

const PAYMENT_MODE_DESCRIPTIONS = {
	"Manual Transfer":
		"<b>Manual Transfer:</b> Customer upload bukti transfer bank. Superadmin review & approve manual.",
	Xendit: "<b>Xendit:</b> Payment gateway online. Customer bayar langsung via Xendit (QRIS, VA, kartu kredit, dll).",
	Hybrid: "<b>Hybrid:</b> Keduanya tersedia. Customer bisa pilih Manual Transfer atau Xendit saat checkout.",
};

frappe.ui.form.on("Qalcuity Settings", {
	refresh(frm) {
		// Show company info in dashboard
		if (frm.doc.company_name) {
			frm.dashboard.set_headline(
				__("Konfigurasi Qalcuity ERP untuk {0}", [frm.doc.company_name])
			);
		}

		// Toggle trial period fields based on enable_trial_period
		toggle_trial_fields(frm);

		// Set payment mode description
		update_payment_mode_description(frm);

		// Show current trial status info
		if (frm.doc.enable_trial_period && frm.doc.trial_period_days) {
			frm.dashboard.add_comment(
				__("Masa trial: {0} hari", [frm.doc.trial_period_days]),
				"blue",
				true
			);
		}

		// Show bank info summary
		if (frm.doc.bank_name && frm.doc.bank_account_name) {
			frm.dashboard.add_comment(
				__("Bank: {0} - {1}", [frm.doc.bank_name, frm.doc.bank_account_name]),
				"gray",
				true
			);
		}

		// Show bank accounts count
		if (frm.doc.bank_accounts && frm.doc.bank_accounts.length > 0) {
			frm.dashboard.add_comment(
				__("Bank Accounts tersedia: {0}", [frm.doc.bank_accounts.length]),
				"green",
				true
			);
		}
	},

	enable_trial_period(frm) {
		toggle_trial_fields(frm);
	},

	payment_mode(frm) {
		update_payment_mode_description(frm);
	},

	validate(frm) {
		// Validate trial period days
		if (frm.doc.enable_trial_period) {
			if (!frm.doc.trial_period_days || frm.doc.trial_period_days < 1) {
				frappe.msgprint({
					message: __("Jika masa trial diaktifkan, minimal harus 1 hari."),
					indicator: "red",
				});
				frappe.validated = false;
			}
			if (frm.doc.trial_period_days && frm.doc.trial_period_days > 365) {
				frappe.msgprint({
					message: __("Masa trial tidak boleh lebih dari 365 hari."),
					indicator: "red",
				});
				frappe.validated = false;
			}
		}

		// Validate max file size
		if (frm.doc.max_file_size_mb && frm.doc.max_file_size_mb < 1) {
			frappe.msgprint({
				message: __("Ukuran file maksimum minimal 1 MB."),
				indicator: "red",
			});
			frappe.validated = false;
		}

		// Validate Xendit config when mode requires it
		const mode = frm.doc.payment_mode || "Manual Transfer";
		if (mode === "Xendit" || mode === "Hybrid") {
			if (!frm.doc.xendit_api_key) {
				frappe.msgprint({
					message: __("Xendit API Key wajib diisi jika Payment Mode adalah {0}.", [mode]),
					indicator: "red",
				});
				frappe.validated = false;
			}
		}

		// Validate bank accounts when mode requires it
		if (mode === "Manual Transfer" || mode === "Hybrid") {
			if (!frm.doc.bank_accounts || frm.doc.bank_accounts.length === 0) {
				frappe.msgprint({
					message: __("Minimal 1 Bank Account wajib diisi jika Payment Mode adalah {0}.", [mode]),
					indicator: "red",
				});
				frappe.validated = false;
			}
		}
	},
});

function toggle_trial_fields(frm) {
	frm.toggle_display("trial_period_days", frm.doc.enable_trial_period);
	frm.toggle_reqd("trial_period_days", frm.doc.enable_trial_period);
}

function update_payment_mode_description(frm) {
	const mode = frm.doc.payment_mode;
	const description = PAYMENT_MODE_DESCRIPTIONS[mode] || "";
	frm.set_df_property("payment_mode_description", "options", description);
}
