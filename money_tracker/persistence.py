"""Loading and saving of the JSON files that hold the user's data."""
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from anytree import Node, PreOrderIter
from anytree.exporter import DictExporter, JsonExporter
from anytree.importer import JsonImporter

from .models import DEFAULT_CATEGORY_COLOR, ExpenseEntry, IncomeEntry

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


class DataFileError(RuntimeError):
    """A data file exists but can't be read."""


def _backup_folders() -> list[Path]:
    """Existing backup folders, oldest first (their names sort by time). Only
    folders named exactly like the ones backup_data_files() makes."""
    return sorted(
        path
        for path in BACKUP_PARENT.iterdir()
        if path.is_dir() and not path.is_symlink() and _BACKUP_NAME.fullmatch(path.name)
    )


def _unreadable_files(folder: Path) -> list[tuple[str, Exception]]:
    """The data files in `folder` that exist but can't be parsed."""
    loaders = {
        EXPENSES_FILE.name: load_expenses,
        INCOMES_FILE.name: load_incomes,
        EXPENSE_CATEGORIES_FILE.name: load_expense_categories,
        INCOME_CATEGORIES_FILE.name: load_income_categories,
    }
    unreadable = []
    for name, load in loaders.items():
        file = folder / name
        if file.exists():
            try:
                load(file)
            except Exception as error:
                unreadable.append((name, error))
    return unreadable


def check_data_files() -> None:
    """Stop, with a message saying how to recover, if a data file is damaged.

    Run before backing up, so a damaged file is never copied into a backup (and
    so never pushes the good backups out), and before the app overwrites it.
    """
    unreadable = _unreadable_files(DATA_DIR)
    if not unreadable:
        return
    problems = "\n".join(f"  {name}: {error}" for name, error in unreadable)
    newest_good = next(
        (folder for folder in reversed(_backup_folders()) if not _unreadable_files(folder)),
        None,
    )
    advice = (
        f"Your newest readable backup is {newest_good}.\n"
        f"To restore it, copy its files into {DATA_DIR}."
        if newest_good
        else "No readable backup was found."
    )
    raise DataFileError(
        f"Can't read your data in {DATA_DIR}:\n{problems}\n"
        f"No backup was made, so your existing backups are safe.\n{advice}"
    )


def _same_as_newest_backup(files: list[Path]) -> bool:
    backups = _backup_folders()
    if not backups:
        return False
    newest = backups[-1]
    data_names = {file.name for file in DATA_FILES}
    if {file.name for file in files} != {f.name for f in newest.iterdir() if f.name in data_names}:
        return False
    return all((newest / file.name).read_bytes() == file.read_bytes() for file in files)


def backup_data_files() -> Path | None:
    """Copy the data files in current/ into a new timestamped backup folder,
    then delete the oldest backups beyond MAX_BACKUPS.

    Nothing is done (None is returned) when there is nothing to back up yet, when
    a file is damaged (a bad copy must never replace a good backup), or when the
    files are the same as in the newest backup.
    """
    existing = [file for file in DATA_FILES if file.exists()]
    if not existing or _unreadable_files(DATA_DIR) or _same_as_newest_backup(existing):
        return None
    folder = BACKUP_PARENT / datetime.now().strftime("back_up_%Y-%m-%d_%H-%M-%S")
    folder.mkdir(exist_ok=True)
    for file in existing:
        shutil.copy2(file, folder)
    prune_backups()
    return folder


def prune_backups(keep: int = MAX_BACKUPS) -> None:
    """Delete the oldest backup folders so at most `keep` remain."""
    for old in _backup_folders()[:-keep]:
        shutil.rmtree(old)


def _stage(path: Path, text: str) -> Path:
    """Write `text` to a temp file next to `path` and return the temp file."""
    temp = Path(path).with_name(Path(path).name + ".tmp")
    try:
        with open(temp, "w", encoding="utf-8", newline="\n") as f:  # same on every OS
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return temp


def _write_atomically(files: dict[Path, str]) -> None:
    """Write several files so a crash, power loss or cloud sync never leaves a
    half-written one: every file is first written in full to a temp file, and
    only then are the temp files swapped in, back to back."""
    staged = []
    try:
        for path, text in files.items():
            staged.append((_stage(path, text), Path(path)))
        for temp, path in staged:
            os.replace(temp, path)
    finally:
        for temp, _ in staged:
            temp.unlink(missing_ok=True)  # Only what is left if something failed.


def default_expense_categories() -> Node:
    return Node("All Categories", notes=["note"], color=DEFAULT_CATEGORY_COLOR)


def default_income_categories() -> Node:
    return Node("All Income Types", color=DEFAULT_CATEGORY_COLOR)


def _with_colors(root: Node) -> Node:
    """Give every category without a colour (a file written before colours
    existed) the default one, so the rest of the app can rely on it."""
    for node in PreOrderIter(root):
        if not hasattr(node, "color"):
            node.color = DEFAULT_CATEGORY_COLOR
    return root


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
            return _with_colors(JsonImporter().read(f))
    except FileNotFoundError:
        return default_expense_categories()


def load_income_categories(path: Path = INCOME_CATEGORIES_FILE) -> Node:
    try:
        with open(path, "r") as f:
            return _with_colors(JsonImporter().read(f))
    except FileNotFoundError:
        return default_income_categories()


def _entries_text(entries) -> str:
    return json.dumps([vars(entry) for entry in entries], indent=4)


def _without_index(attributes):
    # `index` is the tree widget's back-pointer into its rows: it must stay on
    # the live nodes, so it is left out of the file instead of being deleted.
    return [(name, value) for name, value in attributes if name != "index"]


def _categories_text(tree: Node) -> str:
    exporter = JsonExporter(indent=2, dictexporter=DictExporter(attriter=_without_index))
    return exporter.export(tree)


def save_expenses(expense_list: list[ExpenseEntry], path: Path = EXPENSES_FILE) -> None:
    _write_atomically({path: _entries_text(expense_list)})


def save_incomes(income_list: list[IncomeEntry], path: Path = INCOMES_FILE) -> None:
    _write_atomically({path: _entries_text(income_list)})


def save_categories(tree: Node, path: Path) -> None:
    _write_atomically({path: _categories_text(tree)})


def save_all(
    expense_list: list[ExpenseEntry],
    income_list: list[IncomeEntry],
    expense_tree: Node,
    income_tree: Node,
) -> None:
    """Save the four data files together: all are written out before any is
    replaced, so a failure part-way leaves the files as they were."""
    _write_atomically(
        {
            EXPENSES_FILE: _entries_text(expense_list),
            INCOMES_FILE: _entries_text(income_list),
            EXPENSE_CATEGORIES_FILE: _categories_text(expense_tree),
            INCOME_CATEGORIES_FILE: _categories_text(income_tree),
        }
    )
