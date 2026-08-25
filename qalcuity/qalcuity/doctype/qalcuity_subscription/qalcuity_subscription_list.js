// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.listview_settings["Qalcuity Subscription"] = {
	get_indicator(doc) {
		const indicators = {
			Draft: "darkgray",
			"Pending Payment": "yellow",
			Active: "green",
			Suspended: "orange",
			Expired: "red",
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
					return `<span class="text-danger" style="font-weight: 600;">${value} (${days}h)</span>`;
				}
				if (days <= 0) {
					return `<span class="text-danger" style="font-weight: 600;">${value} (${__("KEDALUWARSA")})</span>`;
				}
			}
			return value;
		},
		end_date_wrapper(value) {
			return value;
		},
	},

	onload(listview) {
		// Default filter: show active subscriptions first
		listview.filter_area.add([
			[listview.doctype, "status", "in", ["Active", "Pending Payment"]],
		]);

		// Set page length
		listview.page_length = 20;
	},
};
