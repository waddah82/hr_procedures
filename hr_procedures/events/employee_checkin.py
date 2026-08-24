from __future__ import annotations

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, get_time, getdate, now_datetime, time_diff_in_hours


DEFAULT_SCAN_DAYS = 7
DEFAULT_SCAN_LIMIT = 5000


def after_insert(doc, method=None):
    """Evaluate a newly-created Employee Checkin without blocking check-in creation on HR errors."""
    if not _automatic_detection_enabled():
        return

    try:
        _process_checkin(doc, current_time=now_datetime())
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            _("Employee Checkin automatic detection failed for {0}").format(doc.name),
        )


def on_trash(doc, method=None):
    """Remove only draft automatic violations linked directly to the deleted check-in."""
    draft_violations = frappe.get_all(
        "Employee Violation",
        filters={
            "reference_doctype": "Employee Checkin",
            "reference_name": doc.name,
            "source": "Automatic",
            "docstatus": 0,
        },
        pluck="name",
    )
    for violation_name in draft_violations:
        frappe.delete_doc("Employee Violation", violation_name, ignore_permissions=True)


def scan_pending_employee_checkins():
    """Scheduler entry point: scan recent unprocessed check-ins every hour."""
    if not _automatic_detection_enabled():
        return

    return scan_employee_checkins(
        from_datetime=add_days(now_datetime(), -DEFAULT_SCAN_DAYS),
        to_datetime=now_datetime(),
        limit=DEFAULT_SCAN_LIMIT,
        full_scan=0,
    )


@frappe.whitelist()
def scan_employee_checkins(
    from_datetime=None,
    to_datetime=None,
    employee=None,
    limit=DEFAULT_SCAN_LIMIT,
    full_scan=0,
):
    """Scan Employee Checkin records and create missing automatic violations.

    Existing check-ins already referenced by a non-cancelled automatic Employee Violation
    are filtered out before evaluation. This makes the function safe to run repeatedly.

    full_scan=1 scans from the first Employee Checkin. Otherwise, if no from_datetime is
    supplied, the most recent DEFAULT_SCAN_DAYS are scanned.
    """
    if not _automatic_detection_enabled():
        return {
            "enabled": 0,
            "message": _("Automatic violation detection is disabled in HR Procedures Settings."),
        }

    limit = max(cint(limit), 1)
    current_time = get_datetime(to_datetime) if to_datetime else now_datetime()

    filters = {"skip_auto_attendance": 0}
    if employee:
        filters["employee"] = employee

    if not cint(full_scan):
        scan_from = get_datetime(from_datetime) if from_datetime else add_days(current_time, -DEFAULT_SCAN_DAYS)
        filters["time"] = ["between", [scan_from, current_time]]
    elif from_datetime:
        filters["time"] = ["between", [get_datetime(from_datetime), current_time]]
    elif to_datetime:
        filters["time"] = ["<=", current_time]

    fields = _checkin_query_fields()
    checkins = frappe.get_all(
        "Employee Checkin",
        filters=filters,
        fields=fields,
        order_by="time asc, creation asc",
        limit_page_length=limit,
    )

    names = [row.name for row in checkins]
    already_with_violation = _get_checkins_with_existing_violation(names)

    result = {
        "enabled": 1,
        "fetched": len(checkins),
        "filtered_existing_violation": 0,
        "evaluated": 0,
        "created": 0,
        "late_created": 0,
        "early_exit_created": 0,
        "no_violation": 0,
        "waiting_for_shift_end": 0,
        "not_first_or_last": 0,
        "unresolved_shift": 0,
        "errors": 0,
        "error_samples": [],
    }

    for row in checkins:
        if row.name in already_with_violation:
            result["filtered_existing_violation"] += 1
            continue

        try:
            outcome = _process_checkin(row, current_time=current_time)
        except Exception as exc:
            result["errors"] += 1
            if len(result["error_samples"]) < 10:
                result["error_samples"].append(
                    {
                        "checkin": row.name,
                        "employee": row.employee,
                        "time": str(row.time),
                        "error_type": exc.__class__.__name__,
                        "error": str(exc),
                    }
                )
            frappe.log_error(
                frappe.get_traceback(),
                _("Employee Checkin automatic detection failed for {0}").format(row.name),
            )
            continue

        result["evaluated"] += 1
        status = outcome.get("status") if outcome else "no_violation"

        if status == "created":
            result["created"] += 1
            if outcome.get("rule") == "Late Entry":
                result["late_created"] += 1
            elif outcome.get("rule") == "Early Exit":
                result["early_exit_created"] += 1
        elif status in result:
            result[status] += 1
        else:
            result["no_violation"] += 1

    result["message"] = _("Employee Checkin scan completed.")
    return result


