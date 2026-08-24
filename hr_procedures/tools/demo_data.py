from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, today


DEMO_DEVICE_PREFIX = "HRP-DEMO-"
MORNING_SHIFT = "HRP Demo Morning 08-16"
EVENING_SHIFT = "HRP Demo Evening 14-22"


@dataclass(frozen=True)
class ShiftSpec:
    name: str
    start: time
    end: time


SHIFTS = {
    "morning": ShiftSpec(MORNING_SHIFT, time(8, 0), time(16, 0)),
    "evening": ShiftSpec(EVENING_SHIFT, time(14, 0), time(22, 0)),
}


EMPLOYEES = [
    {
        "key": "001",
        "first_name": "أحمد",
        "middle_name": "محمد",
        "last_name": "تجريبي",
        "shift": "morning",
        "late": [0, 10, 20, 40, 75, 0, 12, 25],
        "early": [0, 0, 0, 0, 0, 0, 0, 0],
        "absent": set(),
    },
    {
        "key": "002",
        "first_name": "سارة",
        "middle_name": "علي",
        "last_name": "تجريبية",
        "shift": "morning",
        "late": [0, 0, 0, 0, 0, 0, 0, 0],
        "early": [0, 10, 20, 0, 30, 0, 15, 0],
        "absent": set(),
    },
    {
        "key": "003",
        "first_name": "علي",
        "middle_name": "حسن",
        "last_name": "تجريبي",
        "shift": "morning",
        "late": [5, 0, 35, 0, 65, 0, 18, 0],
        "early": [0, 20, 0, 10, 0, 0, 0, 25],
        "absent": set(),
    },
    {
        "key": "004",
        "first_name": "منى",
        "middle_name": "عبدالله",
        "last_name": "تجريبية",
        "shift": "evening",
        "late": [0, 15, 30, 0, 50, 0, 80, 0],
        "early": [0, 0, 0, 20, 0, 10, 0, 0],
        "absent": set(),
    },
    {
        "key": "005",
        "first_name": "خالد",
        "middle_name": "صالح",
        "last_name": "تجريبي",
        "shift": "evening",
        "late": [0, 0, 0, 0, 0, 0, 0, 0],
        "early": [0, 0, 0, 0, 0, 0, 0, 0],
        "absent": {2, 5},
    },
    {
        "key": "006",
        "first_name": "رانيا",
        "middle_name": "أحمد",
        "last_name": "تجريبية",
        "shift": "morning",
        "late": [0, 22, 0, 45, 0, 70, 0, 14],
        "early": [0, 0, 15, 0, 0, 0, 20, 0],
        "absent": {3},
    },
]


def seed_demo_data(company: str | None = None, start_date: str | None = None, days: int = 8, trigger_violations: int = 0):
    """Create deterministic HR demo data for testing shifts, check-ins and attendance.

    By default the function temporarily suppresses HR Procedures automatic violation detection
    while Attendance is created. Pass trigger_violations=1 only after configuring an active
    violation policy and the payroll wage source required for penalty calculation.

    Example:
        bench --site SITE execute hr_procedures.tools.demo_data.seed_demo_data

    Optional:
        bench --site SITE execute hr_procedures.tools.demo_data.seed_demo_data \
          --kwargs '{"company":"My Company","start_date":"2026-08-01","days":8}'
    """
    company = company or _get_company()
    days = max(cint(days), 1)
    dates = _demo_dates(start_date, days)

    _ensure_shifts()
    employees = _ensure_employees(company, dates[0])
    assignments_created = _ensure_shift_assignments(employees, dates)

    created = {
        "company": company,
        "dates": [str(d) for d in dates],
        "employees": [],
        "shift_assignments_created": assignments_created,
        "checkins_created": 0,
        "attendance_created": 0,
        "attendance_skipped": 0,
    }

    settings = frappe.get_single("HR Procedures Settings")
    original_detection = cint(settings.enable_automatic_detection)
    if not cint(trigger_violations) and original_detection:
        settings.db_set("enable_automatic_detection", 0, update_modified=False)

    try:
        for spec in EMPLOYEES:
            employee = employees[spec["key"]]
            created["employees"].append(employee)
            shift_spec = SHIFTS[spec["shift"]]

            for index, attendance_date in enumerate(dates):
                if _attendance_exists(employee, attendance_date, shift_spec.name):
                    created["attendance_skipped"] += 1
                    continue

                if index in spec["absent"]:
                    _create_absent_attendance(employee, attendance_date, shift_spec.name)
                    created["attendance_created"] += 1
                    continue

                late_minutes = _value_for_index(spec["late"], index)
                early_minutes = _value_for_index(spec["early"], index)
                in_time, out_time = _attendance_times(
                    attendance_date,
                    shift_spec,
                    late_minutes=late_minutes,
                    early_minutes=early_minutes,
                )

                logs, new_logs = _ensure_checkins(employee, in_time, out_time)
                created["checkins_created"] += new_logs
                _create_present_attendance(
                    employee=employee,
                    attendance_date=attendance_date,
                    shift_name=shift_spec.name,
                    logs=logs,
                    in_time=in_time,
                    out_time=out_time,
                    late_minutes=late_minutes,
                    early_minutes=early_minutes,
                )
                created["attendance_created"] += 1
    finally:
        if not cint(trigger_violations) and original_detection:
            settings.db_set("enable_automatic_detection", original_detection, update_modified=False)

    frappe.db.commit()
    created["message"] = _(
        "HR Procedures demo employees, shift assignments, check-ins and attendance were created successfully."
    )
    return created


