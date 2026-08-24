/**
 * Qalcuity ERP - Main JavaScript
 * Global client-side utilities and configuration
 */

frappe.provide("qalcuity");

qalcuity.version = "0.0.1";

/**
 * Qalcuity namespace for global utilities
 */
qalcuity.utils = {
	/**
	 * Format currency with IDR default
	 */
	format_currency(amount, currency = "IDR") {
		return frappe.format(amount, {
			fieldtype: "Currency",
			options: currency,
		});
	},

	/**
	 * Get status badge HTML
	 */
	get_status_badge(status) {
		const colors = {
			Active: "green",
			Suspended: "orange",
			Terminated: "red",
			Pending: "orange",
			Approved: "green",
			Rejected: "red",
			Draft: "gray",
			Expired: "darkgray",
			Cancelled: "red",
			"Pending Payment": "yellow",
		};
		return `<span class="indicator-pill whitespace-nowrap ${colors[status] || "gray"
			}">${__(status)}</span>`;
	},

	/**
	 * Calculate days remaining until date
	 */
	days_remaining(date) {
		const target = frappe.datetime.str_to_obj(date);
		const now = new Date();
		return Math.ceil((target - now) / (1000 * 60 * 60 * 24));
	},

	/**
	 * Validate file size against settings
	 */
	validate_file_size(file_size_bytes) {
		return frappe.call({
			method: "frappe.client.get_single_value",
			args: {
				doctype: "Qalcuity Settings",
				fieldname: "max_file_size_mb",
			},
		}).then((r) => {
			const max_bytes = (r.message || 5) * 1024 * 1024;
			if (file_size_bytes > max_bytes) {
				frappe.msgprint({
					message: __(
						"File size exceeds maximum allowed size of {0} MB",
						[r.message]
					),
					indicator: "red",
				});
				return false;
			}
			return true;
		});
	},
};

/**
 * Qalcuity branding helpers
 */
qalcuity.branding = {
	get_logo_html(size = 24) {
		return `<span class="qalcuity-logo" style="font-size: ${size}px; font-weight: 700; color: var(--primary);">Qalcuity</span>`;
	},
};

// Log initialization
console.log("Qalcuity ERP v" + qalcuity.version + " loaded");
