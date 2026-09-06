Copyright (C) 2026 Hsing-Yi Lai

## About this project

A PyQt6 desktop app for tracking expenses and income. It is the GUI version of
<https://github.com/hsingyilai/expense-tracker>.

## Running

```
python -m pip install -r requirements.txt
python main_app.py
```

The app reads and writes four JSON files in the working directory:
`my_expenses.json`, `my_incomes.json`, `expense_categories.json`,
`income_categories.json`. Missing files are created on first exit. See the link
above for their format.

## Layout

| Module | Responsibility |
| --- | --- |
| `money_tracker/models.py` | `ExpenseEntry` / `IncomeEntry` data classes |
| `money_tracker/persistence.py` | Loading and saving the JSON files |
| `money_tracker/formatting.py` | Turning entries into display strings |
| `money_tracker/styles.py` | Shared Qt stylesheet snippets |
| `money_tracker/category_tree.py` | `CategoryTree` widget mirroring an anytree tree |
| `money_tracker/app.py` | Windows, navigation and the `main()` entry point |
| `main_app.py` | Thin launcher (`python main_app.py`) |

## License

This project is licensed under the GNU General Public License version 3 or later
(GPL-3.0-or-later). See the LICENSE file for the full license text.