def get_demo_summary():
    employees = frappe.get_all(
        "Employee",
        filters={"attendance_device_id": ["like", f"{DEMO_DEVICE_PREFIX}%"]},
        fields=["name", "employee_name", "company", "attendance_device_id"],
        order_by="attendance_device_id asc",
    )
    employee_names = [row.name for row in employees]
    return {
        "employees": employees,
        "employee_count": len(employees),
        "checkin_count": frappe.db.count("Employee Checkin", {"employee": ["in", employee_names]}) if employee_names else 0,
        "attendance_count": frappe.db.count("Attendance", {"employee": ["in", employee_names], "docstatus": ["<", 2]}) if employee_names else 0,
        "shift_assignment_count": frappe.db.count("Shift Assignment", {"employee": ["in", employee_names], "docstatus": ["<", 2]}) if employee_names else 0,
    }


def _get_company() -> str:
    companies = frappe.get_all("Company", pluck="name", order_by="creation asc", limit=1)
    if not companies:
        frappe.throw(_("Create a Company before generating HR Procedures demo data."))
    return companies[0]


def _demo_dates(start_date: str | None, days: int) -> list[date]:
    if start_date:
        current = getdate(start_date)
    else:
        current = getdate(add_days(today(), -(days + 4)))

    dates = []
    while len(dates) < days:
        # Yemen commonly uses Friday as the weekly off. We skip it only for
        # generating readable demo data; no Holiday List is changed.
        if current.weekday() != 4:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def _ensure_shifts():
    for spec in SHIFTS.values():
        if frappe.db.exists("Shift Type", spec.name):
            continue

        shift = frappe.get_doc(
            {
                "doctype": "Shift Type",
                "name": spec.name,
                "start_time": spec.start.strftime("%H:%M:%S"),
                "end_time": spec.end.strftime("%H:%M:%S"),
                "enable_auto_attendance": 0,
                "determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
                "working_hours_calculation_based_on": "First Check-in and Last Check-out",
                "begin_check_in_before_shift_start_time": 180,
                "allow_check_out_after_shift_end_time": 180,
                "enable_late_entry_marking": 1,
                "late_entry_grace_period": 0,
                "enable_early_exit_marking": 1,
                "early_exit_grace_period": 0,
                "working_hours_threshold_for_half_day": 0,
                "working_hours_threshold_for_absent": 0,
            }
        )
        shift.insert(ignore_permissions=True)


def _ensure_employees(company: str, first_attendance_date: date) -> dict[str, str]:
    genders = frappe.get_all("Gender", pluck="name", order_by="creation asc", limit=2)
    if not genders:
        frappe.throw(_("At least one Gender record is required before generating demo employees."))

    result = {}
    for index, spec in enumerate(EMPLOYEES):
        device_id = f"{DEMO_DEVICE_PREFIX}{spec['key']}"
        employee = frappe.db.get_value("Employee", {"attendance_device_id": device_id}, "name")
        if not employee:
            employee_doc = frappe.new_doc("Employee")
            employee_doc.first_name = spec["first_name"]
            employee_doc.middle_name = spec["middle_name"]
            employee_doc.last_name = spec["last_name"]
            employee_doc.company = company
            employee_doc.status = "Active"
            employee_doc.gender = genders[index % len(genders)]
            employee_doc.date_of_birth = date(1990 + index, 1 + (index % 9), 10 + index)
            employee_doc.date_of_joining = add_days(first_attendance_date, -90)
            employee_doc.attendance_device_id = device_id
            employee_doc.employee_number = f"HRP-{spec['key']}"
            if employee_doc.meta.has_field("default_shift"):
                employee_doc.default_shift = SHIFTS[spec["shift"]].name
            employee_doc.insert(ignore_permissions=True)
            employee = employee_doc.name
        result[spec["key"]] = employee
    return result


