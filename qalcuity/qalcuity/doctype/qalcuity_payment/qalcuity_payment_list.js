// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.listview_settings["Qalcuity Payment"] = {
	get_indicator(doc) {
		const indicators = {
			Pending: "orange",
			Approved: "green",
			Rejected: "red",
		};
		return [
			__(doc.status),
			indicators[doc.status] || "gray",
			`status,=,${doc.status}`,
		];
	},

	formatters: {
		amount(value, df, doc) {
			if (value) {
				return frappe.format(value, {
					fieldtype: "Currency",
					options: doc.currency || "IDR",
				});
			}
			return value;
		},
		payment_date(value) {
			return frappe.datetime.str_to_user(value);
		},
	},

	onload(listview) {
		// Bulk approve/reject actions
		if (
			frappe.user.has_role([
				"System Manager",
				"Qalcuity Superadmin",
				"Qalcuity Admin",
			])
		) {
			// Bulk Approve — uses whitelisted API to trigger approve() and activate subscription
			listview.page.add_menu_item(__("Bulk Approve"), function () {
				const selected = listview.get_checked_items();
				if (!selected.length) {
					frappe.msgprint(__("Please select at least one payment to approve."));
					return;
				}
				frappe.confirm(
					__("Approve {0} payment(s)?", [selected.length]),
					function () {
						frappe.call({
							method: "qalcuity.qalcuity.api.payment.bulk_approve_payments",
							args: {
								payment_names: selected.map((s) => s.name),
							},
							callback: function (r) {
								if (r.message) {
									const results = r.message;
									const success = results.filter(
										(r) => r.status === "success"
									).length;
									const skipped = results.filter(
										(r) => r.status === "skipped"
									).length;
									const failed = results.filter(
										(r) => r.status === "error"
									).length;
									frappe.msgprint(
										__("Approved: {0}, Skipped: {1}, Failed: {2}", [
											success,
											skipped,
											failed,
										])
									);
									listview.refresh();
								}
							},
						});
					}
				);
			});

			// Bulk Reject — uses whitelisted API with rejection reason
			listview.page.add_menu_item(__("Bulk Reject"), function () {
				const selected = listview.get_checked_items();
				if (!selected.length) {
					frappe.msgprint(__("Please select at least one payment to reject."));
					return;
				}
				frappe.prompt(
					{
						label: __("Rejection Reason"),
						fieldname: "reason",
						fieldtype: "Small Text",
						reqd: 1,
					},
					function (values) {
						frappe.call({
							method: "qalcuity.qalcuity.api.payment.bulk_reject_payments",
							args: {
								payment_names: selected.map((s) => s.name),
								reason: values.reason,
							},
							callback: function (r) {
								if (r.message) {
									const results = r.message;
									const success = results.filter(
										(r) => r.status === "success"
									).length;
									const skipped = results.filter(
										(r) => r.status === "skipped"
									).length;
									const failed = results.filter(
										(r) => r.status === "error"
									).length;
									frappe.msgprint(
										__("Rejected: {0}, Skipped: {1}, Failed: {2}", [
											success,
											skipped,
											failed,
										])
									);
									listview.refresh();
								}
							},
						});
					},
					__("Bulk Reject Reason"),
					__("Reject")
				);
			});
		}
	},
};
