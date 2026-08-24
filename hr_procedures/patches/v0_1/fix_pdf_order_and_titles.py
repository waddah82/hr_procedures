import frappe

from hr_procedures.data.source_policy import backfill_policy_doc, seed_source_policy


def execute():
    # Reload metadata first so readable grid fields and Link title behavior are available.
    frappe.reload_doc("hr_procedures", "doctype", "hr_penalty_template")
    frappe.reload_doc("hr_procedures", "doctype", "hr_violation_type")
    frappe.reload_doc("hr_procedures", "doctype", "hr_violation_policy_row")
    frappe.reload_doc("hr_procedures", "doctype", "hr_violation_policy")

    # Refresh the 50 PDF source violations and all source penalty templates.
    seed_source_policy(backfill_policies=False)

    # The previous release sorted by internal code (EC before WS), so reset source rows
    # to the exact PDF order and source penalties. Custom violation types are preserved.
    for policy_name in frappe.get_all("HR Violation Policy", pluck="name"):
        doc = frappe.get_doc("HR Violation Policy", policy_name)
        backfill_policy_doc(doc, preserve_existing=True, force_source_defaults=True)
        doc.flags.ignore_permissions = True
        doc.save()

    frappe.clear_cache()
