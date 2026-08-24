"""Source disciplinary policy transcribed from the supplied Arabic PDF (pages 39-42).

Internal codes are stable; Arabic names/descriptions preserve the source wording as closely as possible.
"""

PENALTIES = {
    "NO-ACTION": {
        "penalty_name": "—",
        "penalty_type": "No Action",
        "description": "لا يوجد جزاء إضافي محدد في الجدول لهذه المرتبة.",
    },
    "WRITTEN-WARNING": {
        "penalty_name": "إنذار كتابي",
        "penalty_type": "Warning",
        "warning_type": "Written Warning",
        "description": "إنذار كتابي.",
    },
}

for pct in (5, 10, 15, 20, 25, 30, 50, 75):
    PENALTIES[f"PCT-{pct}"] = {
        "penalty_name": f"خصم {pct}% من الأجر اليومي",
        "penalty_type": "Salary Deduction",
        "deduction_basis": "Percentage of Daily Wage",
        "deduction_value": pct,
        "description": f"خصم {pct}% من الأجر اليومي.",
    }

DAY_LABELS = {
    1: "يوم",
    2: "يومين",
    3: "ثلاثة أيام",
    4: "أربعة أيام",
    5: "خمسة أيام",
}
for days in (1, 2, 3, 4, 5):
    label = DAY_LABELS[days]
    PENALTIES[f"DAY-{days}"] = {
        "penalty_name": f"خصم {label} من الأجر",
        "penalty_type": "Salary Deduction",
        "deduction_basis": "Days of Daily Wage",
        "deduction_value": days,
        "description": f"حسم أجر {label}.",
    }

PENALTIES.update({
    "ADMIN-DELAY-OR-DEPRIVE": {
        "penalty_name": "تأجيل الترقية أو الحرمان من العلاوة لمرة واحدة",
        "penalty_type": "Administrative Action",
        "administrative_action_type": "Delay Promotion or Deprive Increment",
        "description": "تأجيل الترقية، أو الحرمان من العلاوة لمرة واحدة.",
    },
    "TERM-WITH-BENEFIT": {
        "penalty_name": "الفصل من العمل مع المكافأة",
        "penalty_type": "Administrative Action",
        "administrative_action_type": "Termination With Benefit",
        "description": "الفصل من العمل مع المكافأة.",
    },
    "TERM-WITH-BENEFIT-COND-30": {
        "penalty_name": "الفصل مع المكافأة إذا لم يتجاوز مجموع الغياب 30 يوماً",
        "penalty_type": "Administrative Action",
        "administrative_action_type": "Termination With Benefit",
        "description": "الفصل من العمل مع المكافأة؛ إذا لم يتجاوز مجموع الغياب (30) يوم.",
    },
    "ADMIN-DELAY-OR-DEPRIVE-WARN-ART80": {
        "penalty_name": "تأجيل الترقية أو الحرمان من العلاوة مع إنذار بالفصل وفق المادة 80",
        "penalty_type": "Administrative Action",
        "administrative_action_type": "Delay Promotion or Deprive Increment",
        "description": "تأجيل الترقية، أو الحرمان من العلاوة لمرة واحدة، مع توجيه إنذار بالفصل طبقاً للمادة (الثمانون) من نظام العمل.",
    },
    "TERM-ART80": {
        "penalty_name": "الفصل من العمل طبقاً للمادة 80 من نظام العمل",
        "penalty_type": "Administrative Action",
        "administrative_action_type": "Termination Under Article 80",
        "description": "الفصل من العمل طبقاً للمادة (الثمانون) من نظام العمل.",
    },
    "TERM-NO-BENEFIT-10D-WARNING": {
        "penalty_name": "الفصل دون مكافأة أو تعويض بعد إنذار كتابي عند 10 أيام غياب",
        "penalty_type": "Administrative Action",
        "administrative_action_type": "Termination Without Benefit or Compensation",
        "description": "الفصل دون مكافأة أو تعويض، على أن يسبقه إنذار كتابي بعد الغياب مدة عشرة أيام، في نطاق حكم المادة (الثمانون) من النظام.",
    },
    "TERM-NO-BENEFIT-20D-WARNING": {
        "penalty_name": "الفصل دون مكافأة أو تعويض بعد إنذار كتابي عند 20 يوماً غياب",
        "penalty_type": "Administrative Action",
        "administrative_action_type": "Termination Without Benefit or Compensation",
        "description": "الفصل دون مكافأة أو تعويض، على أن يسبقه إنذار كتابي بعد الغياب مدة عشرين يوماً، في نطاق حكم المادة (الثمانون) من النظام.",
    },
    "TERM-NO-BENEFIT-NOTICE-COMP-ART80": {
        "penalty_name": "فصل بدون مكافأة أو إشعار أو تعويض بموجب المادة 80",
        "penalty_type": "Administrative Action",
        "administrative_action_type": "Termination Without Benefit or Notice or Compensation",
        "description": "فصل بدون مكافأة، أو إشعار، أو تعويض بموجب المادة (الثمانون).",
    },
})


