import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class HRViolationType(Document):
    def validate(self):
        if self.detection_source == "Manual":
            self.detection_rule = "Manual"
        if self.detection_rule in ("Late Entry", "Early Exit"):
            if flt(self.maximum_minutes) and flt(self.maximum_minutes) < flt(self.minimum_minutes):
                frappe.throw(_("Maximum Minutes cannot be less than Minimum Minutes."))
