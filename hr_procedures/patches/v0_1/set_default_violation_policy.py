import frappe
from frappe.utils import getdate, today


def execute():
    frappe.reload_doc("hr_procedures", "doctype", "hr_violation_policy")

    companies = frappe.get_all(
        "HR Violation Policy",
        pluck="company",
    )

    for company in sorted({company for company in companies if company}):
        existing_default = frappe.get_all(
            "HR Violation Policy",
            filters={"company": company, "is_default": 1},
            pluck="name",
            limit=1,
        )
        if existing_default:
            continue

        policies = frappe.get_all(
            "HR Violation Policy",
            filters={"company": company, "is_active": 1},
            fields=["name", "effective_from", "effective_to"],
            order_by="effective_from desc",
        )
        if not policies:
            continue

        current_date = getdate(today())
        selected = None
        for row in policies:
            start = getdate(row.effective_from) if row.effective_from else None
            end = getdate(row.effective_to) if row.effective_to else None
            if start and current_date < start:
                continue
            if end and current_date > end:
                continue
            selected = row
            break

        if selected is None:
            selected = policies[0]

        frappe.db.set_value(
            "HR Violation Policy",
            selected.name,
            "is_default",
            1,
            update_modified=False,
        )
