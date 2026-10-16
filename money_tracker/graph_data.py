"""Monthly totals for the Graph page. No Qt in here so it is easy to test."""
import datetime
from collections import defaultdict

from .models import ExpenseEntry, IncomeEntry


def _month_key(date_str: str) -> tuple[int, int]:
    date = datetime.date.fromisoformat(date_str)
    return date.year, date.month


def _label(key: tuple[int, int]) -> str:
    return f"{key[0]}-{key[1]:02d}"


def _month_span(keys) -> list[tuple[int, int]]:
    """Every month from the earliest to the latest key, so months with no
    entries still show up as empty bars instead of being skipped."""
    keys = list(keys)
    if not keys:
        return []
    year, month = min(keys)
    last = max(keys)
    months = []
    while (year, month) <= last:
        months.append((year, month))
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return months


def expense_by_month(
    expenses: list[ExpenseEntry],
) -> tuple[list[str], list[float], list[float]]:
    """Return (month labels, regular totals, not-regular totals).

    "Regular" means the entry's regular field is exactly "Regular"; Irregular
    and "Every X months" both count as not regular, as in the Summary page.
    """
    regular = defaultdict(float)
    not_regular = defaultdict(float)
    for entry in expenses:
        key = _month_key(entry.date)
        if entry.regular == "Regular":
            regular[key] += entry.cost
        else:
            not_regular[key] += entry.cost

    months = _month_span([*regular, *not_regular])
    return (
        [_label(key) for key in months],
        [round(regular.get(key, 0.0), 2) for key in months],
        [round(not_regular.get(key, 0.0), 2) for key in months],
    )


def regular_expense_by_month(
    expenses: list[ExpenseEntry],
) -> tuple[list[str], list[float]]:
    """Return (month labels, regular totals), counting only entries whose
    regular field is exactly "Regular". The months span from the first to
    the last regular expense."""
    months, regular, _ = expense_by_month(
        [entry for entry in expenses if entry.regular == "Regular"]
    )
    return months, regular


def net_by_month(
    incomes: list[IncomeEntry], expenses: list[ExpenseEntry]
) -> tuple[list[str], list[float]]:
    """Return (month labels, income minus expense for each month)."""
    income_total = defaultdict(float)
    expense_total = defaultdict(float)
    for entry in incomes:
        income_total[_month_key(entry.date)] += entry.amount
    for entry in expenses:
        expense_total[_month_key(entry.date)] += entry.cost

    months = _month_span([*income_total, *expense_total])
    return (
        [_label(key) for key in months],
        [
            round(income_total.get(key, 0.0) - expense_total.get(key, 0.0), 2)
            for key in months
        ],
    )
