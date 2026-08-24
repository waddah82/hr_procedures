from datetime import date

import frappe
from frappe import _
from frappe.utils import add_months, cint, flt, getdate


def get_active_policy(company, violation_date):
    violation_date = getdate(violation_date)
    policies = frappe.get_all(
        "HR Violation Policy",
        filters={"company": company, "is_active": 1},
        fields=["name", "effective_from", "effective_to"],
        order_by="effective_from desc",
    )
    for row in policies:
        start = getdate(row.effective_from) if row.effective_from else None
        end = getdate(row.effective_to) if row.effective_to else None
        if start and violation_date < start:
            continue
        if end and violation_date > end:
            continue
        return row.name
    return None


def occurrence_window(employee, violation_type, violation_date):
    violation_date = getdate(violation_date)
    vtype = frappe.get_cached_doc("HR Violation Type", violation_type)
    method = vtype.repeat_counting_method or "Contractual Year"

    if method == "All Time":
        return date(1900, 1, 1), violation_date

    if method == "Calendar Year":
        return date(violation_date.year, 1, 1), violation_date

    if method == "Rolling 12 Months":
        return add_months(violation_date, -12), violation_date

    employee_doc = frappe.get_cached_doc("Employee", employee)
    joining = getdate(employee_doc.date_of_joining or violation_date)
    anniversary_year = violation_date.year
    try:
        anniversary = joining.replace(year=anniversary_year)
    except ValueError:
        anniversary = joining.replace(year=anniversary_year, day=28)
    if anniversary > violation_date:
        try:
            start = joining.replace(year=anniversary_year - 1)
        except ValueError:
            start = joining.replace(year=anniversary_year - 1, day=28)
    else:
        start = anniversary
    return start, violation_date


def calculate_occurrence(employee, violation_type, violation_date, current_name=None):
    start, end = occurrence_window(employee, violation_type, violation_date)
    filters = {
        "employee": employee,
        "violation_type": violation_type,
        "violation_date": ["between", [start, end]],
        "docstatus": 1,
    }
    names = frappe.get_all("Employee Violation", filters=filters, pluck="name")
    if current_name and current_name in names:
        names.remove(current_name)
    return len(names) + 1


def get_policy_penalty(policy_name, violation_type, occurrence_no):
    if not policy_name:
        return None
    row = frappe.db.get_value(
        "HR Violation Policy Row",
        {"parent": policy_name, "violation_type": violation_type},
        [
            "occurrence_1_penalty",
            "occurrence_2_penalty",
            "occurrence_3_penalty",
            "occurrence_4_penalty",
        ],
        as_dict=True,
    )
    if not row:
        return None
    tier = min(max(cint(occurrence_no), 1), 4)
    return row.get(f"occurrence_{tier}_penalty")


def get_daily_wage(employee, violation_date, settings, strict=True):
    divisor = flt(settings.daily_wage_divisor) or 30
    source = settings.daily_wage_source or "Salary Structure Assignment Base"

    if source == "Last Salary Slip Component":
        component = settings.wage_salary_component
        if not component:
            if not strict:
                return None
            frappe.throw(_("Wage Salary Component is required in HR Procedures Settings."))
        slips = frappe.get_all(
            "Salary Slip",
            filters={
                "employee": employee,
                "docstatus": 1,
                "start_date": ["<=", violation_date],
            },
            fields=["name"],
            order_by="start_date desc",
            limit=1,
        )
        if not slips:
            if not strict:
                return None
            frappe.throw(_("No submitted Salary Slip was found to calculate the daily wage."))
        amount = frappe.db.get_value(
            "Salary Detail",
            {"parent": slips[0].name, "salary_component": component},
            "amount",
        )
        if amount is None:
            if not strict:
                return None
            frappe.throw(_("The configured wage component was not found in the latest Salary Slip."))
        return flt(amount) / divisor

    assignment = frappe.get_all(
        "Salary Structure Assignment",
        filters={
            "employee": employee,
            "docstatus": 1,
            "from_date": ["<=", violation_date],
        },
        fields=["base"],
        order_by="from_date desc",
        limit=1,
    )
    if not assignment:
        if not strict:
            return None
        frappe.throw(_("No submitted Salary Structure Assignment was found to calculate the daily wage."))
    return flt(assignment[0].base) / divisor


