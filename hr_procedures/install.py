import frappe
from frappe import _

APP_NAME = "hr_procedures"
MODULE_NAME = "HR Procedures"
MODULE_KEY = "hr_procedures"


def before_install():
    """Ensure Frappe sees the app module before installer schema synchronization.

    A failed or interrupted `bench new-app` / install can leave the bench-wide
    `app_modules` Redis cache with `hr_procedures: []`. Frappe's installer only
    rebuilds that cache when the app key is absent, so an empty stale entry makes
    `sync_for()` skip every DocType in the app. Refreshing the cache here makes
    installation deterministic and safe to retry.
    """
    cache = frappe.cache() if callable(frappe.cache) else frappe.cache
    cache.delete_value("app_modules")
    frappe.setup_module_map(include_all_apps=True)

    modules = (frappe.local.app_modules or {}).get(APP_NAME) or []
    if MODULE_KEY not in modules:
        frappe.throw(
            _(
                "HR Procedures module was not discovered from modules.txt. "
                "Verify that {0}/modules.txt contains '{1}'."
            ).format(APP_NAME, MODULE_NAME)
        )

    owner = (frappe.local.module_app or {}).get(MODULE_KEY)
    if owner != APP_NAME:
        frappe.throw(
            _(
                "HR Procedures module is mapped to app '{0}' instead of '{1}'. "
                "Resolve the duplicate module name before installing."
            ).format(owner or _("Unknown"), APP_NAME)
        )


def after_install():
    _validate_synced_doctypes()
    from hr_procedures.data.source_policy import seed_source_policy

    seed_source_policy(backfill_policies=True)


def _validate_synced_doctypes():
    required_doctypes = (
        "HR Penalty Template",
        "HR Violation Type",
        "HR Violation Policy Row",
        "HR Violation Policy",
        "Employee Violation",
        "HR Administrative Action",
        "HR Procedures Settings",
    )

    missing = [name for name in required_doctypes if not frappe.db.exists("DocType", name)]
    if missing:
        frappe.throw(
            _(
                "HR Procedures schema synchronization did not create these DocTypes: {0}. "
                "The installation was stopped before seed data was created."
            ).format(", ".join(missing))
        )
