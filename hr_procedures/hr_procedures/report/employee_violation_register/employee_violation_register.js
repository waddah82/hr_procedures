frappe.query_reports["Employee Violation Register"] = {
    filters: [
        { fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
        { fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
        { fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
        { fieldname: "violation_type", label: __("Violation Type"), fieldtype: "Link", options: "HR Violation Type" },
        { fieldname: "source", label: __("Source"), fieldtype: "Select", options: "\nManual\nAutomatic" },
        { fieldname: "penalty_decision", label: __("Penalty Decision"), fieldtype: "Select", options: "\nExecute Deserved Penalty\nWaive Penalty\nApply Alternative Penalty" },
        { fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
        { fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
    ],
};
