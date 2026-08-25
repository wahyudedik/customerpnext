// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.listview_settings["Qalcuity Plan"] = {
	get_indicator(doc) {
		if (doc.is_active) {
			return [__("Active"), "green", "is_active,=,1"];
		}
		return [__("Inactive"), "darkgray", "is_active,=,0"];
	},

	formatters: {
		price(value, df, doc) {
			if (value) {
				return frappe.format(value, {
					fieldtype: "Currency",
					options: doc.currency || "IDR",
				});
			}
			return value;
		},
	},

	onload(listview) {
		// Set default: show active plans first
		listview.filter_area.add([[listview.doctype, "is_active", "=", "1"]]);

		// Set page length
		listview.page_length = 20;
	},
};
