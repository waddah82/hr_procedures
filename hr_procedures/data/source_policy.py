import frappe

from hr_procedures.data.source_policy_data import PENALTIES, VIOLATIONS


CATEGORY_AR = {
    "Work Schedules": "مواعيد العمل",
    "Work Organization": "تنظيم العمل",
    "Employee Conduct": "سلوك العامل",
    "Other": "أخرى",
}

PENALTY_FIELDS = (
    "occurrence_1_penalty",
    "occurrence_2_penalty",
    "occurrence_3_penalty",
    "occurrence_4_penalty",
)
DISPLAY_FIELDS = (
    "occurrence_1_display",
    "occurrence_2_display",
    "occurrence_3_display",
    "occurrence_4_display",
)


def seed_source_policy(backfill_policies=True, force_source_defaults=False):
    """Seed the exact PDF source matrix.

    Internal codes remain stable for automation, while all user-facing values are Arabic.
    When force_source_defaults is true, the 50 supplied PDF rows are reset to the source
    penalties and source order. Custom violation types are preserved.
    """
    seed_penalties()
    seed_violations()
    if backfill_policies:
        backfill_existing_policies(force_source_defaults=force_source_defaults)


def seed_penalties():
    for code, values in PENALTIES.items():
        existing = frappe.db.exists("HR Penalty Template", {"penalty_code": code})
        if existing:
            doc = frappe.get_doc("HR Penalty Template", existing)
        else:
            doc = frappe.new_doc("HR Penalty Template")
            doc.penalty_code = code

        for key, value in values.items():
            if doc.meta.has_field(key):
                setattr(doc, key, value)
        doc.active = 1

        if doc.is_new():
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)


def seed_violations():
    for values in VIOLATIONS:
        code = values["violation_code"]
        existing = frappe.db.exists("HR Violation Type", {"violation_code": code})
        if existing:
            doc = frappe.get_doc("HR Violation Type", existing)
        else:
            doc = frappe.new_doc("HR Violation Type")
            doc.violation_code = code

        # Keep the Link title concise enough for Frappe's Data field (140 chars).
        # The exact PDF wording remains in `description` and in the policy grid display.
        mapped = dict(values)
        mapped["violation_name"] = values.get("violation_name") or values.get("violation_code")

        for key in (
            "violation_name",
            "category",
            "description",
            "detection_source",
            "detection_rule",
            "minimum_minutes",
            "maximum_minutes",
            "requires_hr_confirmation",
        ):
            if key in mapped and doc.meta.has_field(key):
                setattr(doc, key, mapped[key])

        doc.active = 1
        doc.repeat_counting_method = "Contractual Year"

        if doc.is_new():
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)


def _source_by_code(code):
    return next((row for row in VIOLATIONS if row["violation_code"] == code), None)


def get_default_penalty_names(violation_type):
    code = frappe.db.get_value("HR Violation Type", violation_type, "violation_code") or violation_type
    source = _source_by_code(code)
    if not source:
        return (None, None, None, None)

    names = []
    for penalty_code in source["penalties"]:
        if not penalty_code:
            names.append(None)
            continue
        name = frappe.db.get_value("HR Penalty Template", {"penalty_code": penalty_code}, "name")
        names.append(name)
    return tuple(names)


def get_penalty_display(penalty_name):
    if not penalty_name:
        return ""
    return frappe.db.get_value("HR Penalty Template", penalty_name, "penalty_name") or penalty_name


def get_violation_display(violation_type):
    if not violation_type:
        return ""
    values = frappe.db.get_value(
        "HR Violation Type",
        violation_type,
        ["violation_code", "violation_name", "category"],
        as_dict=True,
    )
    if not values:
        return violation_type

    source = _source_by_code(values.violation_code)
    if source:
        section = CATEGORY_AR.get(values.category, values.category or "")
        try:
            source_no = int(values.violation_code.split("-")[-1])
        except Exception:
            source_no = values.violation_code
        # Show the exact PDF text in the policy grid, without storing it in the
        # 140-character Link title field.
        source_text = source.get("description") or values.violation_name
        return f"{section} ({source_no}): {source_text}"

    return values.violation_name or violation_type


def populate_row_display(row):
    row.violation_display = get_violation_display(row.violation_type)
    for penalty_field, display_field in zip(PENALTY_FIELDS, DISPLAY_FIELDS):
        row.set(display_field, get_penalty_display(row.get(penalty_field)))


def build_default_policy_rows():
    """Build rows in the same order as the supplied PDF: WS, WO, then EC.

    The previous implementation sorted by internal code, which made EC-01 appear as
    grid row 1 and therefore did not line up with PDF row 1. This function intentionally
    follows VIOLATIONS source order and appends any custom types afterwards.
    """
    rows = []
    seen = set()

    # Source rows first, in exact PDF order.
    for source in VIOLATIONS:
        violation_type = frappe.db.get_value(
            "HR Violation Type", {"violation_code": source["violation_code"], "active": 1}, "name"
        )
        if not violation_type:
            continue
        penalties = get_default_penalty_names(violation_type)
        row = {
            "violation_type": violation_type,
            "occurrence_1_penalty": penalties[0],
            "occurrence_2_penalty": penalties[1],
            "occurrence_3_penalty": penalties[2],
            "occurrence_4_penalty": penalties[3],
            "is_source_violation": 1,
        }
        row["violation_display"] = get_violation_display(violation_type)
        for penalty_field, display_field in zip(PENALTY_FIELDS, DISPLAY_FIELDS):
            row[display_field] = get_penalty_display(row[penalty_field])
        rows.append(row)
        seen.add(violation_type)

    # Then append any user-created active violation types without disturbing source order.
    custom_types = frappe.get_all(
        "HR Violation Type",
        filters={"active": 1, "name": ["not in", list(seen) or [""]]},
        fields=["name", "violation_name"],
        order_by="violation_name asc",
    )
    for item in custom_types:
        row = {
            "violation_type": item.name,
            "occurrence_1_penalty": None,
            "occurrence_2_penalty": None,
            "occurrence_3_penalty": None,
            "occurrence_4_penalty": None,
            "is_source_violation": 0,
        }
        row["violation_display"] = get_violation_display(item.name)
        for display_field in DISPLAY_FIELDS:
            row[display_field] = ""
        rows.append(row)

    return rows


def backfill_policy_doc(doc, preserve_existing=True, force_source_defaults=False):
    defaults = {row["violation_type"]: row for row in build_default_policy_rows()}
    existing = {row.violation_type: row for row in doc.violations if row.violation_type}
    new_rows = []

    for violation_type, default in defaults.items():
        row = existing.get(violation_type)
        if not row:
            row = doc.append("violations", {"violation_type": violation_type})

        is_source = bool(default.get("is_source_violation"))
        for fieldname in PENALTY_FIELDS:
            if (force_source_defaults and is_source) or not preserve_existing or not row.get(fieldname):
                row.set(fieldname, default.get(fieldname))

        populate_row_display(row)
        new_rows.append(row)

    # Replacing the child table is intentional: it fixes the previous alphabetical order.
    doc.set("violations", new_rows)
    return len(new_rows)


def backfill_existing_policies(force_source_defaults=False):
    for policy_name in frappe.get_all("HR Violation Policy", pluck="name"):
        doc = frappe.get_doc("HR Violation Policy", policy_name)
        backfill_policy_doc(
            doc,
            preserve_existing=True,
            force_source_defaults=force_source_defaults,
        )
        doc.flags.ignore_permissions = True
        doc.save()
