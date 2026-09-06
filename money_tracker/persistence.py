"""Loading and saving of the JSON files that hold the user's data."""
import json

from anytree import Node, PreOrderIter
from anytree.exporter import JsonExporter
from anytree.importer import JsonImporter

from .models import ExpenseEntry, IncomeEntry

EXPENSES_FILE = "my_expenses.json"
INCOMES_FILE = "my_incomes.json"
EXPENSE_CATEGORIES_FILE = "expense_categories.json"
INCOME_CATEGORIES_FILE = "income_categories.json"


def load_expenses(path: str = EXPENSES_FILE) -> list[ExpenseEntry]:
    try:
        with open(path, "r") as f:
            return [ExpenseEntry(**entry) for entry in json.load(f)]
    except FileNotFoundError:
        return []


def load_incomes(path: str = INCOMES_FILE) -> list[IncomeEntry]:
    try:
        with open(path, "r") as f:
            return [IncomeEntry(**entry) for entry in json.load(f)]
    except FileNotFoundError:
        return []


def load_expense_categories(path: str = EXPENSE_CATEGORIES_FILE) -> Node:
    try:
        with open(path, "r") as f:
            return JsonImporter().read(f)
    except FileNotFoundError:
        return Node("All Categories", notes=["note"])


def load_income_categories(path: str = INCOME_CATEGORIES_FILE) -> Node:
    try:
        with open(path, "r") as f:
            return JsonImporter().read(f)
    except FileNotFoundError:
        return Node("All Income Types")


def save_expenses(expense_list: list[ExpenseEntry], path: str = EXPENSES_FILE) -> None:
    with open(path, "w") as f:
        json.dump([vars(entry) for entry in expense_list], f, indent=4)


def save_incomes(income_list: list[IncomeEntry], path: str = INCOMES_FILE) -> None:
    with open(path, "w") as f:
        json.dump([vars(entry) for entry in income_list], f, indent=4)


def save_categories(tree: Node, path: str) -> None:
    """Write a category tree to disk, dropping the transient ``index`` pointer
    the widgets attach to each node."""
    for node in PreOrderIter(tree):
        if hasattr(node, "index"):
            del node.index
    with open(path, "w") as f:
        f.write(JsonExporter(indent=2).export(tree))
