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
	 * Uses Frappe's indicator-pill class with inline style fallback
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

		const color = colors[status] || "gray";

		// Frappe indicator-pill with inline fallback for compatibility
		return `<span class="indicator-pill whitespace-nowrap" style="white-space: nowrap;" data-indicator-color="${color}">${__(status)}</span>`;
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

	/**
	 * Format date to Indonesian locale string
	 */
	format_date_id(date_str) {
		if (!date_str) return "-";
		return frappe.datetime.str_to_user(date_str);
	},

	/**
	 * Get status color mapping for indicators
	 */
	get_status_color(status) {
		const map = {
			Active: "green",
			Suspended: "orange",
			Terminated: "red",
			Pending: "orange",
			Approved: "green",
			Rejected: "red",
			Draft: "darkgray",
			Expired: "darkgray",
			Cancelled: "red",
			"Pending Payment": "yellow",
		};
		return map[status] || "gray";
	},

	/**
	 * Show loading indicator in dashboard
	 */
	show_loading(frm, message) {
		frm.dashboard.set_headline(message || __("Memuat data..."));
	},

	/**
	 * Clear dashboard headline
	 */
	clear_loading(frm) {
		frm.dashboard.set_headline("");
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

/**
 * Qalcuity Bell Icon Notification Component
 * Menampilkan bell icon di navbar dengan dropdown notifikasi
 */
qalcuity.notifications = {
	/**
	 * SVG Bell Icon (minimalis, professional)
	 */
	bell_svg: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
		<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
		<path d="M13.73 21a2 2 0 0 1-3.46 0"/>
	</svg>`,

	/**
	 * Check dot SVG (sudah dibaca)
	 */
	check_svg: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
		<path d="M20 6 9 17l-5-5"/>
	</svg>`,

	/**
	 * Notification type icon colors
	 */
	type_colors: {
		Payment: "#2490EF",
		Subscription: "#4caf50",
		System: "#ff9800",
		Info: "#9e9e9e",
	},

	/**
	 * Initialize bell icon di navbar
	 */
	init() {
		try {
			// Tunggu DOM ready
			if (document.readyState === "loading") {
				document.addEventListener("DOMContentLoaded", () => {
					try {
						this._create();
					} catch (e) {
						console.warn("Qalcuity: Failed to create bell icon:", e);
					}
				});
			} else {
				this._create();
			}
		} catch (e) {
			console.warn("Qalcuity: Notification module init failed:", e);
		}
	},

	/**
	 * Create bell icon element
	 */
	_create() {
		// Cari navbar container
		const navbar = document.querySelector(".navbar .nav-bar-right, .desk-sidebar .sidebar-menu, .page-container .page-head");
		if (!navbar) {
			// Fallback: coba cari di header
			const header = document.querySelector("header, .app-header, .navbar");
			if (!header) return;
			this._insertIntoHeader(header);
			return;
		}

		this._insertIntoContainer(navbar);
	},

	/**
	 * Insert bell icon ke header
	 */
	_insertIntoHeader(header) {
		const container = header.querySelector(".nav-bar-right, .navbar-right, .header-actions");
		if (container) {
			this._insertIntoContainer(container);
		}
	},

	/**
	 * Insert bell icon ke container
	 */
	_insertIntoContainer(container) {
		// Cek apakah sudah ada
		if (document.getElementById("qalcuity-bell-icon")) return;

		const wrapper = document.createElement("div");
		wrapper.id = "qalcuity-bell-icon";
		wrapper.className = "qalcuity-bell-wrapper";
		wrapper.innerHTML = `
			<button class="qalcuity-bell-btn" title="Notifikasi" aria-label="Notifikasi">
				${this.bell_svg}
				<span class="qalcuity-bell-badge" style="display: none;">0</span>
			</button>
			<div class="qalcuity-bell-dropdown" style="display: none;">
				<div class="qalcuity-bell-header">
					<span class="qalcuity-bell-title">Notifikasi</span>
					<button class="qalcuity-bell-mark-all" title="Tandai semua sudah dibaca">
						${this.check_svg} Tandai semua
					</button>
				</div>
				<div class="qalcuity-bell-list">
					<div class="qalcuity-bell-empty">Tidak ada notifikasi</div>
				</div>
				<div class="qalcuity-bell-footer">
					<a href="/app/qalcuity-notification" class="qalcuity-bell-view-all">Lihat Semua</a>
				</div>
			</div>
		`;

		// Insert sebelum element pertama di container
		if (container.firstChild) {
			container.insertBefore(wrapper, container.firstChild);
		} else {
			container.appendChild(wrapper);
		}

		// Bind events
		this._bindEvents(wrapper);

		// Load initial count dari boot session
		this._updateBadge();

		// Set refresh interval (setiap 60 detik)
		setInterval(() => this._updateBadge(), 60000);
	},

	/**
	 * Bind click events
	 */
	_bindEvents(wrapper) {
		const btn = wrapper.querySelector(".qalcuity-bell-btn");
		const dropdown = wrapper.querySelector(".qalcuity-bell-dropdown");
		const markAllBtn = wrapper.querySelector(".qalcuity-bell-mark-all");

		// Toggle dropdown on bell click
		btn.addEventListener("click", (e) => {
			e.stopPropagation();
			const isVisible = dropdown.style.display !== "none";
			dropdown.style.display = isVisible ? "none" : "block";

			// Load notifikasi saat dropdown dibuka
			if (!isVisible) {
				this._loadNotifications();
			}
		});

		// Close dropdown when clicking outside
		document.addEventListener("click", (e) => {
			if (!wrapper.contains(e.target)) {
				dropdown.style.display = "none";
			}
		});

		// Mark all as read
		markAllBtn.addEventListener("click", (e) => {
			e.stopPropagation();
			this._markAllAsRead();
		});

		// Prevent dropdown close when clicking inside
		dropdown.addEventListener("click", (e) => {
			e.stopPropagation();
		});
	},

	/**
	 * Update badge count dari boot session
	 */
	_updateBadge() {
		const badge = document.querySelector(".qalcuity-bell-badge");
		if (!badge) return;

		// Ambil dari boot session
		const count = frappe.boot.qalcuity_unread_notifications || 0;
		if (count > 0) {
			badge.textContent = count > 99 ? "99+" : count;
			badge.style.display = "flex";
		} else {
			badge.style.display = "none";
		}
	},

	/**
	 * Load notifikasi via API
	 */
	_loadNotifications() {
		try {
			const listEl = document.querySelector(".qalcuity-bell-list");
			if (!listEl) return;

			// Show loading
			listEl.innerHTML = `<div class="qalcuity-bell-loading">Memuat notifikasi...</div>`;

			frappe.call({
				method: "qalcuity.qalcuity.api.notification.get_my_notifications",
				args: {
					limit_page_length: 10,
					start: 0,
				},
				callback: (r) => {
					if (r.message) {
						this._renderNotifications(listEl, r.message.notifications || []);
						// Update badge
						frappe.boot.qalcuity_unread_notifications = r.message.unread_count || 0;
						this._updateBadge();
					}
				},
				error: (err) => {
					console.warn("Qalcuity: Notification API not available:", err);
					// Graceful fallback — show empty state
					if (listEl) {
						listEl.innerHTML = `<div class="qalcuity-bell-empty">Notifikasi tidak tersedia</div>`;
					}
				},
			});
		} catch (e) {
			console.warn("Qalcuity: Failed to load notifications:", e);
			// Graceful fallback — bell icon tetap render tanpa notification
			const listEl = document.querySelector(".qalcuity-bell-list");
			if (listEl) {
				listEl.innerHTML = `<div class="qalcuity-bell-empty">Notifikasi tidak tersedia</div>`;
			}
		}
	},

	/**
	 * Render notification list
	 */
	_renderNotifications(listEl, notifications) {
		if (!notifications.length) {
			listEl.innerHTML = `<div class="qalcuity-bell-empty">Tidak ada notifikasi</div>`;
			return;
		}

		const html = notifications
			.map((n) => {
				const color = this.type_colors[n.notification_type] || "#9e9e9e";
				const unreadClass = n.is_read ? "" : " qalcuity-bell-unread";
				const time = frappe.datetime.str_to_user
					? frappe.datetime.str_to_user(n.timestamp)
					: n.timestamp;
				const link = n.link || "#";

				return `
				<div class="qalcuity-bell-item${unreadClass}" data-name="${n.name}" data-link="${link}">
					<div class="qalcuity-bell-item-dot" style="background-color: ${color};"></div>
					<div class="qalcuity-bell-item-content">
						<div class="qalcuity-bell-item-title">${__(n.title)}</div>
						<div class="qalcuity-bell-item-message">${__(n.message)}</div>
						<div class="qalcuity-bell-item-time">${time}</div>
					</div>
				</div>
			`;
			})
			.join("");

		listEl.innerHTML = html;

		// Bind click per item
		listEl.querySelectorAll(".qalcuity-bell-item").forEach((item) => {
			item.addEventListener("click", () => {
				const name = item.dataset.name;
				const link = item.dataset.link;

				// Mark as read
				this._markAsRead(name);

				// Navigate to link
				if (link && link !== "#") {
					frappe.set_route(link);
				}
			});
		});
	},

	/**
	 * Mark notification sebagai read
	 */
	_markAsRead(name) {
		try {
			frappe.call({
				method: "qalcuity.qalcuity.api.notification.mark_as_read",
				args: { notification_name: name },
				callback: () => {
					// Update UI
					const item = document.querySelector(`.qalcuity-bell-item[data-name="${name}"]`);
					if (item) {
						item.classList.remove("qalcuity-bell-unread");
					}
					// Decrease badge
					const current = frappe.boot.qalcuity_unread_notifications || 0;
					frappe.boot.qalcuity_unread_notifications = Math.max(0, current - 1);
					this._updateBadge();
				},
				error: (err) => {
					console.warn("Qalcuity: Failed to mark notification as read:", err);
				},
			});
		} catch (e) {
			console.warn("Qalcuity: Failed to mark notification as read:", e);
		}
	},

	/**
	 * Mark all sebagai read
	 */
	_markAllAsRead() {
		try {
			frappe.call({
				method: "qalcuity.qalcuity.api.notification.mark_all_as_read",
				callback: () => {
					// Update UI
					document.querySelectorAll(".qalcuity-bell-unread").forEach((el) => {
						el.classList.remove("qalcuity-bell-unread");
					});
					frappe.boot.qalcuity_unread_notifications = 0;
					this._updateBadge();
				},
				error: (err) => {
					console.warn("Qalcuity: Failed to mark all as read:", err);
				},
			});
		} catch (e) {
			console.warn("Qalcuity: Failed to mark all as read:", e);
		}
	},
};

// Initialize notifications on page load
$(document).ready(() => {
	qalcuity.notifications.init();
});

/**
 * Qalcuity ERP — Navigation Controller
 * Handles hamburger menu, dropdowns, active state, and role-based nav.
 */
qalcuity.navigation = {
	/**
	 * Initialize navigation on page load
	 */
	init() {
		const nav = document.getElementById("qalcuity-nav");
		if (!nav) return; // No nav on this page (e.g., register/login)

		this._detectRole();
		this._setActivePage();
		this._setUserName();
		this._bindHamburger();
		this._bindDropdowns();
		this._bindMobileMenuClose();
	},

	/**
	 * Detect if current user is admin/superadmin
	 * and add body class to show admin-only nav items
	 */
	_detectRole() {
		try {
			const roles = frappe.boot && frappe.boot.user
				? (frappe.boot.user.roles || [])
				: [];

			const isAdmin = roles.some(
				(r) =>
					r.role === "Qalcuity Superadmin" ||
					r.role === "Qalcuity Admin" ||
					r.role === "System Manager" ||
					r.role === "Administrator"
			);

			if (isAdmin) {
				document.body.classList.add("qalcuity-is-admin");
			}
		} catch (e) {
			// Silently fail — admin items stay hidden by default
		}
	},

	/**
	 * Set active nav link based on current URL path
	 */
	_setActivePage() {
		const path = window.location.pathname.replace(/^\/|\/$/g, "");

		// Map of path segments to nav data-page values
		const pageMap = {
			"dashboard": "dashboard",
			"my-payments": "my-payments",
			"subscription-history": "subscription-history",
			"admin-reviews": "admin-reviews",
			"profile": "profile",
			"account-status": "account-status",
			"pricing": "pricing",
			"checkout": "checkout",
		};

		const currentPage = pageMap[path] || path;

		// Set active on direct links
		document.querySelectorAll(".qalcuity-nav-link[data-page], .qalcuity-nav-dropdown-item[data-page]").forEach((el) => {
			if (el.getAttribute("data-page") === currentPage) {
				el.classList.add("active");
			}
		});

		// If a dropdown item is active, also highlight the parent dropdown toggle
		const activeDropdownItem = document.querySelector(
			".qalcuity-nav-dropdown-menu .qalcuity-nav-dropdown-item.active"
		);
		if (activeDropdownItem) {
			const dropdown = activeDropdownItem.closest(".qalcuity-nav-dropdown");
			if (dropdown) {
				const toggle = dropdown.querySelector(".qalcuity-nav-dropdown-toggle");
				if (toggle) toggle.classList.add("active");
			}
		}
	},

	/**
	 * Set user name in the nav user button
	 */
	_setUserName() {
		const nameEl = document.getElementById("qalcuity-nav-user-name");
		if (!nameEl) return;

		try {
			// Try frappe.boot first
			if (frappe && frappe.session && frappe.session.user) {
				const user = frappe.session.user;
				if (user && user !== "Guest") {
					// Use full_name from boot if available
					const bootUser = frappe.boot.user || {};
					nameEl.textContent = bootUser.full_name || bootUser.email || user.split("@")[0];
				} else {
					nameEl.textContent = "Guest";
				}
			}
		} catch (e) {
			nameEl.textContent = "User";
		}
	},

	/**
	 * Bind hamburger toggle button
	 */
	_bindHamburger() {
		const toggle = document.getElementById("qalcuity-nav-toggle");
		const menu = document.getElementById("qalcuity-nav-menu");
		if (!toggle || !menu) return;

		toggle.addEventListener("click", (e) => {
			e.stopPropagation();
			const isOpen = menu.classList.toggle("open");
			toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
			document.body.classList.toggle("nav-open", isOpen);

			// Change icon
			const icon = toggle.querySelector(".octicon");
			if (icon) {
				icon.classList.toggle("octicon-three-bars");
				icon.classList.toggle("octicon-x", isOpen);
				icon.classList.toggle("octicon-three-bars", !isOpen);
			}
		});
	},

	/**
	 * Bind dropdown toggles (both nav dropdown and user dropdown)
	 */
	_bindDropdowns() {
		// Nav dropdowns (e.g., Pembayaran)
		document.querySelectorAll(".qalcuity-nav-dropdown-toggle").forEach((toggle) => {
			toggle.addEventListener("click", (e) => {
				e.stopPropagation();
				const dropdown = toggle.closest(".qalcuity-nav-dropdown");

				// Close other open dropdowns
				document.querySelectorAll(".qalcuity-nav-dropdown.open").forEach((d) => {
					if (d !== dropdown) d.classList.remove("open");
				});

				dropdown.classList.toggle("open");
			});
		});

		// User dropdown
		const userBtn = document.getElementById("qalcuity-nav-user-btn");
		if (userBtn) {
			userBtn.addEventListener("click", (e) => {
				e.stopPropagation();
				const dropdown = userBtn.closest(".qalcuity-nav-dropdown");

				// Close other open dropdowns
				document.querySelectorAll(".qalcuity-nav-dropdown.open").forEach((d) => {
					if (d !== dropdown) d.classList.remove("open");
				});

				dropdown.classList.toggle("open");
			});
		}

		// Close dropdowns when clicking outside
		document.addEventListener("click", () => {
			document.querySelectorAll(".qalcuity-nav-dropdown.open").forEach((d) => {
				d.classList.remove("open");
			});
		});

		// Prevent dropdown menu clicks from closing
		document.querySelectorAll(".qalcuity-nav-dropdown-menu").forEach((menu) => {
			menu.addEventListener("click", (e) => {
				e.stopPropagation();
			});
		});
	},

	/**
	 * Close mobile menu when clicking a nav link
	 */
	_bindMobileMenuClose() {
		const menu = document.getElementById("qalcuity-nav-menu");
		const toggle = document.getElementById("qalcuity-nav-toggle");
		if (!menu || !toggle) return;

		menu.querySelectorAll(".qalcuity-nav-link, .qalcuity-nav-dropdown-item").forEach((link) => {
			// Only close for links that navigate (have href)
			if (link.getAttribute("href")) {
				link.addEventListener("click", () => {
					if (window.innerWidth <= 768) {
						menu.classList.remove("open");
						toggle.setAttribute("aria-expanded", "false");
						document.body.classList.remove("nav-open");
						const icon = toggle.querySelector(".octicon");
						if (icon) {
							icon.classList.remove("octicon-x");
							icon.classList.add("octicon-three-bars");
						}
					}
				});
			}
		});
	},
};

// Initialize navigation on page load
$(document).ready(() => {
	qalcuity.navigation.init();
});

/**
 * Qalcuity ERP — Desk Branding Overrides
 * Hides Frappe/ERPNext branding elements on desk pages.
 * Injected via CSS so it applies immediately without FOUC.
 */
(function () {
	var style = document.createElement('style');
	style.textContent = `
		/* ============================================
		   Qalcuity ERP — Desk Branding Hide Rules
		   Hides Frappe/ERPNext default branding on desk
		   ============================================ */

		/* Hide "Powered by Frappe" footer */
		.footer-frape,
		.footer-frape a,
		#website-footer .footer-frape,
		.frappe-footer .footer-frape {
			display: none !important;
		}

		/* Hide Frappe sidebar branding / logo */
		.desk-sidebar .sidebar-label img[alt*="Frappe"],
		.desk-sidebar .sidebar-label img[alt*="ERPNext"],
		.sidebar-menu .sidebar-label img[alt*="Frappe"],
		.sidebar-menu .sidebar-label img[alt*="ERPNext"] {
			display: none !important;
		}

		/* Hide Frappe/ERPNext images in sidebar */
		.desk-sidebar img[src*="frappe"],
		.desk-sidebar img[src*="erpnext"],
		.sidebar-menu img[src*="frappe"],
		.sidebar-menu img[src*="erpnext"] {
			display: none !important;
		}

		/* Hide Frappe/ERPNext images in navbar */
		.navbar img[src*="frappe"][alt*="Frappe"],
		.navbar img[src*="erpnext"][alt*="ERPNext"],
		.app-header img[src*="frappe"][alt*="Frappe"],
		.app-header img[src*="erpnext"][alt*="ERPNext"] {
			display: none !important;
		}

		/* Hide Frappe/ERPNext images globally on desk */
		img[src*="frappe"][alt*="Frappe"],
		img[src*="frappe"][alt*="framework"],
		img[src*="erpnext"][alt*="ERPNext"],
		img[src*="erpnext"][alt*="ERP"] {
			display: none !important;
		}

		/* Override Frappe default app icon color */
		.app-icon {
			background-color: #2490EF !important;
		}

		/* Override Frappe sidebar active indicator color */
		.desk-sidebar .sidebar-menu .active a,
		.sidebar-menu .active a {
			border-right-color: #2490EF !important;
		}

		/* Hide "Made with Frappe" / "Frappe Framework" in footer text */
		.footer-frape,
		.website-footer .footer-frape,
		.frappe-footer {
			font-size: 0 !important;
			height: 0 !important;
			padding: 0 !important;
			margin: 0 !important;
			overflow: hidden !important;
		}

		/* Override Frappe desk title to show Qalcuity */
		.page-head .page-title {
			font-weight: 600;
		}
	`;
	document.head.appendChild(style);
})();

// Log initialization
console.log("Qalcuity ERP v" + qalcuity.version + " loaded");
