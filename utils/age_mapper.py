from datetime import date
from dateutil.relativedelta import relativedelta

# Age ranges based on Toronto daycare licensing
AGE_GROUPS = {
    "infant": {
        "column": "IGSPACE",
        "label": "Infant (0-18 months)",
        "min_months": 0,
        "max_months": 18,
    },
    "toddler": {
        "column": "TGSPACE",
        "label": "Toddler (18-30 months)",
        "min_months": 18,
        "max_months": 30,
    },
    "preschool": {
        "column": "PGSPACE",
        "label": "Preschool (30 months - 4 years)",
        "min_months": 30,
        "max_months": 48,
    },
    "kindergarten": {
        "column": "KGSPACE",
        "label": "Kindergarten (4-5 years)",
        "min_months": 48,
        "max_months": 72,
    },
    "school_age": {
        "column": "SGSPACE",
        "label": "School Age (6+ years)",
        "min_months": 72,
        "max_months": None,
    },
}


def calculate_age_in_months(birthday: date, reference_date: date = None) -> int:
    """Calculate age in months from birthday to reference date (defaults to today)."""
    if reference_date is None:
        reference_date = date.today()
    diff = relativedelta(reference_date, birthday)
    return diff.years * 12 + diff.months


def get_age_group(birthday: date, reference_date: date = None) -> dict:
    """
    Determine which daycare age group a child belongs to.

    Args:
        birthday: Child's date of birth
        reference_date: Date to calculate age at (defaults to today)

    Returns:
        Dictionary with column name, label, and age range info
    """
    age_months = calculate_age_in_months(birthday, reference_date)

    for group_info in AGE_GROUPS.values():
        min_m = group_info["min_months"]
        max_m = group_info["max_months"]

        if max_m is None:  # School age has no upper limit
            if age_months >= min_m:
                return group_info
        elif min_m <= age_months < max_m:
            return group_info

    # Default to infant if no match
    return AGE_GROUPS["infant"]
