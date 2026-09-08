import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime

from hr_procedures.utils.penalties import (
    calculate_occurrence,
    calculate_penalty_amount,
    execute_penalty,
    get_active_policy,
    get_policy_penalty,
    reverse_execution,
    validate_override_permission,
)


class EmployeeViolation(Document):
    def validate(self):
        self._set_violation_defaults()
        self._validate_duplicate_automatic_source()
        # Draft documents must remain savable even when payroll wage data is not
        # available yet. Wage data becomes mandatory only when a financial penalty
        # is actually going to be executed on Submit.
        self._recalculate_deserved_penalty(strict=False)
        self._validate_penalty_decision()
        self._set_final_penalty(strict=False)

    def before_submit(self):
        # Preserve the deserved penalty even when wage data is missing. Only the
        # final penalty selected for execution is calculated strictly. This allows
        # Waive Penalty and non-financial alternative penalties to be submitted
        # without requiring a Salary Structure Assignment.
        self._recalculate_deserved_penalty(strict=False)
        if not self.violation_policy:
            frappe.throw(
                f"No active HR Violation Policy was found for company {self.company} on {self.violation_date}."
            )
        self._validate_penalty_decision()
        self._set_final_penalty(strict=True)
        if self.penalty_decision in ("Waive Penalty", "Apply Alternative Penalty"):
            self.decision_by = frappe.session.user
            self.decision_date = now_datetime()

    def on_submit(self):
        execute_penalty(self)

    def on_cancel(self):
        reverse_execution(self)

    def _set_violation_defaults(self):
        if self.employee:
            self.user_id = frappe.db.get_value("Employee", self.employee, "user_id")
        if self.violation_type:
            vtype = frappe.get_cached_doc("HR Violation Type", self.violation_type)
            self.category = vtype.category
            self.requires_hr_confirmation = vtype.requires_hr_confirmation
        if not self.violation_date:
            self.violation_date = getdate()

    def _validate_duplicate_automatic_source(self):
        if self.source != "Automatic" or not self.reference_doctype or not self.reference_name:
            return
        existing = frappe.get_all(
            "Employee Violation",
            filters={
                "name": ["!=", self.name or ""],
                "reference_doctype": self.reference_doctype,
                "reference_name": self.reference_name,
                "violation_type": self.violation_type,
                "docstatus": ["<", 2],
            },
            pluck="name",
            limit=1,
        )
        if existing:
            frappe.throw(_("A violation already exists for this source document and violation type: {0}").format(existing[0]))

    def _recalculate_deserved_penalty(self, strict=False):
        if not (self.employee and self.company and self.violation_date and self.violation_type):
            return

        self.violation_policy = get_active_policy(self.company, self.violation_date)
        if not self.violation_policy:
            self._clear_policy_values()
            return

        self.occurrence_no = calculate_occurrence(
            self.employee, self.violation_type, self.violation_date, self.name
        )
        self.penalty_tier = min(max(cint(self.occurrence_no), 1), 4)
        self.deserved_penalty = get_policy_penalty(
            self.violation_policy, self.violation_type, self.occurrence_no
        )
        if not self.deserved_penalty:
            frappe.throw(_("No penalty is configured for occurrence {0} of violation {1} in policy {2}.").format(
                self.penalty_tier, self.violation_type, self.violation_policy
            ))

        amount, details = calculate_penalty_amount(
            self.deserved_penalty,
            self.employee,
            self.violation_date,
            {
                "late_minutes": self.late_minutes,
                "early_exit_minutes": self.early_exit_minutes,
                "absence_days": self.absence_days,
            },
            strict=strict,
        )
        self.deserved_deduction_amount = amount
        self.deserved_penalty_details = details

    def _clear_policy_values(self):
        self.violation_policy = None
        self.occurrence_no = None
        self.penalty_tier = None
        self.deserved_penalty = None
        self.deserved_penalty_details = None
        self.deserved_deduction_amount = 0
        self.final_penalty = None
        self.final_deduction_amount = 0

    def _validate_penalty_decision(self):
        settings = frappe.get_single("HR Procedures Settings")
        decision = self.penalty_decision or "Execute Deserved Penalty"
        validate_override_permission(decision, settings)

        if decision == "Apply Alternative Penalty" and not self.alternative_penalty:
            frappe.throw(_("Alternative Penalty is required when applying an alternative penalty."))
        if decision == "Waive Penalty" and settings.require_reason_for_waiver and not self.decision_reason:
            frappe.throw(_("Decision Reason is required when waiving a penalty."))
        if decision == "Apply Alternative Penalty" and settings.require_reason_for_alternative_penalty and not self.decision_reason:
            frappe.throw(_("Decision Reason is required when applying an alternative penalty."))

    def _set_final_penalty(self, strict=False):
        if self.penalty_decision == "Waive Penalty":
            self.final_penalty = None
            self.final_deduction_amount = 0
            return

        self.final_penalty = (
            self.alternative_penalty
            if self.penalty_decision == "Apply Alternative Penalty"
            else self.deserved_penalty
        )
        amount, _ = calculate_penalty_amount(
            self.final_penalty,
            self.employee,
            self.violation_date,
            {
                "late_minutes": self.late_minutes,
                "early_exit_minutes": self.early_exit_minutes,
                "absence_days": self.absence_days,
            },
            strict=strict,
        )
        self.final_deduction_amount = amount


@frappe.whitelist()
def get_violation_preview(employee, violation_type, violation_date, company=None, late_minutes=0, early_exit_minutes=0, absence_days=0, penalty_decision="Execute Deserved Penalty", alternative_penalty=None):
    if not company:
        company = frappe.db.get_value("Employee", employee, "company")
    policy = get_active_policy(company, violation_date)
    if not policy:
        return {
            "violation_policy": None,
            "occurrence_no": None,
            "penalty_tier": None,
            "deserved_penalty": None,
            "deserved_penalty_details": None,
            "deserved_deduction_amount": 0,
            "final_penalty": None,
            "final_deduction_amount": 0,
        }
    occurrence = calculate_occurrence(employee, violation_type, violation_date)
    deserved = get_policy_penalty(policy, violation_type, occurrence)
    if not deserved:
        frappe.throw(_("No penalty is configured for this violation occurrence."))
    deserved_amount, details = calculate_penalty_amount(deserved, employee, violation_date, {
        "late_minutes": late_minutes,
        "early_exit_minutes": early_exit_minutes,
        "absence_days": absence_days,
    }, strict=False)
    if penalty_decision == "Waive Penalty":
        final = None
        final_amount = 0
    else:
        final = alternative_penalty if penalty_decision == "Apply Alternative Penalty" else deserved
        final_amount, _ = calculate_penalty_amount(final, employee, violation_date, {
            "late_minutes": late_minutes,
            "early_exit_minutes": early_exit_minutes,
            "absence_days": absence_days,
        }, strict=False)
    return {
        "violation_policy": policy,
        "occurrence_no": occurrence,
        "penalty_tier": min(max(cint(occurrence), 1), 4),
        "deserved_penalty": deserved,
        "deserved_penalty_details": details,
        "deserved_deduction_amount": deserved_amount,
        "final_penalty": final,
        "final_deduction_amount": final_amount,
    }
