// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.ui.form.on("Qalcuity Settings", {
	refresh(frm) {
		// Show company info
		if (frm.doc.company_name) {
			frm.dashboard.set_headline(
				__("Qalcuity ERP Settings for {0}", [frm.doc.company_name])
			);
		}

		// Toggle trial period fields
		toggle_trial_fields(frm);
	},

	enable_trial_period(frm) {
		toggle_trial_fields(frm);
	},
});

function toggle_trial_fields(frm) {
	frm.toggle_display("trial_period_days", frm.doc.enable_trial_period);
}