def _process_checkin(checkin, current_time=None):
    checkin = _as_checkin_dict(checkin)
    if not checkin.employee or not checkin.time:
        return {"status": "no_violation"}

    if _has_existing_checkin_violation(checkin.name):
        return {"status": "filtered_existing_violation"}

    context = _resolve_shift_context(checkin)
    if not context:
        return {"status": "unresolved_shift"}

    logs = _get_shift_logs(checkin, context)
    if not logs:
        return {"status": "no_violation"}

    explicit_log_type = (checkin.log_type or "").upper()
    first_in = _first_in_log(logs)
    last_out = _last_out_log(logs)

    # An explicit IN is evaluated immediately. For devices without log_type, the first
    # log in the shift is treated as IN.
    is_in_candidate = explicit_log_type == "IN" or (not explicit_log_type and first_in and first_in.name == checkin.name)
    if is_in_candidate:
        if not first_in or first_in.name != checkin.name:
            return {"status": "not_first_or_last"}
        return _evaluate_late_entry(checkin, first_in, context)

    # Early-exit evaluation must wait until the shift is over. A worker may have an OUT
    # during a break and then return, so only the last OUT is eligible after shift end.
    is_out_candidate = explicit_log_type == "OUT" or (not explicit_log_type and last_out and last_out.name == checkin.name)
    if is_out_candidate:
        current_time = get_datetime(current_time or now_datetime())
        if current_time < context["shift_end"]:
            return {"status": "waiting_for_shift_end"}
        if not last_out or last_out.name != checkin.name:
            return {"status": "not_first_or_last"}
        return _evaluate_early_exit(checkin, last_out, context)

    return {"status": "no_violation"}


def _evaluate_late_entry(checkin, first_in, context):
    raw_late = max(time_diff_in_hours(get_datetime(first_in.time), context["shift_start"]) * 60, 0)
    if raw_late <= context["late_grace"]:
        return {"status": "no_violation", "minutes": round(raw_late, 2)}

    minutes = round(raw_late, 2)
    violation = _create_for_rule(
        checkin=checkin,
        source_checkin=first_in,
        context=context,
        detection_rule="Late Entry",
        value=minutes,
    )
    if not violation:
        return {"status": "no_violation", "minutes": minutes}
    return {"status": "created", "rule": "Late Entry", "minutes": minutes, "violation": violation}


def _evaluate_early_exit(checkin, last_out, context):
    raw_early = max(time_diff_in_hours(context["shift_end"], get_datetime(last_out.time)) * 60, 0)
    if raw_early <= context["early_grace"]:
        return {"status": "no_violation", "minutes": round(raw_early, 2)}

    minutes = round(raw_early, 2)
    violation = _create_for_rule(
        checkin=checkin,
        source_checkin=last_out,
        context=context,
        detection_rule="Early Exit",
        value=minutes,
    )
    if not violation:
        return {"status": "no_violation", "minutes": minutes}
    return {"status": "created", "rule": "Early Exit", "minutes": minutes, "violation": violation}


def _create_for_rule(checkin, source_checkin, context, detection_rule, value):
    match = _find_violation_type(detection_rule, value)
    if not match:
        return None

    # This also protects migrations from the old Attendance-based detector. If an
    # automatic violation of the same type already exists for the employee and shift day,
    # do not create another one even if its old reference was Attendance.
    duplicate = frappe.db.exists(
        "Employee Violation",
        {
            "employee": checkin.employee,
            "violation_date": getdate(context["shift_start"]),
            "violation_type": match.name,
            "source": "Automatic",
            "docstatus": ["<", 2],
        },
    )
    if duplicate:
        return None

    employee_values = frappe.db.get_value("Employee", checkin.employee, ["company"], as_dict=True) or {}
    company = employee_values.get("company")
    if not company:
        return None

    violation = frappe.new_doc("Employee Violation")
    violation.employee = checkin.employee
    violation.company = company
    violation.violation_date = getdate(context["shift_start"])
    violation.violation_type = match.name
    violation.source = "Automatic"
    violation.reference_doctype = "Employee Checkin"
    violation.reference_name = source_checkin.name
    violation.requires_hr_confirmation = match.requires_hr_confirmation

    if detection_rule == "Late Entry":
        violation.late_minutes = value
    elif detection_rule == "Early Exit":
        violation.early_exit_minutes = value

    violation.flags.ignore_permissions = True
    violation.flags.hr_procedures_detection_only = True
    violation.insert()
    return violation.name


