// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.listview_settings["Qalcuity Subscription"] = {
	get_indicator(doc) {
		const indicators = {
			Draft: "orange",
			"Pending Payment": "yellow",
			Active: "green",
			Suspended: "red",
			Expired: "darkgray",
			Cancelled: "red",
		};
		return [
			__(doc.status),
			indicators[doc.status] || "gray",
			`status,=,${doc.status}`,
		];
	},

	formatters: {
		end_date(value, df, doc) {
			if (value && doc.status === "Active") {
				const end = frappe.datetime.str_to_obj(value);
				const now = new Date();
				const days = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
				if (days <= 7 && days > 0) {
					return `<span class="text-danger">${value} (${days}d)</span>`;
				}
			}
			return value;
		},
	},
};
