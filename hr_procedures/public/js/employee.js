frappe.ui.form.on("Employee", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Employee Violations"), () => {
                frappe.route_options = { employee: frm.doc.name };
                frappe.set_route("query-report", "Employee Violation Register");
            }, __("HR Procedures"));
        }
    },
});
