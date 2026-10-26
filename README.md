Copyright (C) 2026 Hsing-Yi Lai

## About this project

A PyQt6 desktop app for tracking expenses and income. It is the GUI version of
<https://github.com/hsingyilai/expense-tracker>.

## Running

```
python -m pip install -r requirements.txt
python main_app.py
```

The app reads and writes four JSON files in `user_data/current/`:
`my_expenses.json`, `my_incomes.json`, `expense_categories.json`,
`income_categories.json`. A timestamped copy is made in `user_data/back_up_*`
at every start (the newest 10 are kept). See the link above for their format.

By default `user_data/` sits inside the project folder, and any missing folder
or file is created (empty) at startup.

### Keeping the data in a synced folder

To use the same data on several computers, keep `user_data/` in a folder your
sync service (Google Drive, OneDrive, Dropbox, ...) keeps up to date, and tell
each computer where it is. Create `local_settings.json` in the project folder
(it is not committed, since the path differs per computer):

```json
{
    "user_data_dir": "C:/Users/me/Google Drive/expense_data/user_data"
}
```

Use forward slashes, even on Windows. `~` and paths relative to the project
folder also work. The environment variable `MONEY_TRACKER_USER_DATA` overrides
the file.

With a custom folder the app never creates empty data files: if the folder or a
file is missing (a new computer that has not finished syncing, a mistyped path)
it stops with a message instead. Use the app on one computer at a time, and let
the sync finish before opening it on another.

## Layout

| Module | Responsibility |
| --- | --- |
| `money_tracker/models.py` | `ExpenseEntry` / `IncomeEntry` data classes |
| `money_tracker/persistence.py` | Loading and saving the JSON files |
| `money_tracker/formatting.py` | Turning entries into display strings |
| `money_tracker/styles.py` | Shared Qt stylesheet snippets |
| `money_tracker/category_tree.py` | `CategoryTree` widget mirroring an anytree tree |
| `money_tracker/graph_data.py` | Monthly totals behind the Graph page (no Qt) |
| `money_tracker/app.py` | Windows, navigation and the `main()` entry point |
| `main_app.py` | Thin launcher (`python main_app.py`) |

## License

This project is licensed under the GNU General Public License version 3 or later
(GPL-3.0-or-later). See the LICENSE file for the full license text.
