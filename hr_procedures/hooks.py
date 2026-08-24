app_name = "hr_procedures"
app_title = "HR Procedures"
app_publisher = "Shams Solutions"
app_description = "Employee violations and disciplinary procedures for Frappe HRMS"
app_email = ""
app_license = "MIT"

required_apps = ["hrms"]

# Refresh Frappe's bench-level module map before schema sync. This is important
# when the app name was previously added to apps.txt by an interrupted install.
before_install = "hr_procedures.install.before_install"
after_install = "hr_procedures.install.after_install"

doc_events = {
    "Employee Checkin": {
        "after_insert": "hr_procedures.events.employee_checkin.after_insert",
        "on_trash": "hr_procedures.events.employee_checkin.on_trash",
    },
    "Attendance": {
        "on_submit": "hr_procedures.events.attendance.on_submit",
        "on_cancel": "hr_procedures.events.attendance.on_cancel",
    },
}

scheduler_events = {
    "hourly": [
        "hr_procedures.events.employee_checkin.scan_pending_employee_checkins",
    ]
}

doctype_js = {
    "Employee": "public/js/employee.js",
}