def _find_violation_type(detection_rule, value):
    candidates = frappe.get_all(
        "HR Violation Type",
        filters={
            "active": 1,
            "detection_source": "Employee Checkin",
            "detection_rule": detection_rule,
        },
        fields=["name", "minimum_minutes", "maximum_minutes", "requires_hr_confirmation"],
        order_by="minimum_minutes desc, modified desc",
    )

    for item in candidates:
        minimum = flt(item.minimum_minutes)
        maximum = flt(item.maximum_minutes)
        if value >= minimum and (not maximum or value <= maximum):
            return item
    return None


def _resolve_shift_context(checkin):
    """Resolve the scheduled shift boundaries and the valid check-in window.

    Frappe HR stores two different concepts on Employee Checkin:
    - shift_start / shift_end: scheduled shift start and end.
    - shift_actual_start / shift_actual_end: widened window used to accept check-ins
      before/after the shift.

    Violation minutes must always be calculated from the scheduled boundaries, never
    from the widened actual window.
    """
    shift_name = checkin.get("shift")
    shift_start = get_datetime(checkin.get("shift_start")) if checkin.get("shift_start") else None
    shift_end = get_datetime(checkin.get("shift_end")) if checkin.get("shift_end") else None
    window_start = (
        get_datetime(checkin.get("shift_actual_start"))
        if checkin.get("shift_actual_start")
        else None
    )
    window_end = (
        get_datetime(checkin.get("shift_actual_end"))
        if checkin.get("shift_actual_end")
        else None
    )

    # Use HRMS's own resolver when the check-in does not already carry complete shift
    # boundaries. This keeps Shift Assignment/default-shift behavior identical to HRMS.
    if not (shift_name and shift_start and shift_end and window_start and window_end):
        try:
            from hrms.hr.doctype.shift_assignment.shift_assignment import (
                get_actual_start_end_datetime_of_shift,
            )

            details = get_actual_start_end_datetime_of_shift(
                checkin.employee,
                get_datetime(checkin.time),
                consider_default_shift=True,
            )
            if details:
                shift_type = details.get("shift_type")
                resolved_name = getattr(shift_type, "name", None)
                if not resolved_name and isinstance(shift_type, dict):
                    resolved_name = shift_type.get("name")
                shift_name = shift_name or resolved_name
                shift_start = shift_start or (
                    get_datetime(details.get("start_datetime"))
                    if details.get("start_datetime")
                    else None
                )
                shift_end = shift_end or (
                    get_datetime(details.get("end_datetime"))
                    if details.get("end_datetime")
                    else None
                )
                window_start = window_start or (
                    get_datetime(details.get("actual_start"))
                    if details.get("actual_start")
                    else None
                )
                window_end = window_end or (
                    get_datetime(details.get("actual_end"))
                    if details.get("actual_end")
                    else None
                )
        except Exception:
            # The check-in's own shift fields/default shift remain valid fallbacks.
            pass

    if not shift_name:
        shift_name = frappe.db.get_value("Employee", checkin.employee, "default_shift")

    if not shift_name:
        return None

    shift_doc = frappe.get_cached_doc("Shift Type", shift_name)

    if not (shift_start and shift_end):
        shift_start, shift_end = _shift_datetimes_from_clock(get_datetime(checkin.time), shift_doc)

    begin_before = flt(getattr(shift_doc, "begin_check_in_before_shift_start_time", 0))
    allow_after = flt(getattr(shift_doc, "allow_check_out_after_shift_end_time", 0))

    if not window_start:
        window_start = get_datetime(shift_start) - timedelta(minutes=begin_before)
    if not window_end:
        window_end = get_datetime(shift_end) + timedelta(minutes=allow_after)

    late_grace = 0
    if cint(getattr(shift_doc, "enable_late_entry_marking", 0)):
        late_grace = flt(getattr(shift_doc, "late_entry_grace_period", 0))

    early_grace = 0
    if cint(getattr(shift_doc, "enable_early_exit_marking", 0)):
        early_grace = flt(getattr(shift_doc, "early_exit_grace_period", 0))

    return frappe._dict(
        shift_name=shift_name,
        shift_start=get_datetime(shift_start),
        shift_end=get_datetime(shift_end),
        checkin_window_start=get_datetime(window_start),
        checkin_window_end=get_datetime(window_end),
        late_grace=late_grace,
        early_grace=early_grace,
    )


