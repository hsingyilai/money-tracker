"""Monthly totals for the Graph and Prediction pages. No Qt in here so it is easy to test.

A month is a (year, month) tuple. Every function takes an optional `start` and
`end` month: the graph then covers exactly the months from start to end (months
with no entries are empty bars), and entries outside that range are left out.
Without them it covers the first to the last month that has an entry.
"""
import datetime
from collections import defaultdict

from .models import ExpenseEntry, IncomeEntry

Month = tuple[int, int]


def _month_key(date_str: str) -> Month:
    date = datetime.date.fromisoformat(date_str)
    return date.year, date.month


def month_label(key: Month) -> str:
    return f"{key[0]}-{key[1]:02d}"


def _month_span(keys) -> list[Month]:
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


def _months(keys, start: Month | None, end: Month | None) -> list[Month]:
    """The months to graph: start to end, where a missing one defaults to the
    earliest / latest of `keys`. Empty if there is nothing to span, or if start
    is after end."""
    keys = list(keys)
    if start is None and keys:
        start = min(keys)
    if end is None and keys:
        end = max(keys)
    if start is None or end is None or start > end:
        return []
    return _month_span([start, end])


def month_choices(dates, year: int) -> list[Month]:
    """The months a graph can start or end at: every month from the earliest
    date to the latest, always including January to December of `year`."""
    return _month_span([*map(_month_key, dates), (year, 1), (year, 12)])


def expense_by_month(
    expenses: list[ExpenseEntry],
    start: Month | None = None,
    end: Month | None = None,
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

    months = _months([*regular, *not_regular], start, end)
    return (
        [month_label(key) for key in months],
        [round(regular.get(key, 0.0), 2) for key in months],
        [round(not_regular.get(key, 0.0), 2) for key in months],
    )


def category_by_month(
    expenses: list[ExpenseEntry],
    category_names: set[str] | None,
    start: Month | None = None,
    end: Month | None = None,
) -> tuple[list[str], list[float]]:
    """Return (month labels, total spent in `category_names` each month).

    `category_names` is the selected category and everything below it; None
    means every expense. Without start and end the months span all expenses
    (not only this category's), so the axis stays the same whichever category
    is picked.
    """
    totals = defaultdict(float)
    keys = []
    for entry in expenses:
        key = _month_key(entry.date)
        keys.append(key)
        if category_names is None or entry.category in category_names:
            totals[key] += entry.cost

    months = _months(keys, start, end)
    return (
        [month_label(key) for key in months],
        [round(totals.get(key, 0.0), 2) for key in months],
    )


def regular_expense_by_month(
    expenses: list[ExpenseEntry],
    start: Month | None = None,
    end: Month | None = None,
) -> tuple[list[str], list[float]]:
    """Return (month labels, regular totals), counting only entries whose
    regular field is exactly "Regular". Without start and end the months span
    from the first to the last regular expense."""
    months, regular, _ = expense_by_month(
        [entry for entry in expenses if entry.regular == "Regular"], start, end
    )
    return months, regular


def net_by_month(
    incomes: list[IncomeEntry],
    expenses: list[ExpenseEntry],
    start: Month | None = None,
    end: Month | None = None,
) -> tuple[list[str], list[float]]:
    """Return (month labels, income minus expense for each month)."""
    income_total = defaultdict(float)
    expense_total = defaultdict(float)
    for entry in incomes:
        income_total[_month_key(entry.date)] += entry.amount
    for entry in expenses:
        expense_total[_month_key(entry.date)] += entry.cost

    months = _months([*income_total, *expense_total], start, end)
    return (
        [month_label(key) for key in months],
        [
            round(income_total.get(key, 0.0) - expense_total.get(key, 0.0), 2)
            for key in months
        ],
    )


def regular_monthly_average(
    expenses: list[ExpenseEntry],
    category_names: set[str] | None,
    current_month: Month,
) -> float:
    """Average regular spending per month in `category_names` (None means every
    category), leaving out `current_month`, which is not over yet.

    It averages over every month from the first month with any expense to the
    month before `current_month`, so a month without regular spending counts as
    zero. Returns 0.0 when there is no such month.
    """
    if not expenses:
        return 0.0
    year, month = current_month
    last = (year, month - 1) if month > 1 else (year - 1, 12)
    months = _months([_month_key(entry.date) for entry in expenses], None, last)
    if not months:
        return 0.0
    total = sum(
        entry.cost
        for entry in expenses
        if entry.regular == "Regular"
        and (category_names is None or entry.category in category_names)
        and months[0] <= _month_key(entry.date) <= last
    )
    return total / len(months)
