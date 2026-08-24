import frappe


def execute():
    obsolete_drafts = frappe.get_all(
        "Employee Violation",
        filters={
            "source": "Automatic",
            "reference_doctype": "Attendance",
            "docstatus": 0,
        },
        fields=["name", "late_minutes", "early_exit_minutes", "absence_days"],
    )

    for row in obsolete_drafts:
        if (row.late_minutes or row.early_exit_minutes) and not row.absence_days:
            frappe.delete_doc("Employee Violation", row.name, ignore_permissions=True)