def _composite(code, name, basis=None, value=0, late=False, early=False, absence=False,
               warning=None, action=None, description=None):
    row = {
        "penalty_name": name,
        "penalty_type": "Composite",
        "deduction_basis": basis,
        "deduction_value": value,
        "add_actual_late_minutes": 1 if late else 0,
        "add_actual_early_exit_minutes": 1 if early else 0,
        "add_actual_absence_days": 1 if absence else 0,
        "description": description or name,
    }
    if warning:
        row["warning_type"] = warning
    if action:
        row["administrative_action_type"] = action
    PENALTIES[code] = row


# Late-arrival composites: fixed penalty plus actual late-time wage deduction.
_composite("PCT-30-LATE", "خصم 30% بالإضافة إلى حسم أجر دقائق التأخر", "Percentage of Daily Wage", 30, late=True)
_composite("PCT-50-LATE", "خصم 50% بالإضافة إلى حسم أجر دقائق التأخر", "Percentage of Daily Wage", 50, late=True)
_composite("DAY-1-LATE", "خصم يوم بالإضافة إلى حسم أجر مدة التأخر", "Days of Daily Wage", 1, late=True)
_composite("DAY-2-LATE", "خصم يومين بالإضافة إلى حسم أجر مدة التأخر", "Days of Daily Wage", 2, late=True)
_composite("DAY-3-LATE", "خصم ثلاثة أيام بالإضافة إلى حسم أجر ساعات التأخر", "Days of Daily Wage", 3, late=True)
_composite(
    "WARN-LATE",
    "إنذار كتابي بالإضافة إلى حسم أجر ساعات التأخر",
    "Minutes of Wage",
    0,
    late=True,
    warning="Written Warning",
    description="إنذار كتابي، بالإضافة إلى حسم أجر ساعات التأخر.",
)

# Early-leaving composites: fixed penalty plus wage for the actual time away.
_composite("WARN-EARLY", "إنذار كتابي بالإضافة إلى حسم أجر مدة ترك العمل", "Minutes of Wage", 0, early=True, warning="Written Warning")
_composite("PCT-10-EARLY", "خصم 10% بالإضافة إلى حسم أجر مدة ترك العمل", "Percentage of Daily Wage", 10, early=True)
_composite("PCT-25-EARLY", "خصم 25% بالإضافة إلى حسم أجر مدة ترك العمل", "Percentage of Daily Wage", 25, early=True)
_composite("PCT-50-EARLY", "خصم 50% بالإضافة إلى حسم أجر مدة ترك العمل", "Percentage of Daily Wage", 50, early=True)
_composite("DAY-1-EARLY", "خصم يوم بالإضافة إلى حسم أجر مدة ترك العمل", "Days of Daily Wage", 1, early=True)

# Absence composites. The actual absence-wage part is controlled by a payroll setting
# because HRMS may already deduct unpaid absence through payment days.
for days in (2, 3, 4, 5):
    label = {2: "يومين", 3: "ثلاثة أيام", 4: "أربعة أيام", 5: "خمسة أيام"}[days]
    _composite(
        f"DAY-{days}-ABS",
        f"خصم {label} بالإضافة إلى حسم أجر مدة الغياب",
        "Days of Daily Wage",
        days,
        absence=True,
        description=f"حسم أجر {label}، بالإضافة إلى حسم أجر مدة الغياب.",
    )

