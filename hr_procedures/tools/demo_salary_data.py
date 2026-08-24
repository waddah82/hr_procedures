from __future__ import annotations

from datetime import date

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, today


DEMO_DEVICE_PREFIX = "HRP-DEMO-"
DEMO_BASIC_COMPONENT = "HRP Demo Basic"
DEMO_DEDUCTION_COMPONENT = "HRP Disciplinary Deduction"
DEMO_SALARY_STRUCTURE_PREFIX = "HRP Demo Monthly Salary"

# Monthly base amounts are intentionally different so penalty calculations
# can be verified easily. With a divisor of 30 the daily wages become:
# 10,000 / 12,000 / 15,000 / 20,000 / 25,000 / 30,000.
DEMO_MONTHLY_BASE = {
    "001": 300000,
    "002": 360000,
    "003": 450000,
    "004": 600000,
    "005": 750000,
    "006": 900000,
}


def seed_demo_salary_data(company: str | None = None, configure_hr_procedures: int = 1):
    """Create payroll test data for the HR Procedures demo employees.

    Creates/ensures:
    - Earning Salary Component: HRP Demo Basic
    - Deduction Salary Component: HRP Disciplinary Deduction
    - One submitted monthly Salary Structure for the selected company
    - One submitted Salary Structure Assignment for every HRP-DEMO-* employee
    - HR Procedures Settings configured to calculate daily wage from SSA Base

    Safe to run more than once. Existing submitted assignments that already
    cover the demo period are not duplicated.
    """
    company = company or _get_company_for_demo_employees()
    currency = frappe.db.get_value("Company", company, "default_currency")
    if not currency:
        frappe.throw(_("Default Currency is required on Company {0}.").format(company))

    _ensure_salary_component(
        component_name=DEMO_BASIC_COMPONENT,
        abbr="HRPB",
        component_type="Earning",
        depends_on_payment_days=0,
        amount_based_on_formula=1,
        formula="base",
    )
    _ensure_salary_component(
        component_name=DEMO_DEDUCTION_COMPONENT,
        abbr="HRPDD",
        component_type="Deduction",
        depends_on_payment_days=0,
        amount_based_on_formula=0,
        formula="",
    )

    salary_structure = _ensure_salary_structure(company, currency)
    employees = _get_demo_employees(company)
    if not employees:
        frappe.throw(
            _(
                "No HR Procedures demo employees were found. Run seed_demo_data first."
            )
        )

    result = {
        "company": company,
        "currency": currency,
        "salary_structure": salary_structure,
        "basic_component": DEMO_BASIC_COMPONENT,
        "deduction_component": DEMO_DEDUCTION_COMPONENT,
        "created_assignments": [],
        "existing_assignments": [],
        "updated_draft_assignments": [],
        "missing_base_mapping": [],
    }

    for employee in employees:
        key = _device_key(employee.attendance_device_id)
        base = flt(DEMO_MONTHLY_BASE.get(key))
        if not base:
            result["missing_base_mapping"].append(employee.name)
            continue

        from_date = _assignment_from_date(employee.name)
        status, assignment_name = _ensure_salary_assignment(
            employee=employee.name,
            company=company,
            salary_structure=salary_structure,
            from_date=from_date,
            base=base,
        )
        result[f"{status}_assignments"].append(
            {
                "name": assignment_name,
                "employee": employee.name,
                "employee_name": employee.employee_name,
                "monthly_base": base,
                "daily_wage_at_30": base / 30,
                "from_date": str(from_date),
            }
        )

    if cint(configure_hr_procedures):
        _configure_hr_procedures_settings()
        result["hr_procedures_settings_configured"] = 1
    else:
        result["hr_procedures_settings_configured"] = 0

    frappe.db.commit()
    result["message"] = _("Demo salary data was created successfully.")
    return result


def get_demo_salary_summary(company: str | None = None):
    company = company or _get_company_for_demo_employees()
    employees = _get_demo_employees(company)
    employee_names = [row.name for row in employees]

    assignments = []
    if employee_names:
        assignments = frappe.get_all(
            "Salary Structure Assignment",
            filters={
                "employee": ["in", employee_names],
                "docstatus": 1,
            },
            fields=[
                "name",
                "employee",
                "employee_name",
                "salary_structure",
                "from_date",
                "base",
                "currency",
            ],
            order_by="employee asc, from_date desc",
        )

    return {
        "company": company,
        "demo_employee_count": len(employees),
        "submitted_assignment_count": len(assignments),
        "assignments": assignments,
        "basic_component_exists": bool(frappe.db.exists("Salary Component", DEMO_BASIC_COMPONENT)),
        "deduction_component_exists": bool(
            frappe.db.exists("Salary Component", DEMO_DEDUCTION_COMPONENT)
        ),
        "configured_deduction_component": frappe.db.get_single_value(
            "HR Procedures Settings", "deduction_salary_component"
        ),
        "daily_wage_source": frappe.db.get_single_value(
            "HR Procedures Settings", "daily_wage_source"
        ),
        "daily_wage_divisor": frappe.db.get_single_value(
            "HR Procedures Settings", "daily_wage_divisor"
        ),
    }


def _get_company_for_demo_employees() -> str:
    company = frappe.db.get_value(
        "Employee",
        {"attendance_device_id": ["like", f"{DEMO_DEVICE_PREFIX}%"]},
        "company",
        order_by="creation asc",
    )
    if company:
        return company

    companies = frappe.get_all("Company", pluck="name", order_by="creation asc", limit=1)
    if not companies:
        frappe.throw(_("Create a Company before generating demo salary data."))
    return companies[0]


