import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class HRAdministrativeAction(Document):
    def validate(self):
        if self.status == "Executed" and not self.executed_on:
            self.executed_by = frappe.session.user
            self.executed_on = now_datetime()
        if self.status == "Cancelled" and self.executed_on:
            frappe.throw(_("An executed administrative action cannot be cancelled directly."))
