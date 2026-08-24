import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class HRPenaltyTemplate(Document):
    def validate(self):
        if self.penalty_type in ("Salary Deduction", "Composite"):
            has_dynamic_deduction = bool(
                self.add_actual_late_minutes
                or self.add_actual_early_exit_minutes
                or self.add_actual_absence_days
            )
            if not self.deduction_basis and not has_dynamic_deduction:
                frappe.throw(_("Deduction Basis is required for salary deduction penalties."))
            if flt(self.deduction_value) < 0:
                frappe.throw(_("Deduction Value cannot be negative."))

        if self.penalty_type == "Composite" and not (
            self.warning_type
            or self.administrative_action_type
            or self.deduction_basis
            or self.add_actual_late_minutes
            or self.add_actual_early_exit_minutes
            or self.add_actual_absence_days
        ):
            frappe.throw(_("A composite penalty must contain at least one deduction or administrative action."))
