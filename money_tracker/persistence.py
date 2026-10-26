"""Loading and saving of the JSON files that hold the user's data."""
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from anytree import Node, PreOrderIter
from anytree.exporter import JsonExporter
from anytree.importer import JsonImporter

from .models import ExpenseEntry, IncomeEntry

PROJECT_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = PROJECT_DIR / "local_settings.json"  # per device, not committed
USER_DATA_ENV_VAR = "MONEY_TRACKER_USER_DATA"


def _find_user_data_dir() -> tuple[Path, str | None]:
    """Work out which user_data folder (the one holding current/ and the
    back_up_* folders) to use, so it can live in a cloud-synced folder.

    In order of priority: the MONEY_TRACKER_USER_DATA environment variable,
    then "user_data_dir" in local_settings.json, then <project>/user_data.
    Returns (folder, where it was set); the second part is None for the default.
    """
    where = None
    value = os.environ.get(USER_DATA_ENV_VAR)
    if value:
        where = f"the {USER_DATA_ENV_VAR} environment variable"
    elif SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if not isinstance(settings, dict):
                raise ValueError("expected a JSON object like {\"user_data_dir\": \"...\"}")
        except (OSError, ValueError) as error:  # JSONDecodeError is a ValueError
            raise RuntimeError(
                f"Could not read {SETTINGS_FILE}: {error}\n"
                'Write the path with forward slashes, e.g. "C:/Users/me/user_data" '
                "(or double every backslash)."
            ) from error
        value = settings.get("user_data_dir")
        where = SETTINGS_FILE.name
    if not value:
        return PROJECT_DIR / "user_data", None

    folder = Path(value).expanduser()
    if not folder.is_absolute():
        folder = PROJECT_DIR / folder
    return folder, where


USER_DATA_DIR, DATA_LOCATION_SOURCE = _find_user_data_dir()
USING_CUSTOM_LOCATION = DATA_LOCATION_SOURCE is not None
DATA_DIR = USER_DATA_DIR / "current"
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
BACKUP_PARENT = USER_DATA_DIR
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


def check_data_location() -> None:
    """With a custom (usually cloud-synced) data folder, stop unless all four
    data files are already there.

    Starting with an empty folder would create blank files that could clash with
    the real data once a sync catches up (a new device that hasn't finished
    downloading, a drive that isn't mounted, a mistyped path). The default
    location is not checked: there missing files are simply created.
    """
    if not USING_CUSTOM_LOCATION:
        return
    missing = [file.name for file in DATA_FILES if not file.exists()]
    if missing:
        raise FileNotFoundError(
            f"Can't find your data in {DATA_DIR} (folder set by {DATA_LOCATION_SOURCE}).\n"
            f"Missing: {', '.join(missing)}\n"
            "If this is a new device, wait for your sync to finish and try again. "
            "The app won't create empty files in a custom data folder."
        )


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
