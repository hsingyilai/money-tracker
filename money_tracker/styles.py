"""Shared Qt stylesheet snippets, kept in one place so the look stays consistent."""

# Expense/Income toggle labels.
SWITCH_LABEL_ACTIVE = "background-color: #41e8a0;font-weight: bold;font-size: 20px;"
SWITCH_LABEL_INACTIVE = "background-color: #ecffe6;font-size: 16px;"

# The green page-title banner in the navigation bar.
NAV_TITLE_LABEL = "background-color: #41e8a0;font-weight: bold;font-size: 18px;"
NAV_BUTTON = "font-size: 18px;"

# The borderless slider look for the QCheckBox used as an on/off switch.
TOGGLE_CHECKBOX = """
    QCheckBox::indicator {
        width: 90px;
        height: 30px;
    }
    QCheckBox::indicator:checked {
        image: none;
        background-color: none;
        border: none;
    }
    QCheckBox::indicator:unchecked {
        background-color: none;
        border: none;
    }
"""

# Small secondary buttons (Add back / Delete / New Entry).
SMALL_BUTTON = """
    QPushButton {
        font-size: 16px;
        background-color: #f2f2f2;
        border: 1px solid #262626;
        border-radius: 10px;
    }
    QPushButton:hover {
        background-color: #c2c2c2;
    }
    QPushButton:pressed {
        background-color: #949494;
    }
"""

# The big primary Submit button.
SUBMIT_BUTTON = """
    QPushButton {
        font-size: 20px;
        background-color: #ecffe6;
        border: 2px solid #0e4708;
        border-radius: 10px;
    }
    QPushButton:hover {
        background-color: #bffabe;
    }
    QPushButton:pressed {
        background-color: #0b4d0a;
    }
"""

LIST_WIDGET = """
    QListWidget {
        font-size: 18px;
    }
    QListWidget::item {
        border-bottom: 2px solid gray;
        padding: 5px;
    }
    QListWidget::item:selected {
        background: #589453;
        border: 2px solid #2b4d28;
    }
"""
