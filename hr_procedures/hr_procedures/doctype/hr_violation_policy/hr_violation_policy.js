frappe.ui.form.on("HR Violation Policy", {
    onload(frm) {
        load_source_rows_for_new_policy(frm);
    },

    refresh(frm) {
        lock_violation_grid(frm);
        load_source_rows_for_new_policy(frm);

        if (!frm.is_new()) {
            frm.add_custom_button(__("Sync Violation Types"), () => {
                frappe.call({
                    method: "hr_procedures.hr_procedures.doctype.hr_violation_policy.hr_violation_policy.sync_violation_types",
                    args: { policy_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Synchronizing violation types..."),
                    callback() {
                        frm.reload_doc();
                    },
                });
            });

            frm.add_custom_button(__("Reset Source PDF Penalties"), () => {
                frappe.confirm(
                    __("This will restore the 50 source violations to the penalties and order defined in the supplied PDF. Continue?"),
                    () => {
                        frappe.call({
                            method: "hr_procedures.hr_procedures.doctype.hr_violation_policy.hr_violation_policy.reset_source_pdf_penalties",
                            args: { policy_name: frm.doc.name },
                            freeze: true,
                            freeze_message: __("Restoring source PDF penalties..."),
                            callback() {
                                frm.reload_doc();
                            },
                        });
                    }
                );
            }, __("Actions"));
        }
    },
});

frappe.ui.form.on("HR Violation Policy Row", {
    occurrence_1_penalty(frm) { refresh_row_display(frm); },
    occurrence_2_penalty(frm) { refresh_row_display(frm); },
    occurrence_3_penalty(frm) { refresh_row_display(frm); },
    occurrence_4_penalty(frm) { refresh_row_display(frm); },
});

function lock_violation_grid(frm) {
    const grid = frm.fields_dict.violations && frm.fields_dict.violations.grid;
    if (!grid) return;

    grid.cannot_add_rows = true;
    grid.cannot_delete_rows = true;
    grid.wrapper.find(".grid-add-row, .grid-remove-rows, .grid-delete-row, .grid-duplicate-row").hide();
}

function load_source_rows_for_new_policy(frm) {
    if (!frm.is_new() || frm.__hrp_source_rows_loading) return;
    if ((frm.doc.violations || []).length) return;

    frm.__hrp_source_rows_loading = true;
    frappe.call({
        method: "hr_procedures.hr_procedures.doctype.hr_violation_policy.hr_violation_policy.get_default_policy_rows",
        callback(r) {
            const rows = r.message || [];
            frm.clear_table("violations");
            rows.forEach((source) => {
                const row = frm.add_child("violations");
                row.violation_type = source.violation_type;
                row.violation_display = source.violation_display;
                row.occurrence_1_penalty = source.occurrence_1_penalty;
                row.occurrence_2_penalty = source.occurrence_2_penalty;
                row.occurrence_3_penalty = source.occurrence_3_penalty;
                row.occurrence_4_penalty = source.occurrence_4_penalty;
                row.occurrence_1_display = source.occurrence_1_display;
                row.occurrence_2_display = source.occurrence_2_display;
                row.occurrence_3_display = source.occurrence_3_display;
                row.occurrence_4_display = source.occurrence_4_display;
            });
            frm.refresh_field("violations");
            lock_violation_grid(frm);
            frm.__hrp_source_rows_loading = false;
        },
        error() {
            frm.__hrp_source_rows_loading = false;
        },
    });
}

function refresh_row_display(frm) {
    // Server-side validate remains authoritative. This refresh ensures edited Link titles
    // are shown immediately after save/reload without exposing internal codes in the grid.
    frm.dirty();
}
