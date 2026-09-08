import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from hr_procedures.data.source_policy import (
    backfill_policy_doc,
    build_default_policy_rows,
    populate_row_display,
    seed_source_policy,
)


class HRViolationPolicy(Document):
    def validate(self):
        self._validate_dates()
        self._ensure_default_policy()
        self._validate_default_policy()
        self._validate_active_overlap()
        self.sync_rows()
        self._refresh_display_values()

    def before_save(self):
        self._unset_other_default_policies()

    def _ensure_default_policy(self):
        if not (self.company and self.is_active) or self.is_default:
            return

        existing_default = frappe.get_all(
            "HR Violation Policy",
            filters={
                "company": self.company,
                "is_default": 1,
                "name": ["!=", self.name or ""],
            },
            fields=["name"],
            limit=1,
        )
        if not existing_default:
            self.is_default = 1

    def _validate_default_policy(self):
        if self.is_default and not self.is_active:
            frappe.throw(_("Default Policy must be active."))

    def _unset_other_default_policies(self):
        if not (self.is_default and self.company):
            return

        others = frappe.get_all(
            "HR Violation Policy",
            filters={
                "company": self.company,
                "is_default": 1,
                "name": ["!=", self.name or ""],
            },
            fields=["name"],
        )
        for row in others:
            frappe.db.set_value(
                "HR Violation Policy",
                row.name,
                "is_default",
                0,
                update_modified=False,
            )

    def _validate_dates(self):
        if self.effective_to and getdate(self.effective_to) < getdate(self.effective_from):
            frappe.throw(_("Effective To cannot be before Effective From."))

    def _validate_active_overlap(self):
        if not self.is_active:
            return
        others = frappe.get_all(
            "HR Violation Policy",
            filters={"company": self.company, "is_active": 1, "name": ["!=", self.name or ""]},
            fields=["name", "effective_from", "effective_to"],
        )
        start = getdate(self.effective_from)
        end = getdate(self.effective_to) if self.effective_to else None
        for row in others:
            other_start = getdate(row.effective_from)
            other_end = getdate(row.effective_to) if row.effective_to else None
            if (end is None or other_start <= end) and (other_end is None or start <= other_end):
                frappe.throw(_("An active violation policy already overlaps this date range: {0}").format(row.name))

    def sync_rows(self):
        # System-controlled rows; manager penalty overrides are preserved on normal save.
        backfill_policy_doc(self, preserve_existing=True, force_source_defaults=False)

    def _refresh_display_values(self):
        for row in self.violations:
            populate_row_display(row)


@frappe.whitelist()
def sync_violation_types(policy_name):
    doc = frappe.get_doc("HR Violation Policy", policy_name)
    doc.check_permission("write")
    doc.sync_rows()
    doc._refresh_display_values()
    doc.save()
    return len(doc.violations)


@frappe.whitelist()
def reset_source_pdf_penalties(policy_name):
    """Restore the supplied PDF's 50 source rows, exact source order and penalties."""
    doc = frappe.get_doc("HR Violation Policy", policy_name)
    doc.check_permission("write")
    seed_source_policy(backfill_policies=False)
    backfill_policy_doc(doc, preserve_existing=True, force_source_defaults=True)
    doc._refresh_display_values()
    doc.save()
    return len(doc.violations)


@frappe.whitelist()
def get_default_policy_rows():
    # New policies open already populated and in PDF order.
    return build_default_policy_rows()
