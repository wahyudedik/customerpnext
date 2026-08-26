// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.ui.form.on("Qalcuity Login Log", {
	refresh(frm) {
		// Show colored status indicator
		if (frm.doc.status) {
			const colors = {
				"Success": "green",
				"Failed": "red",
				"Blocked": "orange",
			};
			frm.page.set_indicator_title(frm.doc.status);
			frm.page.set_indicator(colors[frm.doc.status] || "gray");
		}
	},
});
