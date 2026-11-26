"""Data classes for the entries stored by the app."""
import re

# The colour a category has until one is picked: what the colour picker returns
# for black.
DEFAULT_CATEGORY_COLOR = "#000000"


class IncomeEntry:
    """An entry to the income list.

    Attributes:
        date: A datetime.date object converted to string in standard ISO format, such as "2026-07-23".
        amount: How much money was earned in dollar.
        category: What category does this income belongs to.
        note: A text entry to take notes on this income.
    """

    def __init__(self, date: str, amount: float, category: str, note: str):
        self.date = date
        self.amount = amount
        self.category = category
        self.note = note


class ExpenseEntry:
    """An entry to the expense list.

    Attributes:
        date: A datetime.date object converted to string in standard ISO format, such as "2026-07-23".
        cost: How much money does it cost in dollar.
        category: What category does this expense belongs to.
        notes: Things that you want to take notes on according to the category it belongs to.
        regular: "Regular", "Irregular", or for a periodic expense "Every x months",
            x being an integer. A periodic expense merged with other entries of
            the same one reads "Every x months, group N", N being 1, 2, 3, ...
            (a new entry never has a group; only merging adds it). Only the
            latest entry of a group is listed and predicted.
        trip: The trip this expense is linked to, "" if none.
    """

    def __init__(
        self,
        date: str,
        cost: float,
        category: str,
        notes: dict,
        regular: str,
        trip: str,
    ):
        self.date = date
        self.cost = cost
        self.category = category
        self.notes = notes
        self.regular = regular
        self.trip = trip


_PERIODIC = re.compile(r"Every (\d+) months(?:, group (\d+))?")


def parse_periodic(regular: str) -> tuple[int, int | None] | None:
    """(x, N) for "Every x months, group N", (x, None) for "Every x months", and
    None for anything that is not a periodic expense."""
    match = _PERIODIC.fullmatch(regular)
    if match is None:
        return None
    months, group = match.groups()
    return int(months), None if group is None else int(group)


def periodic_text(months: int, group: int | None = None) -> str:
    """The `regular` value of a periodic expense."""
    text = f"Every {months} months"
    return text if group is None else f"{text}, group {group}"


def latest_periodic(expenses: list[ExpenseEntry]) -> list[ExpenseEntry]:
    """The periodic expenses that stand for something, in the order given: every
    one without a group, and the latest entry of each group (the later one in
    `expenses` if two share a date)."""
    periodic = [(entry, parse_periodic(entry.regular)) for entry in expenses]
    periodic = [(entry, parts[1]) for entry, parts in periodic if parts is not None]
    latest: dict[int, ExpenseEntry] = {}
    for entry, group in periodic:
        if group is not None and (group not in latest or entry.date >= latest[group].date):
            latest[group] = entry
    return [entry for entry, group in periodic if group is None or latest[group] is entry]
