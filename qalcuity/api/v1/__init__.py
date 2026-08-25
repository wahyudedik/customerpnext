# Copyright (c) 2026, Qalcuity and contributors
# For license information, please see license.txt

"""
Qalcuity API v1 — Versioned Endpoints
=======================================

Centralized API router pattern untuk Qalcuity ERP.

Frappe Framework tidak memiliki built-in URL routing seperti Express/Flask.
Pendekatan kami:
- Module `qalcuity/qalcuity/api/v1/` sebagai namespace
- Wrapper functions yang memanggil existing implementations
- Auth validation (role/permission) di setiap wrapper
- Standard response format (success/error)

Usage:
    Dari client, panggil endpoint seperti:
    - frappe.call("qalcuity.qalcuity.api.v1.endpoints.get_plans")
    - frappe.call("qalcuity.qalcuity.api.v1.endpoints.submit_payment", {...})

Structure:
    qalcuity/qalcuity/api/v1/
    ├── __init__.py      — Module init & documentation
    ├── auth.py          — Authentication & authorization helpers
    ├── responses.py     — Standard response format
    └── endpoints.py     — All v1 wrapper endpoints
"""

__version__ = "1.0.0"