def _get_demo_employees(company: str):
    return frappe.get_all(
        "Employee",
        filters={
            "company": company,
            "attendance_device_id": ["like", f"{DEMO_DEVICE_PREFIX}%"],
            "status": "Active",
        },
        fields=["name", "employee_name", "attendance_device_id", "date_of_joining"],
        order_by="attendance_device_id asc",
    )


def _device_key(device_id: str | None) -> str:
    if not device_id:
        return ""
    return device_id.removeprefix(DEMO_DEVICE_PREFIX)


def _ensure_salary_component(
    component_name: str,
    abbr: str,
    component_type: str,
    depends_on_payment_days: int,
    amount_based_on_formula: int,
    formula: str,
):
    if frappe.db.exists("Salary Component", component_name):
        doc = frappe.get_doc("Salary Component", component_name)
        changed = False
        desired = {
            "salary_component_abbr": abbr,
            "type": component_type,
            "depends_on_payment_days": depends_on_payment_days,
            "is_tax_applicable": 0,
            "disabled": 0,
            "amount_based_on_formula": amount_based_on_formula,
            "formula": formula,
        }
        for fieldname, value in desired.items():
            if doc.meta.has_field(fieldname) and doc.get(fieldname) != value:
                doc.set(fieldname, value)
                changed = True
        if changed:
            doc.save(ignore_permissions=True)
        return doc.name

    doc = frappe.new_doc("Salary Component")
    doc.salary_component = component_name
    doc.salary_component_abbr = abbr
    doc.type = component_type
    doc.depends_on_payment_days = depends_on_payment_days
    doc.is_tax_applicable = 0
    doc.disabled = 0
    if doc.meta.has_field("amount_based_on_formula"):
        doc.amount_based_on_formula = amount_based_on_formula
    if doc.meta.has_field("formula"):
        doc.formula = formula
    doc.insert(ignore_permissions=True)
    return doc.name


def _salary_structure_name(company: str) -> str:
    abbr = frappe.db.get_value("Company", company, "abbr") or company
    return f"{DEMO_SALARY_STRUCTURE_PREFIX} - {abbr}"


def _ensure_salary_structure(company: str, currency: str) -> str:
    name = _salary_structure_name(company)
    existing = frappe.db.exists("Salary Structure", name)
    if existing:
        doc = frappe.get_doc("Salary Structure", existing)
        if doc.docstatus == 2:
            frappe.throw(
                _("Demo Salary Structure {0} is cancelled. Amend or remove it first.").format(name)
            )
        if doc.docstatus == 0:
            _normalize_salary_structure(doc, company, currency)
            doc.save(ignore_permissions=True)
            doc.submit()
        return doc.name

    doc = frappe.new_doc("Salary Structure")
    doc.name = name
    _normalize_salary_structure(doc, company, currency)
    doc.insert(ignore_permissions=True)
    doc.submit()
    return doc.name


def _normalize_salary_structure(doc, company: str, currency: str):
    doc.company = company
    doc.currency = currency
    doc.is_active = "Yes"
    doc.payroll_frequency = "Monthly"
    doc.salary_slip_based_on_timesheet = 0

    # Keep this structure intentionally simple. The assignment Base is the
    # employee's monthly salary and is also what HR Procedures uses for daily wage.
    basic_row = None
    for row in doc.get("earnings") or []:
        if row.salary_component == DEMO_BASIC_COMPONENT:
            basic_row = row
            break
    if not basic_row:
        basic_row = doc.append("earnings", {})

    basic_row.salary_component = DEMO_BASIC_COMPONENT
    basic_row.amount_based_on_formula = 1
    basic_row.formula = "base"
    basic_row.amount = 0


def _assignment_from_date(employee: str):
    joining_date = getdate(frappe.db.get_value("Employee", employee, "date_of_joining"))
    first_checkin = frappe.db.get_value(
        "Employee Checkin",
        {"employee": employee},
        "time",
        order_by="time asc",
    )

    if first_checkin:
        candidate = add_days(getdate(first_checkin), -1)
    else:
        candidate = getdate(today())

    if joining_date and candidate < joining_date:
        return joining_date
    return candidate


def _ensure_salary_assignment(
    employee: str,
    company: str,
    salary_structure: str,
    from_date: date,
    base: float,
):
    # If a submitted assignment already covers the first demo payroll date,
    # keep it rather than creating an overlapping real payroll assignment.
    existing_submitted = frappe.db.get_value(
        "Salary Structure Assignment",
        {
            "employee": employee,
            "docstatus": 1,
            "from_date": ["<=", from_date],
        },
        "name",
        order_by="from_date desc",
    )
    if existing_submitted:
        return "existing", existing_submitted

    existing_draft = frappe.db.get_value(
        "Salary Structure Assignment",
        {
            "employee": employee,
            "docstatus": 0,
            "from_date": from_date,
        },
        "name",
    )
    if existing_draft:
        assignment = frappe.get_doc("Salary Structure Assignment", existing_draft)
        assignment.salary_structure = salary_structure
        assignment.company = company
        assignment.base = base
        assignment.variable = 0
        assignment.save(ignore_permissions=True)
        assignment.submit()
        return "updated_draft", assignment.name

    assignment = frappe.new_doc("Salary Structure Assignment")
    assignment.employee = employee
    assignment.salary_structure = salary_structure
    assignment.company = company
    assignment.from_date = from_date
    assignment.base = base
    assignment.variable = 0
    assignment.insert(ignore_permissions=True)
    assignment.submit()
    return "created", assignment.name


def _configure_hr_procedures_settings():
    settings = frappe.get_single("HR Procedures Settings")
    settings.daily_wage_source = "Salary Structure Assignment Base"
    settings.daily_wage_divisor = 30
    settings.standard_work_hours_per_day = 8
    settings.deduction_salary_component = DEMO_DEDUCTION_COMPONENT
    settings.save(ignore_permissions=True)