def _ensure_shift_assignments(employees: dict[str, str], dates: list[date]):
    created = 0
    for spec in EMPLOYEES:
        employee = employees[spec["key"]]
        shift_name = SHIFTS[spec["shift"]].name
        existing = frappe.db.exists(
            "Shift Assignment",
            {
                "employee": employee,
                "shift_type": shift_name,
                "docstatus": ["<", 2],
                "start_date": ["<=", dates[0]],
            },
        )
        if existing:
            continue

        assignment = frappe.new_doc("Shift Assignment")
        assignment.employee = employee
        assignment.company = frappe.db.get_value("Employee", employee, "company")
        assignment.shift_type = shift_name
        assignment.start_date = add_days(dates[0], -1)
        assignment.end_date = add_days(dates[-1], 1)
        assignment.status = "Active"
        assignment.insert(ignore_permissions=True)
        assignment.submit()
        created += 1
    return created


def _attendance_exists(employee: str, attendance_date: date, shift_name: str) -> bool:
    return bool(
        frappe.db.exists(
            "Attendance",
            {
                "employee": employee,
                "attendance_date": attendance_date,
                "shift": shift_name,
                "docstatus": ["<", 2],
            },
        )
    )


def _attendance_times(
    attendance_date: date,
    shift_spec: ShiftSpec,
    late_minutes: float = 0,
    early_minutes: float = 0,
):
    start = datetime.combine(attendance_date, shift_spec.start)
    end = datetime.combine(attendance_date, shift_spec.end)
    if end <= start:
        end += timedelta(days=1)

    return (
        start + timedelta(minutes=flt(late_minutes)),
        end - timedelta(minutes=flt(early_minutes)),
    )


def _ensure_checkins(employee: str, in_time: datetime, out_time: datetime):
    logs = []
    created = 0
    for log_type, timestamp in (("IN", in_time), ("OUT", out_time)):
        existing = frappe.db.get_value(
            "Employee Checkin",
            {"employee": employee, "time": timestamp, "log_type": log_type},
            "name",
        )
        if existing:
            logs.append(frappe.get_doc("Employee Checkin", existing))
            continue

        log = frappe.new_doc("Employee Checkin")
        log.employee = employee
        log.time = timestamp
        log.log_type = log_type
        log.device_id = "HRP-DEMO-BIOMETRIC"
        log.skip_auto_attendance = 0
        log.insert(ignore_permissions=True)
        logs.append(log)
        created += 1

    logs.sort(key=lambda row: row.time)
    return logs, created


def _create_present_attendance(
    employee: str,
    attendance_date: date,
    shift_name: str,
    logs,
    in_time: datetime,
    out_time: datetime,
    late_minutes: float,
    early_minutes: float,
):
    from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log

    working_hours = max((out_time - in_time).total_seconds() / 3600, 0)
    attendance = mark_attendance_and_link_log(
        logs=logs,
        attendance_status="Present",
        attendance_date=attendance_date,
        working_hours=working_hours,
        late_entry=1 if flt(late_minutes) > 0 else 0,
        early_exit=1 if flt(early_minutes) > 0 else 0,
        in_time=in_time,
        out_time=out_time,
        shift=shift_name,
    )
    if not attendance:
        frappe.throw(
            _("Could not create demo attendance for employee {0} on {1}.").format(
                employee, attendance_date
            )
        )
    return attendance


def _create_absent_attendance(employee: str, attendance_date: date, shift_name: str):
    from hrms.hr.doctype.attendance.attendance import mark_attendance

    name = mark_attendance(employee, attendance_date, "Absent", shift=shift_name)
    if not name:
        frappe.throw(
            _("Could not create absent demo attendance for employee {0} on {1}.").format(
                employee, attendance_date
            )
        )
    return name


def _value_for_index(values, index: int):
    if not values:
        return 0
    return values[index % len(values)]
