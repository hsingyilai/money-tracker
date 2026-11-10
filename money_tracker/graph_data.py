"""Monthly totals for the Graph and Prediction pages. No Qt in here so it is easy to test.

A month is a (year, month) tuple. Every function takes an optional `start` and
`end` month: the graph then covers exactly the months from start to end (months
with no entries are empty bars), and entries outside that range are left out.
Without them it covers the first to the last month that has an entry.
"""
import datetime
import re
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


def _monthly_average(
    all_dates: list[str], counted: list[tuple[str, float]], current_month: Month
) -> float:
    """Total of the `counted` (date, amount) pairs per month, over every month
    from the first of `all_dates` to the month before `current_month` (which is
    not over yet, so it is left out). A month with nothing counted is a zero.
    Returns 0.0 when there is no such month."""
    if not all_dates:
        return 0.0
    year, month = current_month
    last = (year, month - 1) if month > 1 else (year - 1, 12)
    months = _months([_month_key(date) for date in all_dates], None, last)
    if not months:
        return 0.0
    total = sum(
        amount for date, amount in counted if months[0] <= _month_key(date) <= last
    )
    return total / len(months)


def regular_monthly_average(
    expenses: list[ExpenseEntry],
    category_names: set[str] | None,
    current_month: Month,
) -> float:
    """Average regular spending per month in `category_names` (None means every
    category), leaving out `current_month`.

    It averages over every month from the first month with any expense, so a
    month without regular spending counts as zero.
    """
    return _monthly_average(
        [entry.date for entry in expenses],
        [
            (entry.date, entry.cost)
            for entry in expenses
            if entry.regular == "Regular"
            and (category_names is None or entry.category in category_names)
        ],
        current_month,
    )


def income_monthly_average(
    incomes: list[IncomeEntry],
    category_names: set[str] | None,
    current_month: Month,
) -> float:
    """Average income per month in `category_names` (None means every category),
    leaving out `current_month`.

    It averages over every month from the first month with any income, so a
    month without income counts as zero.
    """
    return _monthly_average(
        [entry.date for entry in incomes],
        [
            (entry.date, entry.amount)
            for entry in incomes
            if category_names is None or entry.category in category_names
        ],
        current_month,
    )


def _next_month(key: Month) -> Month:
    year, month = key
    return (year, month + 1) if month < 12 else (year + 1, 1)


def _month_number(key: Month) -> int:
    """Months counted from year 0, so months can be subtracted and stepped."""
    return key[0] * 12 + key[1] - 1


_EVERY_MONTHS = re.compile(r"Every (\d+) months")


def _period(entry: ExpenseEntry) -> int | None:
    """The N of an "Every N months" expense, or None if it is not periodic."""
    match = _EVERY_MONTHS.fullmatch(entry.regular)
    return int(match.group(1)) if match and int(match.group(1)) >= 1 else None


def periodic_expense_by_month(
    expenses: list[ExpenseEntry], current_month: Month, months: int
) -> dict[Month, float]:
    """The periodic ("Every N months") expenses that fall in each of the `months`
    months starting with `current_month`.

    Every periodic entry is worked out on its own: it counts in its own month if
    that is `current_month` or later, and is expected again every N months after
    that. Repeats that fall before `current_month` are not counted. Entries are
    never merged, so the same expense entered twice counts twice.
    """
    start = _month_number(current_month)
    last = start + months - 1
    totals: dict[Month, float] = defaultdict(float)

    def add(month_number: int, cost: float) -> None:
        if start <= month_number <= last:
            year, month = divmod(month_number, 12)
            totals[(year, month + 1)] += cost

    for entry in expenses:
        period = _period(entry)
        if period is None:
            continue
        first = _month_number(_month_key(entry.date))
        add(first, entry.cost)  # When it happened (or is dated to happen).
        # The repeats first + N, first + 2N, ... starting with the first one that
        # is not before the start.
        j = max(1, -(-(start - first) // period))
        while first + j * period <= last:
            add(first + j * period, entry.cost)
            j += 1
    return dict(totals)


def balance_prediction(
    incomes: list[IncomeEntry],
    expenses: list[ExpenseEntry],
    months: int,
    current_month: Month,
) -> tuple[list[str], list[float]]:
    """Return (month labels, predicted balance change), one point for each of
    `months` months starting with `current_month`. Each value is the change in
    the balance since the start of `current_month`, up to the end of that month.

    Every month earns the average income and spends the average regular expense
    (over all categories, as regular_monthly_average and income_monthly_average
    work them out). Only the current month is different: it keeps what it has
    already earned or spent if that is more than the average. Later months always
    use the averages, whatever entries are dated in them. On top of the regular
    expense, a month also spends the periodic expenses that fall in it (see
    periodic_expense_by_month). Irregular expenses are left out.
    """
    average_income = income_monthly_average(incomes, None, current_month)
    average_expense = regular_monthly_average(expenses, None, current_month)
    # What the current month has so far (months after it are not looked at).
    income_so_far = sum(
        entry.amount for entry in incomes if _month_key(entry.date) == current_month
    )
    regular_so_far = sum(
        entry.cost
        for entry in expenses
        if entry.regular == "Regular" and _month_key(entry.date) == current_month
    )

    periodic = periodic_expense_by_month(expenses, current_month, months)

    labels, balance = [], []
    change = 0.0
    key = current_month
    for _ in range(months):
        income, expense = average_income, average_expense
        if key == current_month:
            income = max(income, income_so_far)
            expense = max(expense, regular_so_far)
        expense += periodic.get(key, 0.0)
        change += income - expense
        labels.append(month_label(key))
        balance.append(round(change, 2))
        key = _next_month(key)
    return labels, balance
