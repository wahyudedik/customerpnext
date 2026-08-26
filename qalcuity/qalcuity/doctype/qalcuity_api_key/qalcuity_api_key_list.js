// Copyright (c) 2026, Qalcuity and contributors
// For license information, please see license.txt

frappe.listview_settings['Qalcuity Api Key'] = {
    get_indicator: function (doc) {
        if (doc.is_active) {
            return [__('Active'), 'green', 'is_active,=,1'];
        } else {
            return [__('Revoked'), 'red', 'is_active,=,0'];
        }
    },
    formatters: {
        api_key: function (value) {
            if (value && value.length > 10) {
                return value.substring(0, 12) + '...' + value.substring(value.length - 6);
            }
            return value;
        }
    },
    onload: function (listview) {
        // Add bulk revoke button
        listview.page.add_menu_item(__('Bulk Revoke'), function () {
            var selected = listview.get_checked_items();
            if (!selected.length) {
                frappe.msgprint(__('Please select at least one API key.'));
                return;
            }
            frappe.confirm(
                __('Revoke {0} selected API key(s)?', [selected.length]),
                function () {
                    selected.forEach(function (item) {
                        frappe.call({
                            method: 'qalcuity.qalcuity.api.api_keys.revoke_api_key',
                            args: { api_key_name: item.name },
                            callback: function () {
                                listview.refresh();
                            }
                        });
                    });
                }
            );
        });
    }
};
