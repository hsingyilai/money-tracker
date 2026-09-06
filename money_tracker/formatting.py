"""Helpers that turn entries into the strings shown in the UI."""
import datetime

from .models import ExpenseEntry, IncomeEntry


def expense_string(entry: ExpenseEntry) -> str:
    """Convert an expense into a single readable line.

    Some details such as regular, trip are omitted if none.
    """
    date = datetime.date.fromisoformat(entry.date)
    message = f'{date.strftime("%m/%d/%Y")} {entry.category} ${entry.cost} {entry.notes} '
    message += " "
    message += entry.regular
    if entry.trip != "":
        message += f" Trip: {entry.trip}"
    return message


def income_string(entry: IncomeEntry) -> str:
    """Convert an income into a single readable line."""
    date = datetime.date.fromisoformat(entry.date)
    return f'{date.strftime("%m/%d/%Y")} {entry.category} {entry.note} ${entry.amount}'


def expense_to_Qstring(expense_list: list[ExpenseEntry]) -> list[str]:
    """Convert ExpenseEntry items into strings for QListWidget (newest first)."""
    q_list = []
    for entry in expense_list:
        date = datetime.date.fromisoformat(entry.date)
        q_string = date.strftime("%m/%d/%Y")
        if entry.regular != "Regular":
            q_string += "   "
            q_string += entry.regular
        q_string += "\n$"
        q_string += f"{entry.cost:.2f}" + " " + entry.category + "\n"
        q_string += entry.notes["note"]
        q_list.insert(0, q_string)
    return q_list


def income_to_Qstring(income_list: list[IncomeEntry]) -> list[str]:
    """Convert IncomeEntry items into strings for QListWidget (newest first)."""
    q_list = []
    for entry in income_list:
        date = datetime.date.fromisoformat(entry.date)
        q_string = date.strftime("%m/%d/%Y") + "\n$"
        q_string += f"{entry.amount:.2f}" + " " + entry.category + "\n" + entry.note
        q_list.insert(0, q_string)
    return q_list


def get_trip_list(expense_list: list[ExpenseEntry]) -> list[str]:
    """Return the sorted, de-duplicated list of trip names used by the expenses."""
    trip_list = [entry.trip for entry in expense_list if entry.trip != ""]
    trip_list = list(set(trip_list))
    trip_list.sort()
    return trip_list
