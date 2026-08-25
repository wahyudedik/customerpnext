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
		// Set default filters: show pending first
		listview.filter_area.add([[listview.doctype, "status", "=", "Pending"]]);

		// Bulk approve/reject actions — admin/superadmin only
		if (
			frappe.user.has_role([
				"System Manager",
				"Qalcuity Superadmin",
				"Qalcuity Admin",
			])
		) {
			// Bulk Approve
			listview.page.add_menu_item(__("Bulk Approve"), function () {
				const selected = listview.get_checked_items();
				if (!selected.length) {
					frappe.msgprint({
						message: __("Pilih minimal satu pembayaran untuk disetujui."),
						indicator: "orange",
					});
					return;
				}
				frappe.confirm(
					__("Setujui {0} pembayaran?", [selected.length]),
					function () {
						frappe.call({
							method: "qalcuity.qalcuity.api.payment.bulk_approve_payments",
							args: {
								payment_names: selected.map((item) => item.name),
							},
							freeze: true,
							freeze_message: __("Memproses persetujuan..."),
							callback: function (res) {
								if (res && res.message) {
									const results = res.message;
									const success = results.filter(
										(item) => item.status === "success"
									).length;
									const skipped = results.filter(
										(item) => item.status === "skipped"
									).length;
									const failed = results.filter(
										(item) => item.status === "error"
									).length;
									frappe.msgprint({
										message: __("Disetujui: {0} | Dilewati: {1} | Gagal: {2}", [
											success,
											skipped,
											failed,
										]),
										indicator: failed > 0 ? "orange" : "green",
									});
									listview.refresh();
								}
							},
							error: function (err) {
								frappe.msgprint({
									message: __("Gagal memproses persetujuan massal: {0}", [
										err.message || __("Error tidak diketahui"),
									]),
									indicator: "red",
								});
							},
						});
					}
				);
			});

			// Bulk Reject
			listview.page.add_menu_item(__("Bulk Reject"), function () {
				const selected = listview.get_checked_items();
				if (!selected.length) {
					frappe.msgprint({
						message: __("Pilih minimal satu pembayaran untuk ditolak."),
						indicator: "orange",
					});
					return;
				}
				frappe.prompt(
					{
						label: __("Alasan Penolakan"),
						fieldname: "reason",
						fieldtype: "Small Text",
						reqd: 1,
					},
					function (values) {
						frappe.call({
							method: "qalcuity.qalcuity.api.payment.bulk_reject_payments",
							args: {
								payment_names: selected.map((item) => item.name),
								reason: values.reason,
							},
							freeze: true,
							freeze_message: __("Memproses penolakan..."),
							callback: function (res) {
								if (res && res.message) {
									const results = res.message;
									const success = results.filter(
										(item) => item.status === "success"
									).length;
									const skipped = results.filter(
										(item) => item.status === "skipped"
									).length;
									const failed = results.filter(
										(item) => item.status === "error"
									).length;
									frappe.msgprint({
										message: __("Ditolak: {0} | Dilewati: {1} | Gagal: {2}", [
											success,
											skipped,
											failed,
										]),
										indicator: failed > 0 ? "orange" : "green",
									});
									listview.refresh();
								}
							},
							error: function (err) {
								frappe.msgprint({
									message: __("Gagal memproses penolakan massal: {0}", [
										err.message || __("Error tidak diketahui"),
									]),
									indicator: "red",
								});
							},
						});
					},
					__("Alasan Penolakan Massal"),
					__("Tolak")
				);
			});
		}
	},
};
