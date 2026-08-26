frappe.listview_settings["Qalcuity Login Log"] = {
	"get_form": function (doc) {
		return "/app/qalcuity-login-log/" + encodeURIComponent(doc.name);
	},
};