def _shift_datetimes_from_clock(checkin_time, shift_doc):
    checkin_time = get_datetime(checkin_time)
    base_date = getdate(checkin_time)
    start_clock = _clock_as_time(shift_doc.start_time)
    end_clock = _clock_as_time(shift_doc.end_time)

    shift_start = datetime.combine(base_date, start_clock)
    shift_end = datetime.combine(base_date, end_clock)

    if end_clock <= start_clock:
        # For an overnight shift, a check-in after midnight and before the shift-end clock
        # belongs to the shift that started on the previous calendar day.
        if checkin_time.time() <= end_clock:
            shift_start -= timedelta(days=1)
        else:
            shift_end += timedelta(days=1)

        if shift_end <= shift_start:
            shift_end = shift_start + _shift_duration(start_clock, end_clock)

    return shift_start, shift_end


def _shift_duration(start_clock, end_clock):
    anchor = datetime(2000, 1, 1)
    start_dt = datetime.combine(anchor.date(), start_clock)
    end_dt = datetime.combine(anchor.date(), end_clock)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return end_dt - start_dt


def _clock_as_time(value):
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds()) % 86400
        return (datetime.min + timedelta(seconds=seconds)).time()
    if isinstance(value, time):
        return value
    return get_time(value)


def _get_shift_logs(checkin, context):
    filters = {
        "employee": checkin.employee,
        "skip_auto_attendance": 0,
        "time": ["between", [context.checkin_window_start, context.checkin_window_end]],
    }

    meta = frappe.get_meta("Employee Checkin")
    if meta.has_field("shift_actual_start") and checkin.get("shift_actual_start"):
        filters["shift_actual_start"] = checkin.get("shift_actual_start")
    elif meta.has_field("shift") and context.shift_name:
        filters["shift"] = context.shift_name

    return frappe.get_all(
        "Employee Checkin",
        filters=filters,
        fields=_checkin_query_fields(),
        order_by="time asc, creation asc",
        limit_page_length=500,
    )


def _first_in_log(logs):
    explicit = [row for row in logs if (row.get("log_type") or "").upper() == "IN"]
    return explicit[0] if explicit else logs[0]


def _last_out_log(logs):
    explicit = [row for row in logs if (row.get("log_type") or "").upper() == "OUT"]
    if explicit:
        return explicit[-1]
    return logs[-1] if len(logs) > 1 else None


def _get_checkins_with_existing_violation(names):
    if not names:
        return set()
    rows = frappe.get_all(
        "Employee Violation",
        filters={
            "reference_doctype": "Employee Checkin",
            "reference_name": ["in", names],
            "source": "Automatic",
            "docstatus": ["<", 2],
        },
        pluck="reference_name",
    )
    return set(rows)


def _has_existing_checkin_violation(checkin_name):
    if not checkin_name:
        return False
    return bool(
        frappe.db.exists(
            "Employee Violation",
            {
                "reference_doctype": "Employee Checkin",
                "reference_name": checkin_name,
                "source": "Automatic",
                "docstatus": ["<", 2],
            },
        )
    )


def _checkin_query_fields():
    meta = frappe.get_meta("Employee Checkin")
    wanted = [
        "name",
        "employee",
        "time",
        "log_type",
        "shift",
        "shift_start",
        "shift_end",
        "shift_actual_start",
        "shift_actual_end",
        "skip_auto_attendance",
        "creation",
    ]
    standard = {"name", "creation"}
    return [field for field in wanted if field in standard or meta.has_field(field)]


def _as_checkin_dict(checkin):
    if isinstance(checkin, frappe._dict):
        return checkin
    if isinstance(checkin, dict):
        return frappe._dict(checkin)

    values = {"name": checkin.name}
    for fieldname in _checkin_query_fields():
        if fieldname == "name":
            continue
        values[fieldname] = getattr(checkin, fieldname, None)
    return frappe._dict(values)


def _automatic_detection_enabled():
    try:
        return bool(cint(frappe.get_single_value("HR Procedures Settings", "enable_automatic_detection")))
    except Exception:
        return False
