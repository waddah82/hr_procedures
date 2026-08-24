import frappe

from hr_procedures.data.source_policy import backfill_policy_doc, seed_source_policy


def execute():
    # Ensure current metadata is loaded, then reseed with short Link titles while
    # retaining the exact PDF wording in Description / policy display fields.
    frappe.reload_doc("hr_procedures", "doctype", "hr_violation_type")
    frappe.reload_doc("hr_procedures", "doctype", "hr_penalty_template")
    frappe.reload_doc("hr_procedures", "doctype", "hr_violation_policy_row")
    frappe.reload_doc("hr_procedures", "doctype", "hr_violation_policy")

    seed_source_policy(backfill_policies=False)

    for policy_name in frappe.get_all("HR Violation Policy", pluck="name"):
        doc = frappe.get_doc("HR Violation Policy", policy_name)
        backfill_policy_doc(doc, preserve_existing=True, force_source_defaults=True)
        doc.flags.ignore_permissions = True
        doc.save()

    frappe.clear_cache()
