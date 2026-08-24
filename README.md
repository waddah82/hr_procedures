# HR Procedures

HR Procedures is a Frappe/HRMS application for employee violations, disciplinary penalties, automated detection from Attendance / Employee Checkin, and payroll deductions through HRMS Additional Salary.

## Core behavior

- Violation types are maintained in **HR Violation Type**.
- Penalties are maintained in **HR Penalty Template**.
- **HR Violation Policy** contains one protected row per active violation type. Users cannot manually add/delete policy rows from the UI; the server re-syncs rows from violation types.
- **Employee Violation** is submittable.
- The policy-derived penalty is preserved as the **Deserved Penalty**.
- Before submit, authorized HR users may execute the deserved penalty, waive it, or apply an alternative penalty depending on **HR Procedures Settings**.
- Monetary penalties create and optionally submit **Additional Salary** using a Deduction Salary Component.
- Non-monetary penalties create **HR Administrative Action** records.
- Automatic detection creates **Draft** violations only. The penalty is never executed until the Employee Violation is submitted.
- Attendance cancellation removes only auto-created draft violations; submitted violations are never silently deleted.

## Compatibility

Designed for Frappe / ERPNext / HRMS 15 and 16. Test on a staging site before production deployment.

## Install

This app is already created. **Do not run `bench new-app hr_procedures`**.

The package uses a zero-dependency local PEP 517/660 backend so editable installation does not need to download `flit_core`, `setuptools`, or another build backend from PyPI.

```bash
cd ~/frappe-bench
bench get-app /path/to/hr_procedures
bench --site your.site install-app hr_procedures
bench --site your.site migrate
bench build --app hr_procedures
```

If the server has no internet and the application folder is copied manually into `apps/hr_procedures`, install it with:

```bash
cd ~/frappe-bench
./env/bin/python -m pip install -e ./apps/hr_procedures
grep -qxF hr_procedures sites/apps.txt || echo hr_procedures >> sites/apps.txt
bench --site your.site install-app hr_procedures
bench --site your.site migrate
bench build --app hr_procedures
```

Then open **HR Procedures Settings** and set:

1. Deduction Salary Component.
2. Daily wage calculation method.
3. Whether penalty waiver is allowed.
4. Whether alternative penalties are allowed.
5. The role authorized to override penalties.
6. Automatic detection settings.

## Recommended setup sequence

1. Create / review HR Penalty Templates.
2. Create HR Violation Types.
3. Create one active HR Violation Policy per company and click **Sync Violation Types**.
4. Configure occurrence 1-4 penalties on the policy.
5. Enable automatic detection after testing the Attendance / Employee Checkin flow.

## Arabic translation

All application labels, buttons and application messages are translated in:

`hr_procedures/translations/ar.csv`


## Retry after an interrupted install

If a previous `bench new-app` or installation attempt was interrupted, Frappe can retain a stale bench-level `app_modules` cache entry with no modules for this app. Version 0.1.2 refreshes that cache in `before_install` before Frappe runs `sync_for()`.
