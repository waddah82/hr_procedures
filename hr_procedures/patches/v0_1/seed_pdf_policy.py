import frappe

from hr_procedures.data.source_policy import seed_source_policy


def execute():
    # Patches may run before the general schema sync. Reload the changed DocTypes
    # explicitly so Composite penalties and the absence-wage flag exist first.
    frappe.reload_doc("hr_procedures", "doctype", "hr_penalty_template")
    frappe.reload_doc("hr_procedures", "doctype", "hr_violation_type")
    frappe.reload_doc("hr_procedures", "doctype", "hr_violation_policy_row")
    frappe.reload_doc("hr_procedures", "doctype", "hr_violation_policy")
    frappe.reload_doc("hr_procedures", "doctype", "hr_procedures_settings")
    seed_source_policy(backfill_policies=True)