_composite(
    "ADMIN-DELAY-OR-DEPRIVE-ABS",
    "تأجيل الترقية أو الحرمان من العلاوة بالإضافة إلى حسم أجر مدة الغياب",
    "Days of Daily Wage",
    0,
    absence=True,
    action="Delay Promotion or Deprive Increment",
    description="تأجيل الترقية، أو الحرمان من العلاوة لمرة واحدة، بالإضافة إلى حسم أجر مدة الغياب.",
)
_composite(
    "TERM-WITH-BENEFIT-COND-30-ABS",
    "الفصل مع المكافأة وفق شرط 30 يوماً بالإضافة إلى حسم أجر مدة الغياب",
    "Days of Daily Wage",
    0,
    absence=True,
    action="Termination With Benefit",
    description="الفصل من العمل مع المكافأة؛ إذا لم يتجاوز مجموع الغياب (30) يوم، بالإضافة إلى حسم أجر مدة الغياب.",
)
_composite(
    "ADMIN-DELAY-WARN-ART80-ABS",
    "تأجيل الترقية أو الحرمان من العلاوة مع إنذار بالفصل وحسم أجر الغياب",
    "Days of Daily Wage",
    0,
    absence=True,
    action="Delay Promotion or Deprive Increment",
    description="تأجيل الترقية، أو الحرمان من العلاوة لمرة واحدة، مع توجيه إنذار بالفصل طبقاً للمادة (الثمانون) من نظام العمل، بالإضافة إلى حسم أجر مدة الغياب.",
)
_composite(
    "TERM-ART80-ABS",
    "الفصل طبقاً للمادة 80 بالإضافة إلى حسم أجر مدة الغياب",
    "Days of Daily Wage",
    0,
    absence=True,
    action="Termination Under Article 80",
    description="الفصل من العمل طبقاً للمادة (الثمانون) من نظام العمل، بالإضافة إلى حسم أجر مدة الغياب.",
)


