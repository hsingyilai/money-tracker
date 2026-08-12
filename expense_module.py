# This script has all the classes defined for this project.


class IncomeEntry:
    """An entry to the income list

    This class is the skeleton for recording an income

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
    """An entry to the expense list

    This class is the skeleton for recording an expense

    Attributes:
        date: A datetime.date object converted to string in standard ISO format, such as "2026-07-23".
        cost: How much money does it cost in dollar.
        category: What category does this expense belongs to.
        notes: Things that you want to take notes on according to the category it belongs to.
        regular: Regular, Irregular or Every x months, x being an integer
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
