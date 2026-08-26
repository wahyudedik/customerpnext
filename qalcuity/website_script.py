"""
Qalcuity ERP — Website Script Hook

Injects JavaScript and CSS into ALL website pages including the login page.
This is the most reliable way to override Frappe/ERPNext branding on website
pages because:
  - `override_website_page_render_context` does NOT fire for login page
  - `app_include_css`/`app_include_js` only load on Desk pages, NOT website pages
  - `website_script` hook is injected into every page via frappe's base template
"""


def get_website_script():
    """Return JavaScript + CSS to be injected into all website pages."""
    return """
    <style>
    /* ============================================================
       Qalcuity ERP — Website Branding CSS
       Overrides Frappe/ERPNext default branding on website pages
       ============================================================ */

    /* --- Login Page Branding --- */
    .page-card .page-card-head .page-card-image {
        max-width: 120px;
        margin: 0 auto 16px;
    }

    .page-card .page-card-head .page-card-image img {
        max-height: 60px;
        width: auto;
    }

    /* Override login page title */
    .page-card .page-card-head h4,
    .page-card .page-card-head h3 {
        font-size: 20px;
        font-weight: 600;
        color: #1a202c;
    }

    [data-theme="dark"] .page-card .page-card-head h4,
    [data-theme="dark"] .page-card .page-card-head h3 {
        color: #e2e8f0;
    }

    /* Brand logo in login page */
    .page-card .page-card-head img[alt*="Frappe"],
    .page-card .page-card-head img[alt*="ERPNext"] {
        display: none !important;
    }

    .qalcuity-website-logo {
        max-height: 60px;
        width: auto;
        margin: 0 auto 16px;
        display: block;
    }

    /* Navbar branding */
    .navbar .navbar-brand img[alt*="Frappe"],
    .navbar .navbar-brand img[alt*="ERPNext"] {
        display: none !important;
    }

    .navbar .navbar-brand .qalcuity-nav-logo {
        max-height: 24px;
        width: auto;
    }

    /* Footer branding */
    .footer-frape img[alt*="Frappe"],
    .website-footer img[alt*="Frappe"] {
        display: none !important;
    }

    /* Login links styling */
    .qalcuity-login-links {
        text-align: center;
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid #e2e8f0;
    }

    [data-theme="dark"] .qalcuity-login-links {
        border-top-color: #4a5568;
    }

    .qalcuity-login-forgot-link {
        margin-bottom: 8px;
    }

    .qalcuity-login-register-link p {
        margin: 0;
        color: #6c757d;
        font-size: 14px;
    }

    .qalcuity-register-cta {
        color: #2490ef;
        font-weight: 600;
        text-decoration: none;
    }

    .qalcuity-register-cta:hover {
        text-decoration: underline;
        color: #1a7fd4;
    }

    /* Global override: hide any Frappe/ERPNext branding images */
    img[src*="frappe"][alt*="Frappe"],
    img[src*="frappe"][alt*="framework"],
    img[src*="erpnext"][alt*="ERPNext"],
    img[src*="erpnext"][alt*="ERP"] {
        display: none !important;
    }

    /* Splash screen override */
    .splash-image img {
        max-height: 80px;
        width: auto;
    }
    </style>

    <script>
    (function() {
        'use strict';

        var QALCUITY_LOGO = '/assets/qalcuity/images/logo-dark.png';
        var QALCUITY_LOGO_LIGHT = '/assets/qalcuity/images/logo-light.png';

        /**
         * Determine if current page is the login page.
         */
        function isLoginPage() {
            var path = window.location.pathname || '';
            var hash = window.location.hash || '';
            return path === '/login' ||
                   path === '/#login' ||
                   hash.indexOf('login') !== -1 ||
                   document.querySelector('.page-card[data-page="login"]') !== null ||
                   document.querySelector('.for-login') !== null;
        }

        /**
         * Replace the login page title "Login to Frappe" with "Login to Qalcuity".
         */
        function fixLoginTitle() {
            var headings = document.querySelectorAll(
                '.page-card .page-card-head h4, ' +
                '.page-card .page-card-head h3, ' +
                '.page-card h4, .page-card h3, ' +
                '.for-login h4, .for-login h3'
            );
            headings.forEach(function(el) {
                var text = el.textContent || '';
                if (text.indexOf('Frappe') !== -1 || text.indexOf('ERPNext') !== -1) {
                    el.textContent = text
                        .replace(/Login to Frappe/gi, 'Login to Qalcuity')
                        .replace(/Frappe Framework/gi, 'Qalcuity ERP')
                        .replace(/ERPNext/gi, 'Qalcuity ERP')
                        .replace(/Frappe/gi, 'Qalcuity');
                }
                // If heading is empty or generic, set it
                if (!text.trim() || text.trim() === 'Sign In' || text.trim() === 'Login') {
                    el.textContent = 'Login to Qalcuity';
                }
            });
        }

        /**
         * Replace login page logo image with Qalcuity logo.
         */
        function fixLoginLogo() {
            // Look for the login card image
            var cardImages = document.querySelectorAll(
                '.page-card .page-card-head img, ' +
                '.page-card .page-card-image img, ' +
                '.for-login .page-card-head img, ' +
                '.login-brand img'
            );
            cardImages.forEach(function(img) {
                var src = img.getAttribute('src') || '';
                if (src.indexOf('frappe') !== -1 ||
                    src.indexOf('erpnext') !== -1 ||
                    src.indexOf('logo') === -1 ||
                    src.indexOf('qalcuity') === -1) {
                    // Check theme
                    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                    img.setAttribute('src', isDark ? QALCUITY_LOGO_LIGHT : QALCUITY_LOGO);
                    img.setAttribute('alt', 'Qalcuity ERP');
                    img.classList.add('qalcuity-website-logo');
                }
            });
        }

        /**
         * Fix the brand_html area — inject Qalcuity logo if not already present.
         */
        function fixBrandHtml() {
            var brandArea = document.querySelector('.page-card .page-card-head');
            if (!brandArea) return;

            var existingLogo = brandArea.querySelector('img[alt*="Qalcuity"]');
            if (existingLogo) return; // Already fixed

            var existingImages = brandArea.querySelectorAll('img');
            existingImages.forEach(function(img) {
                var src = img.getAttribute('src') || '';
                if (src.indexOf('qalcuity') === -1) {
                    // Replace non-Qalcuity images
                    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                    img.setAttribute('src', isDark ? QALCUITY_LOGO_LIGHT : QALCUITY_LOGO);
                    img.setAttribute('alt', 'Qalcuity ERP');
                }
            });

            // If no images at all, add one
            if (existingImages.length === 0) {
                var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                var newImg = document.createElement('img');
                newImg.setAttribute('src', isDark ? QALCUITY_LOGO_LIGHT : QALCUITY_LOGO);
                newImg.setAttribute('alt', 'Qalcuity ERP');
                newImg.setAttribute('style', 'height: 60px; margin: 0 auto 16px; display: block;');
                newImg.classList.add('qalcuity-website-logo');
                brandArea.insertBefore(newImg, brandArea.firstChild);
            }
        }

        /**
         * Fix document title.
         */
        function fixDocumentTitle() {
            var title = document.title || '';
            if (title.indexOf('Frappe') !== -1 || title.indexOf('ERPNext') !== -1) {
                document.title = title
                    .replace(/Frappe Framework/gi, 'Qalcuity ERP')
                    .replace(/ERPNext/gi, 'Qalcuity ERP')
                    .replace(/Frappe/gi, 'Qalcuity');
            }
            if (isLoginPage() && (title.indexOf('Login') !== -1 || title.indexOf('Sign In') !== -1)) {
                if (title.indexOf('Qalcuity') === -1) {
                    document.title = 'Login - Qalcuity ERP';
                }
            }
        }

        /**
         * Fix all Frappe/ERPNext text references on the page.
         */
        function fixBrandingText() {
            // Fix page title tag
            fixDocumentTitle();

            // Fix any remaining Frappe/ERPNext text in visible elements
            var walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            var textNodes = [];
            while (walker.nextNode()) {
                textNodes.push(walker.currentNode);
            }

            textNodes.forEach(function(node) {
                var text = node.textContent || '';
                if (text.indexOf('Frappe') !== -1 && text.indexOf('Qalcuity') === -1) {
                    // Only replace in certain contexts to avoid breaking things
                    var parent = node.parentElement;
                    if (parent && !parent.matches('script, style, code, pre, textarea')) {
                        node.textContent = text
                            .replace(/Frappe Framework/g, 'Qalcuity ERP')
                            .replace(/Frappe/g, 'Qalcuity');
                    }
                }
            });
        }

        /**
         * Fix the navbar "Home" link and branding.
         */
        function fixNavbar() {
            // Fix navbar brand
            var navBrand = document.querySelector('.navbar .navbar-brand, .website-sidebar .sidebar-label');
            if (navBrand) {
                var brandText = navBrand.textContent || '';
                if (brandText.indexOf('Frappe') !== -1 || brandText.indexOf('ERPNext') !== -1) {
                    navBrand.textContent = brandText
                        .replace(/Frappe Framework/g, 'Qalcuity ERP')
                        .replace(/ERPNext/g, 'Qalcuity ERP')
                        .replace(/Frappe/g, 'Qalcuity');
                }
            }

            // Fix navbar images
            var navImages = document.querySelectorAll('.navbar img, .website-sidebar img');
            navImages.forEach(function(img) {
                var src = img.getAttribute('src') || '';
                if (src.indexOf('frappe') !== -1 || src.indexOf('erpnext') !== -1) {
                    img.setAttribute('src', QALCUITY_LOGO);
                    img.setAttribute('alt', 'Qalcuity');
                    img.classList.add('qalcuity-nav-logo');
                }
            });
        }

        /**
         * Main initialization — run all fixes.
         */
        function init() {
            fixLoginTitle();
            fixLoginLogo();
            fixBrandHtml();
            fixBrandingText();
            fixNavbar();
        }

        // Run immediately if DOM is ready, otherwise wait
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                init();
                // Run again after a short delay to catch dynamically loaded content
                setTimeout(init, 500);
                setTimeout(init, 1500);
            });
        } else {
            init();
            setTimeout(init, 500);
            setTimeout(init, 1500);
        }

        // Observe for DOM changes (for SPA-like navigation)
        if (typeof MutationObserver !== 'undefined') {
            var observer = new MutationObserver(function(mutations) {
                var shouldRefix = false;
                mutations.forEach(function(mutation) {
                    if (mutation.addedNodes.length > 0) {
                        shouldRefix = true;
                    }
                });
                if (shouldRefix) {
                    setTimeout(init, 100);
                }
            });
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    })();
    </script>
    """
