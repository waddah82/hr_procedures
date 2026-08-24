import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": _("Violation"), "fieldname": "name", "fieldtype": "Link", "options": "Employee Violation", "width": 150},
        {"label": _("Date"), "fieldname": "violation_date", "fieldtype": "Date", "width": 100},
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 130},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": _("Violation Type"), "fieldname": "violation_type", "fieldtype": "Link", "options": "HR Violation Type", "width": 160},
        {"label": _("Occurrence Number"), "fieldname": "occurrence_no", "fieldtype": "Int", "width": 100},
        {"label": _("Deserved Penalty"), "fieldname": "deserved_penalty", "fieldtype": "Link", "options": "HR Penalty Template", "width": 170},
        {"label": _("Penalty Decision"), "fieldname": "penalty_decision", "fieldtype": "Data", "width": 170},
        {"label": _("Final Penalty"), "fieldname": "final_penalty", "fieldtype": "Link", "options": "HR Penalty Template", "width": 170},
        {"label": _("Deserved Deduction Amount"), "fieldname": "deserved_deduction_amount", "fieldtype": "Currency", "width": 140},
        {"label": _("Final Deduction Amount"), "fieldname": "final_deduction_amount", "fieldtype": "Currency", "width": 140},
        {"label": _("Execution Status"), "fieldname": "execution_status", "fieldtype": "Data", "width": 150},
        {"label": _("Source"), "fieldname": "source", "fieldtype": "Data", "width": 100},
        {"label": _("Additional Salary"), "fieldname": "additional_salary", "fieldtype": "Link", "options": "Additional Salary", "width": 150},
    ]


def get_data(filters):
    conditions = ["docstatus = 1"]
    values = {}

    for field in ("company", "employee", "department", "violation_type", "source", "penalty_decision"):
        if filters.get(field):
            conditions.append(f"{field} = %({field})s")
            values[field] = filters[field]

    if filters.get("from_date"):
        conditions.append("violation_date >= %(from_date)s")
        values["from_date"] = filters.from_date
    if filters.get("to_date"):
        conditions.append("violation_date <= %(to_date)s")
        values["to_date"] = filters.to_date

    return frappe.db.sql(
        f"""
        SELECT
            name, violation_date, employee, employee_name, department, violation_type,
            occurrence_no, deserved_penalty, penalty_decision, final_penalty,
            deserved_deduction_amount, final_deduction_amount, execution_status,
            source, additional_salary
        FROM `tabEmployee Violation`
        WHERE {' AND '.join(conditions)}
        ORDER BY violation_date DESC, creation DESC
        """,
        values,
        as_dict=True,
    )