def calculate_penalty_amount(penalty_name, employee, violation_date, metrics=None, strict=True):
    if not penalty_name:
        return 0, ""

    metrics = metrics or {}
    penalty = frappe.get_cached_doc("HR Penalty Template", penalty_name)
    description = penalty.description or penalty.penalty_name

    if penalty.penalty_type not in ("Salary Deduction", "Composite"):
        return 0, description

    settings = frappe.get_single("HR Procedures Settings")
    basis = penalty.deduction_basis
    value = flt(penalty.deduction_value)

    needs_daily_wage = basis in (
        "Percentage of Daily Wage",
        "Days of Daily Wage",
        "Minutes of Wage",
        "Hours of Wage",
    ) or bool(
        penalty.add_actual_late_minutes
        or penalty.add_actual_early_exit_minutes
        or (penalty.add_actual_absence_days and getattr(settings, "add_absence_wage_through_additional_salary", 0))
    )

    daily = None
    if needs_daily_wage:
        daily = get_daily_wage(employee, violation_date, settings, strict=strict)
        if daily is None:
            return 0, _("Penalty amount pending until payroll wage data is available. {0}").format(description)

    amount = 0
    if basis == "Percentage of Daily Wage":
        amount = daily * value / 100
    elif basis == "Days of Daily Wage":
        amount = daily * value
    elif basis == "Fixed Amount":
        amount = value
    elif basis == "Minutes of Wage":
        work_hours = flt(settings.standard_work_hours_per_day) or 8
        amount = (daily / (work_hours * 60)) * value
    elif basis == "Hours of Wage":
        work_hours = flt(settings.standard_work_hours_per_day) or 8
        amount = (daily / work_hours) * value

    if daily is not None:
        work_hours = flt(settings.standard_work_hours_per_day) or 8
        per_minute = daily / (work_hours * 60)
        if penalty.add_actual_late_minutes:
            amount += per_minute * flt(metrics.get("late_minutes"))
        if penalty.add_actual_early_exit_minutes:
            amount += per_minute * flt(metrics.get("early_exit_minutes"))
        if penalty.add_actual_absence_days and getattr(settings, "add_absence_wage_through_additional_salary", 0):
            amount += daily * flt(metrics.get("absence_days"))

    return round(amount, 2), description


def validate_override_permission(decision, settings):
    if decision == "Waive Penalty" and not settings.allow_penalty_waiver:
        frappe.throw(_("Penalty waiver is disabled in HR Procedures Settings."))
    if decision == "Apply Alternative Penalty" and not settings.allow_alternative_penalty:
        frappe.throw(_("Alternative penalties are disabled in HR Procedures Settings."))

    if decision in ("Waive Penalty", "Apply Alternative Penalty"):
        role = settings.penalty_override_role
        if role and role not in frappe.get_roles():
            frappe.throw(_("You do not have the role required to override the deserved penalty: {0}").format(role))


def execute_penalty(violation):
    if violation.penalty_decision == "Waive Penalty" or not violation.final_penalty:
        violation.db_set("execution_status", "Waived", update_modified=False)
        return

    penalty = frappe.get_cached_doc("HR Penalty Template", violation.final_penalty)
    if penalty.penalty_type == "Salary Deduction":
        create_additional_salary(violation)
        violation.db_set("execution_status", "Executed", update_modified=False)
        return

    if penalty.penalty_type in ("Warning", "Administrative Action"):
        create_administrative_action(violation, penalty)
        violation.db_set("execution_status", "Pending Administrative Action", update_modified=False)
        return

    if penalty.penalty_type == "Composite":
        created_salary = False
        created_action = False
        if flt(violation.final_deduction_amount) > 0:
            create_additional_salary(violation)
            created_salary = True
        if penalty.warning_type or penalty.administrative_action_type:
            create_administrative_action(violation, penalty)
            created_action = True
        if created_action:
            violation.db_set("execution_status", "Pending Administrative Action", update_modified=False)
        elif created_salary:
            violation.db_set("execution_status", "Executed", update_modified=False)
        else:
            violation.db_set("execution_status", "No Action", update_modified=False)
        return

    violation.db_set("execution_status", "No Action", update_modified=False)


def create_additional_salary(violation):
    settings = frappe.get_single("HR Procedures Settings")
    if not settings.deduction_salary_component:
        frappe.throw(_("Deduction Salary Component is required in HR Procedures Settings."))
    if flt(violation.final_deduction_amount) <= 0:
        frappe.throw(_("The final deduction amount must be greater than zero."))

    additional = frappe.new_doc("Additional Salary")
    additional.employee = violation.employee
    additional.salary_component = settings.deduction_salary_component
    additional.amount = flt(violation.final_deduction_amount)
    additional.payroll_date = violation.violation_date
    if additional.meta.has_field("company"):
        additional.company = violation.company
    if additional.meta.has_field("ref_doctype"):
        additional.ref_doctype = "Employee Violation"
    if additional.meta.has_field("ref_docname"):
        additional.ref_docname = violation.name
    additional.insert(ignore_permissions=True)

    if settings.submit_additional_salary_automatically:
        additional.submit()

    violation.db_set("additional_salary", additional.name, update_modified=False)


def create_administrative_action(violation, penalty):
    action = frappe.new_doc("HR Administrative Action")
    action.employee = violation.employee
    action.company = violation.company
    action.employee_violation = violation.name
    action.penalty_template = penalty.name
    if penalty.warning_type:
        action.action_type = penalty.warning_type
    elif penalty.administrative_action_type:
        action.action_type = penalty.administrative_action_type
    else:
        action.action_type = "Other"
    action.action_date = violation.violation_date
    action.status = "Pending"
    action.details = penalty.description
    action.insert(ignore_permissions=True)
    violation.db_set("administrative_action", action.name, update_modified=False)


def reverse_execution(violation):
    if violation.additional_salary:
        doc = frappe.get_doc("Additional Salary", violation.additional_salary)
        if doc.docstatus == 1:
            doc.cancel()
        if doc.docstatus == 0:
            frappe.delete_doc("Additional Salary", doc.name, ignore_permissions=True)

    if violation.administrative_action and frappe.db.exists("HR Administrative Action", violation.administrative_action):
        action = frappe.get_doc("HR Administrative Action", violation.administrative_action)
        if action.status == "Executed":
            frappe.throw(_("The linked administrative action is already executed and must be reversed manually before cancelling the violation."))
        action.status = "Cancelled"
        action.save(ignore_permissions=True)
