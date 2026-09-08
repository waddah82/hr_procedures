import frappe
from frappe.utils import flt

from hr_procedures.utils.penalties import get_active_policy


def on_submit(doc, method=None):
    """Attendance is retained only as the absence source.

    Late entry and early exit are detected from Employee Checkin directly.
    """
    settings = frappe.get_single("HR Procedures Settings")
    if not settings.enable_automatic_detection:
        return

    if getattr(doc, "status", None) != "Absent":
        return

    _create_absence_violation(doc)


def on_cancel(doc, method=None):
    drafts = frappe.get_all(
        "Employee Violation",
        filters={
            "reference_doctype": "Attendance",
            "reference_name": doc.name,
            "source": "Automatic",
            "docstatus": 0,
        },
        pluck="name",
    )
    for name in drafts:
        frappe.delete_doc("Employee Violation", name, ignore_permissions=True)


def _create_absence_violation(attendance):
    if not get_active_policy(attendance.company, attendance.attendance_date):
        return {"status": "no_active_policy"}

    candidates = frappe.get_all(
        "HR Violation Type",
        filters={
            "active": 1,
            "detection_source": "Attendance",
            "detection_rule": "Absence",
        },
        fields=["name", "requires_hr_confirmation"],
        order_by="modified desc",
        limit=1,
    )
    if not candidates:
        return

    match = candidates[0]
    duplicate = frappe.db.exists(
        "Employee Violation",
        {
            "reference_doctype": "Attendance",
            "reference_name": attendance.name,
            "violation_type": match.name,
            "docstatus": ["<", 2],
        },
    )
    if duplicate:
        return

    violation = frappe.new_doc("Employee Violation")
    violation.employee = attendance.employee
    violation.company = attendance.company
    violation.violation_date = attendance.attendance_date
    violation.violation_type = match.name
    violation.source = "Automatic"
    violation.reference_doctype = "Attendance"
    violation.reference_name = attendance.name
    violation.absence_days = 1
    violation.requires_hr_confirmation = match.requires_hr_confirmation
    violation.flags.ignore_permissions = True
    violation.insert()
    return {"status": "created", "violation": violation.name}
