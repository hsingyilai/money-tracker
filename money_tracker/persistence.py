"""Loading and saving of the JSON files that hold the user's data."""
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from anytree import Node, PreOrderIter
from anytree.exporter import JsonExporter
from anytree.importer import JsonImporter

from .models import ExpenseEntry, IncomeEntry

# Anchored to the project folder (the parent of this package) so the data is
# found wherever the app is launched from.
DATA_DIR = Path(__file__).resolve().parent.parent / "user_data" / "current"
EXPENSES_FILE = DATA_DIR / "my_expenses.json"
INCOMES_FILE = DATA_DIR / "my_incomes.json"
EXPENSE_CATEGORIES_FILE = DATA_DIR / "expense_categories.json"
INCOME_CATEGORIES_FILE = DATA_DIR / "income_categories.json"
DATA_FILES = (
    EXPENSES_FILE,
    INCOMES_FILE,
    EXPENSE_CATEGORIES_FILE,
    INCOME_CATEGORIES_FILE,
)

# Backups sit next to current/ as user_data/back_up_<date>_<time>.
BACKUP_PARENT = DATA_DIR.parent
MAX_BACKUPS = 10
_BACKUP_NAME = re.compile(r"back_up_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}")


def backup_data_files() -> Path | None:
    """Copy the data files in current/ into a new timestamped backup folder,
    then delete the oldest backups beyond MAX_BACKUPS.

    Returns the new folder, or None when there is nothing to back up yet.
    """
    existing = [file for file in DATA_FILES if file.exists()]
    if not existing:
        return None
    folder = BACKUP_PARENT / datetime.now().strftime("back_up_%Y-%m-%d_%H-%M-%S")
    folder.mkdir(exist_ok=True)
    for file in existing:
        shutil.copy2(file, folder)
    prune_backups()
    return folder


def prune_backups(keep: int = MAX_BACKUPS) -> None:
    """Delete the oldest backup folders so at most `keep` remain. Only folders
    named exactly like the ones backup_data_files() makes are ever touched."""
    backups = sorted(
        path
        for path in BACKUP_PARENT.iterdir()
        if path.is_dir() and not path.is_symlink() and _BACKUP_NAME.fullmatch(path.name)
    )
    for old in backups[:-keep]:
        shutil.rmtree(old)


def default_expense_categories() -> Node:
    return Node("All Categories", notes=["note"])


def default_income_categories() -> Node:
    return Node("All Income Types")


def ensure_data_files() -> None:
    """Create user_data/current and any missing data file with empty defaults."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not EXPENSES_FILE.exists():
        save_expenses([])
    if not INCOMES_FILE.exists():
        save_incomes([])
    if not EXPENSE_CATEGORIES_FILE.exists():
        save_categories(default_expense_categories(), EXPENSE_CATEGORIES_FILE)
    if not INCOME_CATEGORIES_FILE.exists():
        save_categories(default_income_categories(), INCOME_CATEGORIES_FILE)


def load_expenses(path: Path = EXPENSES_FILE) -> list[ExpenseEntry]:
    try:
        with open(path, "r") as f:
            entries = [ExpenseEntry(**entry) for entry in json.load(f)]
    except FileNotFoundError:
        return []
    entries.sort(key=lambda entry: entry.date)
    return entries


def load_incomes(path: Path = INCOMES_FILE) -> list[IncomeEntry]:
    try:
        with open(path, "r") as f:
            entries = [IncomeEntry(**entry) for entry in json.load(f)]
    except FileNotFoundError:
        return []
    entries.sort(key=lambda entry: entry.date)
    return entries


def load_expense_categories(path: Path = EXPENSE_CATEGORIES_FILE) -> Node:
    try:
        with open(path, "r") as f:
            return JsonImporter().read(f)
    except FileNotFoundError:
        return default_expense_categories()


def load_income_categories(path: Path = INCOME_CATEGORIES_FILE) -> Node:
    try:
        with open(path, "r") as f:
            return JsonImporter().read(f)
    except FileNotFoundError:
        return default_income_categories()


def save_expenses(expense_list: list[ExpenseEntry], path: Path = EXPENSES_FILE) -> None:
    with open(path, "w") as f:
        json.dump([vars(entry) for entry in expense_list], f, indent=4)


def save_incomes(income_list: list[IncomeEntry], path: Path = INCOMES_FILE) -> None:
    with open(path, "w") as f:
        json.dump([vars(entry) for entry in income_list], f, indent=4)


def save_categories(tree: Node, path: Path) -> None:
    """Write a category tree to disk, dropping the transient ``index`` pointer
    the widgets attach to each node."""
    for node in PreOrderIter(tree):
        if hasattr(node, "index"):
            del node.index
    with open(path, "w") as f:
        f.write(JsonExporter(indent=2).export(tree))
