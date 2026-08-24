frappe.ui.form.on("Employee Violation", {
    refresh(frm) {
        configure_penalty_decision(frm);
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Recalculate Penalty"), () => refresh_preview(frm));
        }
    },
    employee(frm) { refresh_preview(frm); },
    company(frm) { refresh_preview(frm); },
    violation_type(frm) { refresh_preview(frm); },
    violation_date(frm) { refresh_preview(frm); },
    late_minutes(frm) { refresh_preview(frm); },
    early_exit_minutes(frm) { refresh_preview(frm); },
    absence_days(frm) { refresh_preview(frm); },
    penalty_decision(frm) {
        configure_penalty_decision(frm);
        refresh_preview(frm);
    },
    alternative_penalty(frm) { refresh_preview(frm); },
});

function configure_penalty_decision(frm) {
    frappe.db.get_single_value("HR Procedures Settings", "allow_penalty_waiver").then((allowWaiver) => {
        frappe.db.get_single_value("HR Procedures Settings", "allow_alternative_penalty").then((allowAlternative) => {
            const options = [__("Execute Deserved Penalty")];
            if (allowWaiver) options.push(__("Waive Penalty"));
            if (allowAlternative) options.push(__("Apply Alternative Penalty"));
            frm.set_df_property("penalty_decision", "options", options.join("\n"));

            const allowed = ["Execute Deserved Penalty"];
            if (allowWaiver) allowed.push("Waive Penalty");
            if (allowAlternative) allowed.push("Apply Alternative Penalty");
            if (!allowed.includes(frm.doc.penalty_decision)) {
                frm.set_value("penalty_decision", "Execute Deserved Penalty");
            }

            frm.toggle_display("alternative_penalty", Boolean(allowAlternative) && frm.doc.penalty_decision === "Apply Alternative Penalty");
            frm.toggle_display("decision_reason", frm.doc.penalty_decision !== "Execute Deserved Penalty");
        });
    });
}

function refresh_preview(frm) {
    if (frm.doc.docstatus !== 0 || !frm.doc.employee || !frm.doc.violation_type || !frm.doc.violation_date) return;

    frappe.call({
        method: "hr_procedures.hr_procedures.doctype.employee_violation.employee_violation.get_violation_preview",
        args: {
            employee: frm.doc.employee,
            violation_type: frm.doc.violation_type,
            violation_date: frm.doc.violation_date,
            company: frm.doc.company,
            late_minutes: frm.doc.late_minutes || 0,
            early_exit_minutes: frm.doc.early_exit_minutes || 0,
            absence_days: frm.doc.absence_days || 0,
            penalty_decision: frm.doc.penalty_decision || "Execute Deserved Penalty",
            alternative_penalty: frm.doc.alternative_penalty,
        },
        callback(r) {
            if (!r.message) return;
            const m = r.message;
            frm.set_value("violation_policy", m.violation_policy);
            frm.set_value("occurrence_no", m.occurrence_no);
            frm.set_value("penalty_tier", m.penalty_tier);
            frm.set_value("deserved_penalty", m.deserved_penalty);
            frm.set_value("deserved_penalty_details", m.deserved_penalty_details);
            frm.set_value("deserved_deduction_amount", m.deserved_deduction_amount);
            frm.set_value("final_penalty", m.final_penalty);
            frm.set_value("final_deduction_amount", m.final_deduction_amount);
        },
    });
}