VIOLATIONS = [
    # أولاً: مخالفات تتعلق بمواعيد العمل (PDF p.39-40)
    {
        "violation_code": "WS-01",
        "violation_name": "التأخر عن مواعيد الحضور للعمل لغاية 15 دقيقة دون إذن أو عذر مقبول دون تعطيل عمال آخرين",
        "category": "Work Schedules",
        "description": "التأخر عن مواعيد الحضور للعمل لغاية (15) دقيقة دون إذن، أو عذر مقبول؛ إذا لم يترتب على ذلك تعطيل عمال آخرين.",
        "detection_source": "Employee Checkin", "detection_rule": "Late Entry", "minimum_minutes": 0.01, "maximum_minutes": 15, "requires_hr_confirmation": 1,
        "penalties": ["WRITTEN-WARNING", "PCT-5", "PCT-10", "PCT-20"],
    },
    {
        "violation_code": "WS-02",
        "violation_name": "التأخر لغاية 15 دقيقة دون إذن أو عذر مقبول مع تعطيل عمال آخرين",
        "category": "Work Schedules",
        "description": "التأخر عن مواعيد الحضور للعمل لغاية (15) دقيقة دون إذن، أو عذر مقبول؛ إذا ترتب على ذلك تعطيل عمال آخرين.",
        "detection_source": "Manual", "detection_rule": "Manual", "requires_hr_confirmation": 1,
        "penalties": ["WRITTEN-WARNING", "PCT-15", "PCT-25", "PCT-50"],
    },
    {
        "violation_code": "WS-03",
        "violation_name": "التأخر أكثر من 15 ولغاية 30 دقيقة دون إذن أو عذر مقبول دون تعطيل عمال آخرين",
        "category": "Work Schedules",
        "description": "التأخر عن مواعيد الحضور للعمل أكثر من (15) دقيقة لغاية (30) دقيقة دون إذن، أو عذر مقبول؛ إذا لم يترتب على ذلك تعطيل عمال آخرين.",
        "detection_source": "Employee Checkin", "detection_rule": "Late Entry", "minimum_minutes": 15.01, "maximum_minutes": 30, "requires_hr_confirmation": 1,
        "penalties": ["PCT-10", "PCT-15", "PCT-25", "PCT-50"],
    },
    {
        "violation_code": "WS-04",
        "violation_name": "التأخر أكثر من 15 ولغاية 30 دقيقة دون إذن أو عذر مقبول مع تعطيل عمال آخرين",
        "category": "Work Schedules",
        "description": "التأخر عن مواعيد الحضور للعمل أكثر من (15) دقيقة لغاية (30) دقيقة دون إذن، أو عذر مقبول؛ إذا ترتب على ذلك تعطيل عمال آخرين.",
        "detection_source": "Manual", "detection_rule": "Manual", "requires_hr_confirmation": 1,
        "penalties": ["PCT-25", "PCT-50", "PCT-75", "DAY-1"],
    },
    {
        "violation_code": "WS-05",
        "violation_name": "التأخر أكثر من 30 ولغاية 60 دقيقة دون إذن أو عذر مقبول دون تعطيل عمال آخرين",
        "category": "Work Schedules",
        "description": "التأخر عن مواعيد الحضور للعمل أكثر من (30) دقيقة لغاية (60) دقيقة دون إذن، أو عذر مقبول؛ إذا لم يترتب على ذلك تعطيل عمال آخرين.",
        "detection_source": "Employee Checkin", "detection_rule": "Late Entry", "minimum_minutes": 30.01, "maximum_minutes": 60, "requires_hr_confirmation": 1,
        "penalties": ["PCT-25", "PCT-50", "PCT-75", "DAY-1"],
    },
    {
        "violation_code": "WS-06",
        "violation_name": "التأخر أكثر من 30 ولغاية 60 دقيقة دون إذن أو عذر مقبول مع تعطيل عمال آخرين",
        "category": "Work Schedules",
        "description": "التأخر عن مواعيد الحضور للعمل أكثر من (30) دقيقة لغاية (60) دقيقة دون إذن، أو عذر مقبول؛ إذا ترتب على ذلك تعطيل عمال آخرين. بالإضافة إلى حسم أجر دقائق التأخر.",
        "detection_source": "Manual", "detection_rule": "Manual", "requires_hr_confirmation": 1,
        "penalties": ["PCT-30-LATE", "PCT-50-LATE", "DAY-1-LATE", "DAY-2-LATE"],
    },
    {
        "violation_code": "WS-07",
        "violation_name": "التأخر أكثر من ساعة دون إذن أو عذر مقبول سواء ترتب أو لم يترتب عليه تعطيل عمال آخرين",
        "category": "Work Schedules",
        "description": "التأخر عن مواعيد الحضور للعمل لمدة تزيد على ساعة دون إذن، أو عذر مقبول؛ سواء ترتب، أو لم يترتب على ذلك تعطيل عمال آخرين. بالإضافة إلى حسم أجر ساعات التأخر.",
        "detection_source": "Employee Checkin", "detection_rule": "Late Entry", "minimum_minutes": 60.01, "maximum_minutes": 0, "requires_hr_confirmation": 1,
        "penalties": ["WARN-LATE", "DAY-1-LATE", "DAY-2-LATE", "DAY-3-LATE"],
    },
    {
        "violation_code": "WS-08",
        "violation_name": "ترك العمل أو الانصراف قبل الميعاد بما لا يتجاوز 15 دقيقة دون إذن أو عذر مقبول",
        "category": "Work Schedules",
        "description": "ترك العمل، أو الانصراف قبل الميعاد دون إذن، أو عذر مقبول بما لا يتجاوز (15) دقيقة. بالإضافة إلى حسم أجر مدة ترك العمل.",
        "detection_source": "Employee Checkin", "detection_rule": "Early Exit", "minimum_minutes": 0.01, "maximum_minutes": 15, "requires_hr_confirmation": 1,
        "penalties": ["WARN-EARLY", "PCT-10-EARLY", "PCT-25-EARLY", "DAY-1-EARLY"],
    },
    {
        "violation_code": "WS-09",
        "violation_name": "ترك العمل أو الانصراف قبل الميعاد بما يتجاوز 15 دقيقة دون إذن أو عذر مقبول",
        "category": "Work Schedules",
        "description": "ترك العمل، أو الانصراف قبل الميعاد دون إذن، أو عذر مقبول بما يتجاوز (15) دقيقة. بالإضافة إلى حسم أجر مدة ترك العمل.",
        "detection_source": "Employee Checkin", "detection_rule": "Early Exit", "minimum_minutes": 15.01, "maximum_minutes": 0, "requires_hr_confirmation": 1,
        "penalties": ["PCT-10-EARLY", "PCT-25-EARLY", "PCT-50-EARLY", "DAY-1-EARLY"],
    },
    {
        "violation_code": "WS-10",
        "violation_name": "البقاء في أماكن العمل أو العودة إليها بعد انتهاء مواعيد العمل دون إذن مسبق",
        "category": "Work Schedules",
        "description": "البقاء في أماكن العمل، أو العودة إليها بعد انتهاء مواعيد العمل دون إذن مسبق.",
        "detection_source": "Manual", "detection_rule": "Manual",
        "penalties": ["WRITTEN-WARNING", "PCT-10", "PCT-25", "DAY-1"],
    },
    {
        "violation_code": "WS-11",
        "violation_name": "الغياب دون إذن كتابي أو عذر مقبول لمدة يوم خلال السنة العقدية الواحدة",
        "category": "Work Schedules",
        "description": "الغياب دون إذن كتابي، أو عذر مقبول لمدة يوم، خلال السنة العقدية الواحدة.",
        "detection_source": "Attendance", "detection_rule": "Absence", "requires_hr_confirmation": 1,
        "penalties": ["PCT-50", "DAY-1", "DAY-2", "DAY-3"],
    },
    {
        "violation_code": "WS-12",
        "violation_name": "الغياب المتصل من يومين إلى ستة أيام خلال السنة العقدية الواحدة",
        "category": "Work Schedules",
        "description": "الغياب المتصل دون إذن كتابي، أو عذر مقبول من يومين إلى ستة أيام، خلال السنة العقدية الواحدة. بالإضافة إلى حسم أجر مدة الغياب.",
        "detection_source": "Manual", "detection_rule": "Manual", "requires_hr_confirmation": 1,
        "penalties": ["DAY-2-ABS", "DAY-3-ABS", "DAY-4-ABS", "ADMIN-DELAY-OR-DEPRIVE-ABS"],
    },
    {
        "violation_code": "WS-13",
        "violation_name": "الغياب المتصل من سبعة أيام إلى عشرة أيام خلال السنة العقدية الواحدة",
        "category": "Work Schedules",
        "description": "الغياب المتصل دون إذن كتابي، أو عذر مقبول من سبعة أيام إلى عشرة أيام، خلال السنة العقدية الواحدة. بالإضافة إلى حسم أجر مدة الغياب.",
        "detection_source": "Manual", "detection_rule": "Manual", "requires_hr_confirmation": 1,
        "penalties": ["DAY-4-ABS", "DAY-5-ABS", "ADMIN-DELAY-OR-DEPRIVE-ABS", "TERM-WITH-BENEFIT-COND-30-ABS"],
    },
    {
        "violation_code": "WS-14",
        "violation_name": "الغياب المتصل من أحد عشر يوماً إلى أربعة عشر يوماً خلال السنة العقدية الواحدة",
        "category": "Work Schedules",
        "description": "الغياب المتصل دون إذن كتابي، أو عذر مقبول من أحد عشر يوماً إلى أربعة عشر يوماً، خلال السنة العقدية الواحدة. بالإضافة إلى حسم أجر مدة الغياب.",
        "detection_source": "Manual", "detection_rule": "Manual", "requires_hr_confirmation": 1,
        "penalties": ["DAY-5-ABS", "ADMIN-DELAY-WARN-ART80-ABS", "TERM-ART80-ABS", None],
    },
    {
        "violation_code": "WS-15",
        "violation_name": "الانقطاع عن العمل دون سبب مشروع مدة تزيد على خمسة عشر يوماً متصلة خلال السنة العقدية الواحدة",
        "category": "Work Schedules",
        "description": "الانقطاع عن العمل دون سبب مشروع مدة تزيد على خمسة عشر يوماً متصلة، خلال السنة العقدية الواحدة.",
        "detection_source": "Manual", "detection_rule": "Manual", "requires_hr_confirmation": 1,
        "penalties": ["TERM-NO-BENEFIT-10D-WARNING"] * 4,
    },
    {
        "violation_code": "WS-16",
        "violation_name": "الغياب المتقطع دون سبب مشروع مدة تزيد في مجموعها على ثلاثين يوماً خلال السنة العقدية الواحدة",
        "category": "Work Schedules",
        "description": "الغياب المتقطع دون سبب مشروع مدة تزيد في مجموعها على ثلاثين يوماً، خلال السنة العقدية الواحدة.",
        "detection_source": "Manual", "detection_rule": "Manual", "requires_hr_confirmation": 1,
        "penalties": ["TERM-NO-BENEFIT-20D-WARNING"] * 4,
    },

    # ثانياً: مخالفات تتعلق بتنظيم العمل (PDF p.40-41)
    {"violation_code": "WO-01", "violation_name": "التواجد دون مبرر في غير مكان العمل المخصص للعامل أثناء وقت الدوام", "category": "Work Organization", "description": "التواجد دون مبرر في غير مكان العمل المخصص للعامل أثناء وقت الدوام.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["PCT-10", "PCT-25", "PCT-50", "DAY-1"]},
    {"violation_code": "WO-02", "violation_name": "استقبال زائرين في غير أمور عمل المنشأة في أماكن العمل دون إذن من الإدارة", "category": "Work Organization", "description": "استقبال زائرين في غير أمور عمل المنشأة في أماكن العمل، دون إذن من الإدارة.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["WRITTEN-WARNING", "PCT-10", "PCT-15", "PCT-25"]},
    {"violation_code": "WO-03", "violation_name": "استعمال آلات أو معدات أو أدوات المنشأة لأغراض خاصة دون إذن", "category": "Work Organization", "description": "استعمال آلات، أو معدات، أو أدوات المنشأة؛ لأغراض خاصة، دون إذن.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["WRITTEN-WARNING", "PCT-10", "PCT-25", "PCT-50"]},
    {"violation_code": "WO-04", "violation_name": "تدخل العامل دون وجه حق في أي عمل ليس في اختصاصه أو لم يعهد به إليه", "category": "Work Organization", "description": "تدخل العامل، دون وجه حق في أي عمل ليس في اختصاصه، أو لم يعهد به إليه.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["PCT-50", "DAY-1", "DAY-2", "DAY-3"]},
    {"violation_code": "WO-05", "violation_name": "الخروج أو الدخول من غير المكان المخصص لذلك", "category": "Work Organization", "description": "الخروج، أو الدخول من غير المكان المخصص لذلك.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["WRITTEN-WARNING", "PCT-10", "PCT-15", "PCT-25"]},
    {"violation_code": "WO-06", "violation_name": "الإهمال في تنظيف الآلات وصيانتها أو عدم العناية بها أو عدم التبليغ عن خلل", "category": "Work Organization", "description": "الإهمال في تنظيف الآلات، وصيانتها، أو عدم العناية بها، أو عدم التبليغ عن ما بها من خلل.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["PCT-50", "DAY-1", "DAY-2", "DAY-3"]},
    {"violation_code": "WO-07", "violation_name": "عدم وضع أدوات الإصلاح والصيانة واللوازم الأخرى في الأماكن المخصصة لها بعد الانتهاء من العمل", "category": "Work Organization", "description": "عدم وضع أدوات الإصلاح، والصيانة، واللوازم الأخرى في الأماكن المخصصة لها، بعد الانتهاء من العمل.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["WRITTEN-WARNING", "PCT-25", "PCT-50", "DAY-1"]},
    {"violation_code": "WO-08", "violation_name": "تمزيق أو إتلاف إعلانات أو بلاغات إدارة المنشأة", "category": "Work Organization", "description": "تمزيق، أو إتلاف إعلانات، أو بلاغات إدارة المنشأة.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-2", "DAY-3", "DAY-5", "TERM-WITH-BENEFIT"]},
    {"violation_code": "WO-09", "violation_name": "الإهمال في العهد التي بحوزة العامل مثل السيارات والآلات والأجهزة والمعدات والأدوات", "category": "Work Organization", "description": "الإهمال في العهد التي بحوزته، مثال: (سيارات، آلات، أجهزة، معدات، أدوات ...إلخ).", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-2", "DAY-3", "DAY-5", "TERM-WITH-BENEFIT"]},
    {"violation_code": "WO-10", "violation_name": "الأكل في مكان العمل أو غير المكان المعد له أو في غير أوقات الراحة", "category": "Work Organization", "description": "الأكل في مكان العمل، أو غير المكان المعد له، أو في غير أوقات الراحة.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["WRITTEN-WARNING", "PCT-10", "PCT-15", "PCT-25"]},
    {"violation_code": "WO-11", "violation_name": "النوم أثناء العمل", "category": "Work Organization", "description": "النوم أثناء العمل.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["WRITTEN-WARNING", "PCT-10", "PCT-25", "PCT-50"]},
    {"violation_code": "WO-12", "violation_name": "النوم في الحالات التي تستدعي يقظة مستمرة", "category": "Work Organization", "description": "النوم في الحالات التي تستدعي يقظة مستمرة.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["PCT-50", "DAY-1", "DAY-2", "DAY-3"]},
    {"violation_code": "WO-13", "violation_name": "التسكع أو وجود العامل في غير مكان عمله أثناء ساعات العمل", "category": "Work Organization", "description": "التسكع، أو وجود العامل في غير مكان عمله، أثناء ساعات العمل.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["PCT-10", "PCT-25", "PCT-50", "DAY-1"]},
    {"violation_code": "WO-14", "violation_name": "التلاعب في إثبات الحضور والانصراف", "category": "Work Organization", "description": "التلاعب في إثبات الحضور، والانصراف.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-1", "DAY-2", "ADMIN-DELAY-OR-DEPRIVE", "TERM-WITH-BENEFIT"]},
    {"violation_code": "WO-15", "violation_name": "عدم إطاعة الأوامر العادية الخاصة بالعمل أو عدم تنفيذ التعليمات الخاصة بالعمل والمعلقة في مكان ظاهر", "category": "Work Organization", "description": "عدم إطاعة الأوامر العادية الخاصة بالعمل، أو عدم تنفيذ التعليمات الخاصة بالعمل، والمعلقة في مكان ظاهر.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["PCT-25", "PCT-50", "DAY-1", "DAY-2"]},
    {"violation_code": "WO-16", "violation_name": "التحريض على مخالفة الأوامر والتعليمات الخطية الخاصة بالعمل", "category": "Work Organization", "description": "التحريض على مخالفة الأوامر، والتعليمات الخطية الخاصة بالعمل.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-2", "DAY-3", "DAY-5", "TERM-WITH-BENEFIT"]},
    {"violation_code": "WO-17", "violation_name": "التدخين في الأماكن المحظورة والمعلن عنها للمحافظة على سلامة العمال والمنشأة", "category": "Work Organization", "description": "التدخين في الأماكن المحظورة، والمعلن عنها للمحافظة على سلامة العمال، والمنشأة.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-2", "DAY-3", "DAY-5", "TERM-WITH-BENEFIT"]},
    {"violation_code": "WO-18", "violation_name": "الإهمال أو التهاون في العمل الذي قد ينشأ عنه ضرر في صحة العمال أو سلامتهم أو المواد أو الأدوات والأجهزة", "category": "Work Organization", "description": "الإهمال، أو التهاون في العمل الذي قد ينشأ عنه ضرر في صحة العمال، أو سلامتهم، أو في المواد، أو الأدوات، والأجهزة.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-2", "DAY-3", "DAY-5", "TERM-WITH-BENEFIT"]},

    # ثالثاً: مخالفات تتعلق بسلوك العامل (PDF p.41-42)
    {"violation_code": "EC-01", "violation_name": "التشاجر مع الزملاء أو مع الغير أو إحداث مشاغبات في مكان العمل", "category": "Employee Conduct", "description": "التشاجر مع الزملاء، أو مع الغير، أو إحداث مشاغبات في مكان العمل.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-1", "DAY-2", "DAY-3", "DAY-5"]},
    {"violation_code": "EC-02", "violation_name": "التمارض أو ادعاء العامل كذباً أنه أصيب أثناء العمل أو بسببه", "category": "Employee Conduct", "description": "التمارض، أو ادعاء العامل كذباً أنه أصيب أثناء العمل، أو بسببه.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-1", "DAY-2", "DAY-3", "DAY-5"]},
    {"violation_code": "EC-03", "violation_name": "الامتناع عن إجراء الكشف الطبي عند طلب طبيب المنشأة أو رفض اتباع التعليمات الطبية أثناء العلاج", "category": "Employee Conduct", "description": "الامتناع عن إجراء الكشف الطبي عند طلب طبيب المنشأة، أو رفض اتباع التعليمات الطبية أثناء العلاج.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-1", "DAY-2", "DAY-3", "DAY-5"]},
    {"violation_code": "EC-04", "violation_name": "مخالفة التعليمات الصحية المعلقة بأماكن العمل", "category": "Employee Conduct", "description": "مخالفة التعليمات الصحية المعلقة بأماكن العمل.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["PCT-50", "DAY-1", "DAY-2", "DAY-5"]},
    {"violation_code": "EC-05", "violation_name": "الكتابة على جدران المنشأة أو لصق إعلانات عليها", "category": "Employee Conduct", "description": "الكتابة على جدران المنشأة، أو لصق إعلانات عليها.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["WRITTEN-WARNING", "PCT-10", "PCT-25", "PCT-50"]},
    {"violation_code": "EC-06", "violation_name": "رفض التفتيش الإداري عند الانصراف", "category": "Employee Conduct", "description": "رفض التفتيش الإداري عند الانصراف.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["PCT-25", "PCT-50", "DAY-1", "DAY-2"]},
    {"violation_code": "EC-07", "violation_name": "عدم تسليم النقود المحصلة لحساب المنشأة في المواعيد المحددة دون تبرير مقبول", "category": "Employee Conduct", "description": "عدم تسليم النقود المحصلة لحساب المنشأة في المواعيد المحددة دون تبرير مقبول.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-2", "DAY-3", "DAY-5", "TERM-WITH-BENEFIT"]},
    {"violation_code": "EC-08", "violation_name": "الامتناع عن ارتداء الملابس والأجهزة المقررة للوقاية والسلامة", "category": "Employee Conduct", "description": "الامتناع عن ارتداء الملابس، والأجهزة المقررة للوقاية والسلامة.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["WRITTEN-WARNING", "DAY-1", "DAY-2", "DAY-5"]},
    {"violation_code": "EC-09", "violation_name": "تعمد الخلوة مع الجنس الآخر في أماكن العمل", "category": "Employee Conduct", "description": "تعمد الخلوة مع الجنس الآخر في أماكن العمل.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-2", "DAY-3", "DAY-5", "TERM-WITH-BENEFIT"]},
    {"violation_code": "EC-10", "violation_name": "الإيحاء للآخرين بما يخدش الحياء قولاً أو فعلاً", "category": "Employee Conduct", "description": "الإيحاء للآخرين بما يخدش الحياء قولاً، أو فعلاً.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-2", "DAY-3", "DAY-5", "TERM-WITH-BENEFIT"]},
    {"violation_code": "EC-11", "violation_name": "الاعتداء على زملاء العمل بالقول أو الإشارة أو باستعمال وسائل الاتصال الالكترونية بالشتم أو التحقير", "category": "Employee Conduct", "description": "الاعتداء على زملاء العمل بالقول، أو الإشارة، أو باستعمال وسائل الاتصال الالكترونية بالشتم، أو التحقير.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-2", "DAY-3", "DAY-5", "TERM-WITH-BENEFIT"]},
    {"violation_code": "EC-12", "violation_name": "الاعتداء بالإيذاء الجسدي على زملاء العمل أو على غيرهم بطريقة إيجابية", "category": "Employee Conduct", "description": "الاعتداء بالإيذاء الجسدي على زملاء العمل، أو على غيرهم بطريقة إيجابية.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["TERM-NO-BENEFIT-NOTICE-COMP-ART80"] * 4},
    {"violation_code": "EC-13", "violation_name": "الاعتداء الجسدي أو القولي أو بأي وسيلة اتصال إلكترونية على صاحب العمل أو المدير المسؤول أو أحد الرؤساء أثناء العمل أو بسببه", "category": "Employee Conduct", "description": "الاعتداء الجسدي، أو القولي، أو بأي وسيلة من وسائل الاتصال الالكترونية على صاحب العمل، أو المدير المسؤول، أو أحد الرؤساء أثناء العمل، أو بسببه.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["TERM-NO-BENEFIT-NOTICE-COMP-ART80"] * 4},
    {"violation_code": "EC-14", "violation_name": "تقديم بلاغ أو شكوى كيدية", "category": "Employee Conduct", "description": "تقديم بلاغ، أو شكوى كيدية.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-3", "DAY-5", "TERM-WITH-BENEFIT", None]},
    {"violation_code": "EC-15", "violation_name": "عدم الامتثال لطلب لجنة التحقيق بالحضور", "category": "Employee Conduct", "description": "عدم الامتثال لطلب لجنة التحقيق بالحضور.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-2", "DAY-3", "DAY-5", "TERM-WITH-BENEFIT"]},
    {"violation_code": "EC-16", "violation_name": "عدم التقيد بالزي الرسمي المعتمد بالمنشأة", "category": "Employee Conduct", "description": "عدم التقيد بالزي الرسمي المعتمد بالمنشأة.", "detection_source": "Manual", "detection_rule": "Manual", "penalties": ["DAY-1", "DAY-2", "DAY-3", "DAY-5"]},
]

DEFAULT_POLICY_BY_VIOLATION = {row["violation_code"]: tuple(row["penalties"]) for row in VIOLATIONS}
