import copy
import datetime
import math
import re
import sys

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QAbstractItemView,
    QCalendarWidget,
    QLabel,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QFormLayout,
    QStackedWidget,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QSpinBox,
    QStyleFactory,
)
from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDoubleValidator, QPalette
from anytree import Node, PreOrderIter, PostOrderIter
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from pint import UnitRegistry

from . import graph_data, persistence, styles
from .category_tree import CategoryTree
from .models import ExpenseEntry, IncomeEntry
from .formatting import (
    expense_to_Qstring,
    income_to_Qstring,
    expense_string,
    get_trip_list,
    insort_by_date,
)

ureg = UnitRegistry()
Q_ = ureg.Quantity

# Categories with this note get a price-per-pound comparison in the summary,
# which needs the value to be a positive weight Pint can convert to pounds.
WEIGHT_NOTE = "quantity (weight)"


def parse_weight_lb(text: str) -> float | None:
    """Return text (e.g. "2 lb", "500 g") as a positive number of pounds, or
    None if Pint can't read it, it isn't a weight, or it isn't greater than 0."""
    try:
        magnitude = Q_(text).to("lb").magnitude
    except Exception:  # Pint raises several error types for unreadable input.
        return None
    if not math.isfinite(magnitude) or magnitude <= 0:
        return None
    return magnitude


# Matches the `regular` values written by list_add() for "Every X months"
# (X being any integer), and nothing else - not "Regular", "Irregular", or
# "Regular but not monthly".
PERIODIC_REGEX = re.compile(r"^Every \d+ months$")


# Define a QDate object for today.
date_now = datetime.datetime.now()
qtoday = QDate(date_now.year, date_now.month, date_now.day)

# App-wide data. Populated by load_data() before the main window is built.
expense_list: list[ExpenseEntry] = []
income_list: list[IncomeEntry] = []
expense_type: Node = Node("All Categories", notes=["note"])
income_type: Node = Node("All Income Types")
trip_list: list[str] = []

# Stores the removed entries as a stack of ExpenseEntry or IncomeEntry
removed_expense = []
removed_income = []


def load_data():
    """Read the user's data files into the module-level state."""
    global expense_list, income_list, expense_type, income_type, trip_list
    persistence.check_data_location()
    persistence.backup_data_files()
    persistence.ensure_data_files()
    expense_list = persistence.load_expenses()
    income_list = persistence.load_incomes()
    expense_type = persistence.load_expense_categories()
    income_type = persistence.load_income_categories()
    trip_list = get_trip_list(expense_list)


def save_data():
    """Write the module-level state back to the user's data files."""
    persistence.save_expenses(expense_list)
    persistence.save_incomes(income_list)
    persistence.save_categories(expense_type, persistence.EXPENSE_CATEGORIES_FILE)
    persistence.save_categories(income_type, persistence.INCOME_CATEGORIES_FILE)


# Main Window
PAGES = ["Input", "Categories", "Summary", "Periodic Expenses", "Graph"]

# Horizontal shift applied to the Input page so the widened window grows
# to the left of the centred input fields.
INPUT_SHIFT = 263


class NavBar(QWidget):
    """The bottom bar of page buttons. Emits navigate(name) when one is clicked."""

    navigate = pyqtSignal(str)

    def __init__(self, pages):
        super().__init__()
        self._buttons = {}
        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(0, 0, 0, 0)
        for name in pages:
            button = QPushButton(name)
            button.clicked.connect(lambda _, n=name: self.navigate.emit(n))
            hbox.addWidget(button)
            self._buttons[name] = button
        self.set_active(pages[0])

    def set_active(self, active_name):
        for name, button in self._buttons.items():
            if name == active_name:
                button.setStyleSheet(styles.NAV_TITLE_LABEL)
                button.setFixedHeight(60)
            else:
                button.setStyleSheet(styles.NAV_BUTTON)
                button.setFixedHeight(50)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.pages = QStackedWidget()
        self._page_by_name = {
            "Input": InputWindow(),
            "Categories": CategoriesWindow(),
            "Summary": SummaryWindow(),
            "Periodic Expenses": PeriodicWindow(),
            "Graph": GraphWindow(),
        }
        for widget in self._page_by_name.values():
            self.pages.addWidget(widget)

        self.nav = NavBar(PAGES)
        self.nav.navigate.connect(self.show_page)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.pages, stretch=12)
        vbox.addWidget(self.nav, stretch=1)

    def show_page(self, name):
        page = self._page_by_name[name]
        self.pages.setCurrentWidget(page)
        self.nav.set_active(name)

        # Per-page refresh when it comes to the front.
        if name == "Input":
            page.refresh()
        elif name == "Categories":
            page.reload_categories()
        elif name == "Summary":
            page.load_options(page.summary_type.currentText())
        elif name == "Periodic Expenses":
            page.refresh()
        elif name == "Graph":
            page.refresh()

    def closeEvent(self, event):
        save_data()
        event.accept()
        super().closeEvent(event)


# Custom widgets for stacked child-windows in the main window.
class ScrollableFormApp(QWidget):
    def __init__(self):
        super().__init__()

        # Create the Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(
            True
        )  # Essential to let the inner widget resize properly.

        # Create a container widget for the form contents.
        form_content = QWidget()
        self.form_layout = QFormLayout(form_content)

        # Set the container widget into the scroll area.
        scroll.setWidget(form_content)

        # Set the scroll area as the main window layout.
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

    def assign_content(self, label_list: list[str]):  # Assign the labels.
        # Clear the notes.
        while self.form_layout.count():
            self.form_layout.removeRow(0)

        self.init_add_note()

        # Add the notes.
        for text in label_list:
            label = QLabel(text)
            label.setStyleSheet("font-size: 16px;")
            entry = QLineEdit()
            entry.setStyleSheet("font-size: 16px;")
            self.form_layout.addRow(label, entry)

    def values(self) -> dict:
        """Return the form as a {label: text} mapping (the inverse of fill_values)."""
        result = {}
        for row in range(self.form_layout.rowCount()):
            label_item = self.form_layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
            field_item = self.form_layout.itemAt(row, QFormLayout.ItemRole.FieldRole)
            result[label_item.widget().text()] = field_item.widget().text()
        return result

    def fill_values(self, values: dict) -> None:
        """Fill the note fields from a {label: value} mapping.

        Labels with no matching key are cleared, and keys with no matching
        field are ignored - the same rule ``list_add`` uses when reading
        the form back.
        """
        for row in range(self.form_layout.rowCount()):
            label_item = self.form_layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
            field_item = self.form_layout.itemAt(row, QFormLayout.ItemRole.FieldRole)
            if label_item is None or field_item is None:
                continue
            field = field_item.widget()
            if isinstance(field, QLineEdit):
                field.setText(str(values.get(label_item.widget().text(), "")))

    def init_add_note(self):
        # For adding new notes for new subcategory
        self.new_note = QLineEdit()
        self.new_note.setStyleSheet("font-size: 16px;")
        self.new_note.setPlaceholderText("new note")
        self.new_note.setVisible(False)
        self.new_note.textChanged.connect(self.can_add_new_note)

        self.button_add = QPushButton("+")
        self.button_add.setStyleSheet("font-size: 16px;")
        self.button_add.setEnabled(False)
        self.button_add.setVisible(False)
        self.button_add.clicked.connect(self.add_new_note)

    def enable_button(self):  # Show a button for adding new notes
        last_index = self.form_layout.rowCount() - 1
        if not isinstance(
            self.form_layout.itemAt(
                last_index, QFormLayout.ItemRole.LabelRole
            ).widget(),
            QLineEdit,
        ):
            # Clear the notes.
            while self.form_layout.count():
                self.form_layout.removeRow(0)

            label = QLabel("note")
            label.setStyleSheet("font-size: 16px;")
            entry = QLabel("")
            entry.setStyleSheet("font-size: 16px;")
            self.form_layout.addRow(label, entry)

            self.new_note.setVisible(True)
            self.button_add.setVisible(True)
            self.form_layout.addRow(self.new_note, self.button_add)

    def can_add_new_note(self):
        if self.new_note.text() == "":
            self.button_add.setEnabled(False)
        else:
            self.button_add.setEnabled(True)

    def add_new_note(self):
        label = QLabel(self.new_note.text())
        label.setStyleSheet("font-size: 16px;")
        entry = QLabel("")
        entry.setStyleSheet("font-size: 16px;")
        last_index = self.form_layout.rowCount() - 1
        self.form_layout.insertRow(last_index, label, entry)
        self.new_note.clear()


# The stacked child-windows.
class InputWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()
        self.expense_mode = True

    @property
    def index_selected(self):
        """Row of the entry highlighted on the list, or None.

        Read from the list itself rather than cached, so it can't go stale when
        rows are inserted (Add back, Submit) or the selection is cleared.
        """
        items = self.list.selectedItems()
        return self.list.row(items[0]) if items else None

    def initUI(self):
        # The input-field column and the entry list are positioned relative
        # to these anchors so the window can be widened by moving them.
        self.switch_x = 40 + INPUT_SHIFT
        self.list_x = 380 + INPUT_SHIFT
        self.switch_y = 30
        self.init_expense_income_switch()
        self.init_select_date()
        self.init_amount()
        self.init_irregular()
        self.init_category_tree()
        self.init_add_subcategory()
        self.init_notes()
        self.init_select_trip()
        self.init_button_submit()
        self.init_list()

    def init_expense_income_switch(self):
        self.label_switch_expense = QLabel("Expense", self)
        self.label_switch_expense.setGeometry(self.switch_x, self.switch_y, 230, 40)
        self.label_switch_expense.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_switch_expense.setStyleSheet(styles.SWITCH_LABEL_ACTIVE)

        self.label_switch_income = QLabel("Income", self)
        self.label_switch_income.setGeometry(self.switch_x + 230, self.switch_y, 95, 30)
        self.label_switch_income.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_switch_income.setStyleSheet(styles.SWITCH_LABEL_INACTIVE)

        self.switch = QCheckBox("", self)
        self.switch.setGeometry(self.switch_x + 230, self.switch_y, 95, 30)
        self.switch.setStyleSheet(styles.TOGGLE_CHECKBOX)

        self.switch.stateChanged.connect(self.switch_change)

    def switch_change(self, state):
        if Qt.CheckState(state) == Qt.CheckState.Checked:  # Income mode.
            self.switch.setGeometry(self.switch_x, self.switch_y, 95, 30)
            self.label_switch_expense.setStyleSheet(
                "background-color: #ecffe6;font-size: 16px;"
            )
            self.label_switch_expense.setGeometry(self.switch_x, self.switch_y, 95, 30)

            self.label_switch_income.setStyleSheet(
                "background-color: #41e8a0;font-weight: bold;font-size: 20px;"
            )
            self.label_switch_income.setGeometry(
                self.switch_x + 95, self.switch_y, 230, 40
            )
            self.list.clear()
            self.list.addItems(income_to_Qstring(income_list))
            self.expense_mode = False
            self.income_tree.setVisible(True)
            self.expense_tree.setVisible(False)
            self.label_amount.setText("Income:   $")
            self.irregular.setVisible(False)
            self.expense_notes.setVisible(False)
            self.label_income_note.setVisible(True)
            self.income_note_entry.setVisible(True)
            self.trip_selector.setVisible(False)
            if len(removed_income) == 0:
                self.button_add_back.setDisabled(True)
            else:
                self.button_add_back.setDisabled(False)
        else:  # Expense mode.
            self.switch.setGeometry(self.switch_x + 230, self.switch_y, 95, 30)
            self.label_switch_expense.setStyleSheet(
                "background-color: #41e8a0;font-weight: bold;font-size: 20px;"
            )
            self.label_switch_expense.setGeometry(self.switch_x, self.switch_y, 230, 40)

            self.label_switch_income.setStyleSheet(
                "background-color: #ecffe6;font-size: 16px;"
            )
            self.label_switch_income.setGeometry(
                self.switch_x + 230, self.switch_y, 95, 30
            )
            self.list.clear()
            self.list.addItems(expense_to_Qstring(expense_list))
            self.expense_mode = True
            self.income_tree.setVisible(False)
            self.expense_tree.setVisible(True)
            self.label_amount.setText("Expense: $")
            self.irregular.setVisible(True)
            self.expense_notes.setVisible(True)
            self.label_income_note.setVisible(False)
            self.income_note_entry.setVisible(False)
            self.trip_selector.setVisible(True)
            if len(removed_expense) == 0:
                self.button_add_back.setDisabled(True)
            else:
                self.button_add_back.setDisabled(False)

        # A name typed before switching has to be checked against the other
        # mode's categories.
        self.update_add_category_button()

    def init_select_date(self):
        # A click-to-pick calendar living in the empty space to the left of
        # the input-field column. It replaces the old QDateEdit; the spot the
        # QDateEdit used to sit in (self.switch_x + 50, 80) is left empty.
        self.calender = QCalendarWidget(self)
        self.calender.setGeometry(12, 78, self.switch_x - 24, 200)
        self.calender.setGridVisible(True)
        self.calender.setSelectedDate(qtoday)
        self._recolor_calendar_selection()

        self.label_date = QLabel("Date:", self)
        self.label_date.setGeometry(12, 35, 50, 40)
        self.label_date.setStyleSheet("font-size: 20px;")

        self.button_today = QPushButton("Today", self)
        self.button_today.setGeometry(210, 35, 70, 40)
        self.button_today.setStyleSheet("font-size: 16px;")

        self.button_today.clicked.connect(self.set_today)

    def _recolor_calendar_selection(self):
        """Make the selected day green (matching the entry list) instead of
        the default grey.

        The native Windows 11 style paints the selected cell itself and
        ignores both a stylesheet and a palette override, so switch the
        calendar to the Fusion style (which honours them) and then set the
        green via the inner view's palette and stylesheet.
        """
        view = self.calender.findChild(QAbstractItemView, "qt_calendar_calendarview")
        if view is None:
            return

        # Kept as an attribute so the QStyle object outlives this call.
        self._calendar_style = QStyleFactory.create("Fusion")
        if self._calendar_style is not None:
            view.setStyle(self._calendar_style)

        view.setStyleSheet(styles.CALENDAR_VIEW)
        palette = view.palette()
        palette.setColor(QPalette.ColorRole.Highlight, QColor(styles.SELECTION_GREEN))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
        view.setPalette(palette)

    def set_today(self):
        self.calender.setSelectedDate(qtoday)

    def init_amount(self):
        self.label_amount = QLabel("Expense: $", self)
        self.label_amount.setGeometry(self.switch_x, 85, 100, 35)
        self.label_amount.setStyleSheet("font-size: 20px;")

        self.amount = QLineEdit(self)
        self.amount.setGeometry(self.switch_x + 100, 83, 110, 40)
        self.amount.setPlaceholderText("0.00")
        self.amount.setStyleSheet("font-size: 20px;")
        validator = QDoubleValidator(0.00, 999999.99, 2, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.amount.setValidator(validator)

    def init_irregular(self):
        self.irregular = QComboBox(self)
        self.irregular.setGeometry(self.switch_x + 220, 78, 110, 40)
        self.irregular.setStyleSheet("font-size: 18px;")
        self.irregular.addItem("Regular")
        self.irregular.addItem("Irregular")
        self.irregular.addItem("Regular but not monthly")
        self.irregular.setPlaceholderText("period")

        self.irregular.activated.connect(self.irregular_clicked)

        self.spin_period = QSpinBox(self)
        # Windows draws wider up/down buttons and right-aligns the text, so a
        # 50px box hides the digits behind the buttons. Give it more room and
        # left-align the number.
        self.spin_period.setGeometry(self.switch_x + 210, 105, 80, 30)
        self.spin_period.setStyleSheet("font-size: 12px;")
        self.spin_period.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.spin_period.setMinimum(2)
        self.spin_period.setMaximum(999)
        self.spin_period.setVisible(False)
        self.label_month = QLabel("months", self)
        self.label_month.setGeometry(self.switch_x + 291, 108, 44, 28)
        self.label_month.setStyleSheet("font-size: 13px;")
        self.label_month.setVisible(False)

    def irregular_clicked(self, index):
        if index == 2:
            self.irregular.setGeometry(self.switch_x + 220, 73, 110, 40)
            self.irregular.removeItem(2)
            self.irregular.setCurrentIndex(-1)
            self.spin_period.setVisible(True)
            self.label_month.setVisible(True)
        else:
            self.irregular.setGeometry(self.switch_x + 220, 78, 110, 40)
            self.irregular.setEditable(False)
            self.spin_period.setVisible(False)
            self.label_month.setVisible(False)
            if self.irregular.count() == 2:
                self.irregular.addItem("Regular but not monthly")

    def init_category_tree(self):
        geometry = (self.switch_x, self.switch_y + 103, 324, 210)

        self.expense_tree = CategoryTree(expense_type, self)
        self.expense_tree.setGeometry(*geometry)
        self.expense_tree.currentItemChanged.connect(self.load_notes)

        self.income_tree = CategoryTree(income_type, self)
        self.income_tree.setGeometry(*geometry)
        self.income_tree.setVisible(False)
        self.income_tree.currentItemChanged.connect(self.load_notes)

    def load_notes(self, previous):
        self.new_category.clear()
        self.add_category.setEnabled(False)
        if self.expense_mode:
            node = self.expense_tree.current_node()
            if node is not None and hasattr(node, "notes"):
                self.expense_notes.assign_content(node.notes)

    def init_add_subcategory(self):
        self.new_category = QLineEdit(self)
        self.new_category.setStyleSheet("font-size: 16px;")
        self.new_category.setGeometry(self.switch_x, self.switch_y + 320, 200, 30)
        self.new_category.setPlaceholderText("new subcategory")
        self.add_category = QPushButton("Add", self)
        self.add_category.setStyleSheet("font-size: 16px;")
        self.add_category.setEnabled(False)
        self.add_category.setGeometry(self.switch_x + 210, self.switch_y + 315, 114, 40)

        self.new_category.textChanged.connect(self.entering_category)
        self.add_category.clicked.connect(self.add_new_category)

    def update_add_category_button(self):
        """Enable "Add" only for a non-empty name no existing category has."""
        tree = self.expense_tree if self.expense_mode else self.income_tree
        name = self.new_category.text()
        self.add_category.setEnabled(name != "" and not tree.has_name(name))

    def entering_category(self):
        self.update_add_category_button()

        if self.expense_mode:
            self.expense_notes.enable_button()

    def add_new_category(self):
        self.add_category.setEnabled(False)

        # Update the anytree category tree (and the widget mirroring it).
        if self.expense_mode:
            current_category = self.expense_tree.current_node()
            notes_list = [
                self.expense_notes.form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
                .widget()
                .text()
                for i in range(0, self.expense_notes.form_layout.rowCount() - 1)
            ]
            new_node = self.expense_tree.add_child(
                current_category, self.new_category.text(), notes=notes_list
            )
            self.expense_notes.assign_content(new_node.notes)
        else:
            current_category = self.income_tree.current_node()
            self.income_tree.add_child(current_category, self.new_category.text())

        self.new_category.clear()

    def init_notes(self):
        self.expense_notes = ScrollableFormApp()
        self.expense_notes.setParent(self)
        self.expense_notes.setGeometry(
            self.switch_x - 12, self.switch_y + 345, 348, 130
        )
        self.expense_notes.assign_content(expense_type.notes)

        self.label_income_note = QLabel("Note:", self)
        self.label_income_note.setStyleSheet("font-size: 18px;")
        self.label_income_note.setGeometry(self.switch_x, self.switch_y + 355, 100, 50)
        self.income_note_entry = QLineEdit(self)
        self.income_note_entry.setGeometry(self.switch_x, self.switch_y + 400, 324, 50)
        self.income_note_entry.setStyleSheet("font-size: 18px;")
        self.label_income_note.setVisible(False)
        self.income_note_entry.setVisible(False)

    def init_select_trip(self):
        self.trip_selector = QComboBox(self)
        self.trip_selector.setGeometry(self.switch_x, 495, 330, 35)
        self.trip_selector.setStyleSheet("font-size: 16px;")

        # Change this placeholder code
        self.trip_selector.addItems(trip_list)

        self.trip_selector.setEditable(True)
        self.trip_selector.setCurrentIndex(-1)
        self.trip_selector.lineEdit().setPlaceholderText("Link to a trip")

    def init_button_submit(self):
        self.button_submit = QPushButton("Submit", self)
        self.button_submit.setGeometry(self.switch_x, 535, 325, 50)
        self.button_submit.setStyleSheet(styles.SUBMIT_BUTTON)

        self.button_submit.clicked.connect(self.submit_entry)

    def weight_note_is_valid(self) -> bool:
        """If the selected expense category tracks a weight, check that the
        entered weight is something the summary can use. Prints a warning and
        returns False if not."""
        if not self.expense_mode:
            return True
        node = self.expense_tree.current_node()
        if node is None or WEIGHT_NOTE not in getattr(node, "notes", []):
            return True
        text = self.expense_notes.values().get(WEIGHT_NOTE, "")
        if parse_weight_lb(text) is not None:
            return True
        print(
            f'Warning: entry not submitted. "{WEIGHT_NOTE}" must be a weight '
            f'with units, such as "2 lb" or "500 g" (got {text!r}).'
        )
        return False

    def submit_entry(self):
        if not self.weight_note_is_valid():
            return
        list_add(self)
        self.amount.clear()
        # Clear the note text for the next entry: always in income mode, and in
        # expense mode only if the category has just one note.
        if self.expense_mode:
            node = self.expense_tree.current_node()
            if node is not None and len(getattr(node, "notes", [])) == 1:
                self.expense_notes.fill_values({})  # no values -> every field blanked
        else:
            self.income_note_entry.clear()
        # update trip list
        selected_trip = self.trip_selector.currentText()
        if selected_trip in trip_list:
            pass
        elif selected_trip != "":
            self.trip_selector.addItem(selected_trip)
            trip_list.append(selected_trip)
            trip_list.sort()
        self.list.clearSelection()

    def init_list(self):
        self.label_find = QLabel("Find:", self)
        self.label_find.setGeometry(self.list_x, 30, 40, 30)
        self.label_find.setStyleSheet("font-size: 18px;")

        self.text_find = QLineEdit(self)
        self.text_find.setGeometry(self.list_x + 45, 30, 285, 30)
        self.text_find.setStyleSheet("font-size: 18px;")
        self.text_find.textChanged.connect(self.filter_list)

        self.list = QListWidget(self)
        self.list.setGeometry(self.list_x, 65, 330, 475)
        self.list.addItems(expense_to_Qstring(expense_list))
        self.list.setStyleSheet(styles.LIST_WIDGET)
        self.list.itemClicked.connect(self.list_clicked)

        self.button_add_back = QPushButton("Add back", self)
        self.button_add_back.setStyleSheet(styles.SMALL_BUTTON)
        self.button_add_back.setGeometry(self.list_x + 5, 550, 100, 30)
        self.button_add_back.setDisabled(True)
        self.button_add_back.clicked.connect(self.add_back)

        self.button_delete = QPushButton("Delete", self)
        self.button_delete.setStyleSheet(styles.SMALL_BUTTON)
        self.button_delete.setGeometry(self.list_x + 115, 550, 100, 30)
        self.button_delete.setDisabled(True)
        self.button_delete.clicked.connect(self.delete_entry)
        # Delete is enabled exactly while an entry is highlighted.
        self.list.itemSelectionChanged.connect(self.update_delete_button)

        self.button_new_entry = QPushButton("New Entry", self)
        self.button_new_entry.setStyleSheet(styles.SMALL_BUTTON)
        self.button_new_entry.setGeometry(self.list_x + 225, 550, 100, 30)
        self.button_new_entry.clicked.connect(self.new_entry)

    def update_delete_button(self):
        self.button_delete.setEnabled(self.index_selected is not None)

    def list_clicked(self, item):
        row = self.list.row(item)
        if self.expense_mode:
            selected_entry = expense_list[len(expense_list) - 1 - row]
            self.calender.setSelectedDate(
                QDate.fromString(selected_entry.date, "yyyy-MM-dd")
            )
            self.amount.setText(str(selected_entry.cost))
            match selected_entry.regular:
                case "Regular":
                    self.irregular.setGeometry(self.switch_x + 220, 78, 110, 40)
                    self.irregular.setEditable(False)
                    self.spin_period.setVisible(False)
                    self.label_month.setVisible(False)
                    if self.irregular.count() == 2:
                        self.irregular.addItem("Regular but not monthly")
                    self.irregular.setCurrentIndex(0)
                case "Irregular":
                    self.irregular.setGeometry(self.switch_x + 220, 78, 110, 40)
                    self.irregular.setEditable(False)
                    self.spin_period.setVisible(False)
                    self.label_month.setVisible(False)
                    if self.irregular.count() == 2:
                        self.irregular.addItem("Regular but not monthly")
                    self.irregular.setCurrentIndex(1)
                case _:
                    self.irregular.setGeometry(self.switch_x + 220, 73, 110, 40)
                    self.irregular.removeItem(2)
                    self.irregular.setCurrentIndex(-1)
                    self.spin_period.setVisible(True)
                    self.label_month.setVisible(True)
                    # selected_entry.regular has the form "Every X months".
                    try:
                        self.spin_period.setValue(
                            int(selected_entry.regular.split()[1])
                        )
                    except (IndexError, ValueError):
                        pass
            self.expense_tree.select_by_name(selected_entry.category)
            # Auto-fill the note fields from the selected entry. Rebuild the
            # rows for the entry's category first so any leftover edits are
            # cleared, then drop in the stored values.
            node = self.expense_tree.current_node()
            if node is not None and hasattr(node, "notes"):
                self.expense_notes.assign_content(node.notes)
            self.expense_notes.fill_values(selected_entry.notes)

            self.trip_selector.setCurrentIndex(-1)
            for i in range(self.trip_selector.count()):
                if self.trip_selector.itemText(i) == selected_entry.trip:
                    self.trip_selector.setCurrentIndex(i)
        else:
            selected_entry = income_list[len(income_list) - 1 - row]
            self.calender.setSelectedDate(
                QDate.fromString(selected_entry.date, "yyyy-MM-dd")
            )
            self.amount.setText(str(selected_entry.amount))
            self.income_tree.select_by_name(selected_entry.category)
            self.income_note_entry.setText(selected_entry.note)

    def new_entry(self):
        self.list.clearSelection()
        self.trip_selector.setCurrentIndex(-1)
        self.amount.clear()

        # Clear the note fields but keep the selected category: rebuilding
        # the rows for the current category gives blank fields.
        node = self.expense_tree.current_node()
        if node is not None and hasattr(node, "notes"):
            self.expense_notes.assign_content(node.notes)
        self.income_note_entry.clear()

        # Reset the period selector back to "Regular".
        self.irregular.setGeometry(self.switch_x + 220, 78, 110, 40)
        self.irregular.setEditable(False)
        self.spin_period.setVisible(False)
        self.label_month.setVisible(False)
        if self.irregular.count() == 2:
            self.irregular.addItem("Regular but not monthly")
        self.irregular.setCurrentIndex(0)

    def delete_entry(self):
        if self.index_selected is None:
            return
        list_remove(self)
        self.list.clearSelection()
        self.button_add_back.setDisabled(False)

    def add_back(self):
        if self.expense_mode:
            entry = removed_expense.pop(-1)
            index = insort_by_date(expense_list, entry)
            q_list_entry = expense_to_Qstring([entry])
            display_index = len(expense_list) - 1 - index
            if len(removed_expense) == 0:
                self.button_add_back.setDisabled(True)
        else:
            entry = removed_income.pop(-1)
            index = insort_by_date(income_list, entry)
            q_list_entry = income_to_Qstring([entry])
            display_index = len(income_list) - 1 - index
            if len(removed_income) == 0:
                self.button_add_back.setDisabled(True)

        new_item = QListWidgetItem(q_list_entry[0])
        self.list.insertItem(display_index, new_item)
        self.list.scrollToItem(new_item)

    def filter_list(self, text):
        if text == "":
            for i in range(self.list.count()):
                item = self.list.item(i)
                item.setHidden(False)
        else:
            text = text.lower()

            for i in range(self.list.count()):
                item = self.list.item(i)
                # Hide items that don't match
                item.setHidden(text not in item.text().lower())

    def refresh(self):
        # Reload categories, then the entry list.
        self.expense_tree.set_root(expense_type)
        self.income_tree.set_root(income_type)

        self.list.clear()
        if self.expense_mode:
            self.list.addItems(expense_to_Qstring(expense_list))
        else:
            self.list.addItems(income_to_Qstring(income_list))


# wrap list editing into a single function to prevent mistake
def list_add(inputwindow: InputWindow):
    # Fix the formate of amount.
    text = inputwindow.amount.text()
    if not text:
        inputwindow.amount.setText("0.00")

    try:
        # Convert to float and format to 2 decimal places
        value = float(text)
        inputwindow.amount.setText(f"{value:.2f}")
    except ValueError:
        inputwindow.amount.setText("0.00")

    # Append to expense_list and income_list
    date = inputwindow.calender.selectedDate().toString("yyyy-MM-dd")
    if inputwindow.expense_mode:
        cost = float(inputwindow.amount.text())
        category = inputwindow.expense_tree.current_node().name
        notes = inputwindow.expense_notes.values()

        if inputwindow.irregular.currentIndex() == -1:
            regular = "Every " + str(inputwindow.spin_period.value()) + " months"
        else:
            regular = inputwindow.irregular.currentText()
        trip = inputwindow.trip_selector.currentText()
        entry = ExpenseEntry(date, cost, category, notes, regular, trip)
        index = insort_by_date(expense_list, entry)
    else:
        amount = float(inputwindow.amount.text())
        category = inputwindow.income_tree.current_node().name
        note = inputwindow.income_note_entry.text()
        entry = IncomeEntry(date, amount, category, note)
        index = insort_by_date(income_list, entry)

    # Update QListWidget (displayed newest-date-first, the reverse of the list)
    if inputwindow.expense_mode:
        q_list_entry = expense_to_Qstring([entry])
        display_index = len(expense_list) - 1 - index
    else:
        q_list_entry = income_to_Qstring([entry])
        display_index = len(income_list) - 1 - index

    new_item = QListWidgetItem(q_list_entry[0])
    inputwindow.list.insertItem(display_index, new_item)
    inputwindow.list.scrollToItem(new_item)


def list_remove(inputwindow: InputWindow):
    row = inputwindow.index_selected  # the highlighted row on the list
    if row is None:
        return

    # Put item into removed list to be restored
    if inputwindow.expense_mode:
        # Convert the index since the order of two lists are reversed
        index = len(expense_list) - 1 - row
        removed_expense.append(expense_list.pop(index))
        # Update trip list
        global trip_list
        trip_list = get_trip_list(expense_list)
    else:
        # Convert the index since the order of two lists are reversed
        index = len(income_list) - 1 - row
        removed_income.append(income_list.pop(index))

    # Update QListWidget, need to do this after the above because the removing row in q_list will update the idex
    q_list_entry = inputwindow.list.takeItem(row)
    del q_list_entry


class CategoriesWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.expense_mode = True
        self.switch_x = 40  # Left edge of the widgets below it.
        self.switch_y = 20
        # Top to bottom: the switch, the Delete button, then the category tree.
        self.tree_width = 324
        self.add_button_size = (114, 40)  # The Add button; Delete is sized from it.
        add_height = self.add_button_size[1]
        self.delete_size = (round(self.add_button_size[0] * 3 / 4), add_height)
        self.tree_bottom = self.switch_y + 320  # Fixed; the tree grows upwards.
        self.add_y = self.tree_bottom + 2
        self.notes_y = self.tree_bottom + 32
        notes_frame_y = self.notes_y + 9  # The form's layout margin is 9 px.
        # Delete sits like Add does: the same gap below the switch as Add has
        # below the tree, and the same gap above the tree as Add has above the
        # notes field (negative: their edges overlap by a pixel).
        gap_add_tree = self.add_y - self.tree_bottom
        gap_add_notes = notes_frame_y - (self.add_y + add_height)
        self.delete_y = self.switch_y + 40 + gap_add_tree
        self.tree_y = self.delete_y + add_height + gap_add_notes + 4
        self.initUI()

    def initUI(self):
        self.init_expense_income_switch()
        self.init_category_tree()
        self.init_add_subcategory()
        self.init_notes()
        self.init_rename()
        self.init_button_delete()

    def init_expense_income_switch(self):
        self.label_switch_expense = QLabel("Expense", self)
        self.label_switch_expense.setGeometry(self.switch_x, self.switch_y, 230, 40)

        self.label_switch_expense.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_switch_expense.setStyleSheet(styles.SWITCH_LABEL_ACTIVE)

        self.label_switch_income = QLabel("Income", self)
        self.label_switch_income.setGeometry(self.switch_x + 230, self.switch_y, 95, 30)
        self.label_switch_income.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_switch_income.setStyleSheet(styles.SWITCH_LABEL_INACTIVE)

        self.switch = QCheckBox("", self)
        self.switch.setGeometry(self.switch_x + 230, self.switch_y, 95, 30)
        self.switch.setStyleSheet(styles.TOGGLE_CHECKBOX)

        self.switch.stateChanged.connect(self.switch_change)

    def switch_change(self, state):
        if Qt.CheckState(state) == Qt.CheckState.Checked:  # Income mode.
            self.switch.setGeometry(self.switch_x, self.switch_y, 95, 30)
            self.label_switch_expense.setStyleSheet(
                "background-color: #ecffe6;font-size: 16px;"
            )
            self.label_switch_expense.setGeometry(self.switch_x, self.switch_y, 95, 30)

            self.label_switch_income.setStyleSheet(
                "background-color: #41e8a0;font-weight: bold;font-size: 20px;"
            )
            self.label_switch_income.setGeometry(
                self.switch_x + 95, self.switch_y, 230, 40
            )
            self.expense_mode = False
            self.income_tree.setVisible(True)
            self.expense_tree.setVisible(False)
            self.expense_notes.setVisible(False)
            self.income_tree.clearSelection()
            self.button_delete.setDisabled(True)
        else:  # Expense mode.
            self.switch.setGeometry(self.switch_x + 230, self.switch_y, 95, 30)
            self.label_switch_expense.setStyleSheet(
                "background-color: #41e8a0;font-weight: bold;font-size: 20px;"
            )
            self.label_switch_expense.setGeometry(self.switch_x, self.switch_y, 230, 40)

            self.label_switch_income.setStyleSheet(
                "background-color: #ecffe6;font-size: 16px;"
            )
            self.label_switch_income.setGeometry(
                self.switch_x + 230, self.switch_y, 95, 30
            )
            self.expense_mode = True
            self.income_tree.setVisible(False)
            self.expense_tree.setVisible(True)
            self.expense_notes.setVisible(True)
            self.expense_tree.clearSelection()
            self.button_delete.setDisabled(True)

        # A name typed before switching has to be checked against the other
        # mode's categories, and nothing is selected to add it under yet.
        self.update_add_category_button()
        self.update_rename_button()

    def init_category_tree(self):
        geometry = (40, self.tree_y, self.tree_width, self.tree_bottom - self.tree_y)

        self.expense_tree = CategoryTree(expense_type, self)
        self.expense_tree.setGeometry(*geometry)
        self.expense_tree.itemClicked.connect(self.category_selected)
        self.expense_tree.currentItemChanged.connect(self.load_notes)
        self.expense_tree.itemSelectionChanged.connect(self.update_rename_button)

        self.income_tree = CategoryTree(income_type, self)
        self.income_tree.setGeometry(*geometry)
        self.income_tree.setVisible(False)
        self.income_tree.itemClicked.connect(self.category_selected)
        self.income_tree.currentItemChanged.connect(self.load_notes)
        self.income_tree.itemSelectionChanged.connect(self.update_rename_button)

    def active_tree(self) -> CategoryTree:
        return self.expense_tree if self.expense_mode else self.income_tree

    def selected_node(self) -> Node | None:
        """The category highlighted in the tree, or None if nothing is."""
        items = self.active_tree().selectedItems()
        return items[0].anytree_node if items else None

    def load_notes(self):
        self.new_category.clear()
        self.rename_category.clear()
        self.update_add_category_button()
        if self.expense_mode:
            node = self.expense_tree.current_node()
            if node is not None and hasattr(node, "notes"):
                self.expense_notes.assign_content(node.notes)

    def init_add_subcategory(self):
        self.new_category = QLineEdit(self)
        self.new_category.setStyleSheet("font-size: 16px;")
        self.new_category.setGeometry(self.switch_x, self.tree_bottom + 7, 200, 30)
        self.new_category.setPlaceholderText("new subcategory")
        self.add_category = QPushButton("Add", self)
        self.add_category.setStyleSheet("font-size: 16px;")
        self.add_category.setEnabled(False)
        add_width, add_height = self.add_button_size
        self.add_category.setGeometry(
            self.switch_x + self.tree_width - add_width,
            self.add_y,
            add_width,
            add_height,
        )

        self.new_category.textChanged.connect(self.entering_category)
        self.add_category.clicked.connect(self.add_new_category)

    def update_add_category_button(self):
        """Enable "Add" only for a non-empty name no existing category has, and
        only while a category is highlighted to add it under."""
        name = self.new_category.text()
        self.add_category.setEnabled(
            name != ""
            and not self.active_tree().has_name(name)
            and self.selected_node() is not None
        )

    def entering_category(self):
        self.update_add_category_button()

        if self.expense_mode:
            self.expense_notes.enable_button()

    def add_new_category(self):
        parent = self.selected_node()
        if parent is None:
            return
        self.add_category.setEnabled(False)

        # Update the anytree category tree (and the widget mirroring it).
        if self.expense_mode:
            form = self.expense_notes.form_layout
            # Every row but the last (the "new note" box) names a note.
            notes_list = [
                form.itemAt(i, QFormLayout.ItemRole.LabelRole).widget().text()
                for i in range(form.rowCount() - 1)
            ]
            self.expense_tree.add_child(parent, self.new_category.text(), notes=notes_list)
        else:
            self.income_tree.add_child(parent, self.new_category.text())

        self.new_category.clear()
        # The new category is now the highlighted one.
        self.button_delete.setDisabled(False)

    def init_notes(self):
        self.expense_notes = ScrollableFormApp()
        self.expense_notes.setParent(self)
        self.expense_notes.setGeometry(self.switch_x - 12, self.notes_y, 348, 130)
        self.expense_notes.assign_content(expense_type.notes)

    def category_selected(self, item, column):
        if self.expense_mode:
            if item.text(column) != "All Categories":
                self.button_delete.setDisabled(False)
            else:
                self.button_delete.setDisabled(True)
        else:
            if item.text(column) != "All Income Types":
                self.button_delete.setDisabled(False)
            else:
                self.button_delete.setDisabled(True)

    def reload_categories(self):
        self.expense_tree.set_root(expense_type)
        self.income_tree.set_root(income_type)

    def init_rename(self):
        """The rename box and button, left of Delete. They don't do anything yet."""
        button_width, button_height = self.delete_size
        gap = 10
        delete_x = self.switch_x + self.tree_width - button_width
        rename_x = delete_x - gap - button_width

        self.button_rename = QPushButton("Rename", self)
        self.button_rename.setStyleSheet("font-size: 16px;")
        self.button_rename.setGeometry(rename_x, self.delete_y, button_width, button_height)

        # Same look as the new-subcategory box, vertically centred on the buttons.
        box_height = 30
        self.rename_category = QLineEdit(self)
        self.rename_category.setStyleSheet("font-size: 16px;")
        self.rename_category.setPlaceholderText("new name")
        self.rename_category.setGeometry(
            self.switch_x,
            self.delete_y + (button_height - box_height) // 2,
            rename_x - gap - self.switch_x,
            box_height,
        )

        self.rename_category.textChanged.connect(self.update_rename_button)
        self.button_rename.clicked.connect(self.rename_clicked)
        self.update_rename_button()

    def update_rename_button(self):
        """Rename is available only while a name is typed that no category has
        yet (the same rule as Add), and a category is highlighted. The root
        ("All Categories" / "All Income Types") can't be renamed, as it can't
        be deleted: other code recognises it by name."""
        name = self.rename_category.text()
        node = self.selected_node()
        self.button_rename.setEnabled(
            name != ""
            and not self.active_tree().has_name(name)
            and node is not None
            and node.parent is not None
        )

    def rename_clicked(self):
        tree = self.active_tree()
        node = self.selected_node()
        new_name = self.rename_category.text()
        if node is None or node.parent is None or tree.has_name(new_name):
            return

        old_name = node.name
        tree.rename_node(node, new_name)
        # Entries refer to their category by name, so follow the rename. That
        # includes deleted entries that "Add back" could still restore.
        if self.expense_mode:
            entries = expense_list + removed_expense
        else:
            entries = income_list + removed_income
        for entry in entries:
            if entry.category == old_name:
                entry.category = new_name

        self.rename_category.clear()
        # The old name is free again, so Add may now accept it.
        self.update_add_category_button()

    def init_button_delete(self):
        self.button_delete = QPushButton("Delete", self)
        # Right-aligned with the tree; the Add button's height and font, 3/4 of its width.
        delete_width, delete_height = self.delete_size
        self.button_delete.setGeometry(
            self.switch_x + self.tree_width - delete_width,
            self.delete_y,
            delete_width,
            delete_height,
        )
        self.button_delete.setStyleSheet("font-size: 16px;")
        self.button_delete.setDisabled(True)

        self.button_delete.clicked.connect(self.delete_category)

    def delete_category(self):
        self.button_delete.setDisabled(True)

        tree = self.expense_tree if self.expense_mode else self.income_tree
        entries = expense_list if self.expense_mode else income_list

        current_category = tree.current_node()
        # Move any entries in the deleted category up to its parent.
        parent_name = current_category.parent.name
        for entry in entries:
            if entry.category == current_category.name:
                entry.category = parent_name

        tree.remove_current()


class SummaryWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.summary_type = QComboBox(self)
        self.summary_type.setStyleSheet("font-size: 18px;")
        self.summary_type.addItem("Summarize by time")
        self.summary_type.addItem("Summarize a trip")

        self.summary_type.currentTextChanged.connect(self.load_options)

        self.select = QComboBox(self)
        self.select.setStyleSheet("font-size: 18px;")

        self.button_summarize = QPushButton("Summarize", self)
        self.button_summarize.setStyleSheet("font-size: 18px;")

        self.button_summarize.clicked.connect(self.summarize)

        self.load_options("Summarize by time")

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.summary_type)
        layout.addWidget(self.select)
        layout.addWidget(self.button_summarize)
        layout.addWidget(self.canvas)

    def load_options(self, text):
        self.select.clear()
        match text:
            case "Summarize by time":
                self.select.addItem("All time")
                # Figure out the options of year.
                year_list = []
                for entry in expense_list:
                    date = datetime.date.fromisoformat(entry.date)
                    year_list.append(date.year)

                year_list = list(set(year_list))
                year_list.sort()

                # Figure out the options of month.
                month_list = []  # Store year in month in (year * 100 + month) integer format.
                for entry in expense_list:
                    date = datetime.date.fromisoformat(entry.date)
                    for year in year_list:
                        if date.year == year:
                            month_list.append(year * 100 + date.month)

                month_list = list(set(month_list))
                month_list.sort()

                # Add to QCombobox.
                for month in month_list:
                    self.select.addItem(str(month % 100) + "/" + str(month // 100))

            case "Summarize a trip":
                self.select.addItems(trip_list)
            case _:
                print("Unknown summary type.")

        if self.select.count() == 0:
            self.button_summarize.setDisabled(True)
        else:
            self.button_summarize.setDisabled(False)

    def summarize(self):
        print("=" * 100)
        print(self.summary_type.currentText())
        print(f"For {self.select.currentText()}:")

        # select the entries to include in the summary.
        expense_list_for_summary = []
        match self.summary_type.currentText():
            case "Summarize a trip":
                print("-" * 100)
                # Create a list only containing the expenses on the trip and print it.
                expense_list_for_summary = []
                for entry in expense_list:
                    if entry.trip == self.select.currentText():
                        expense_list_for_summary.append(entry)
                        print(expense_string(entry))
                print("-" * 100)
                print("Total spending in each category:")
            case "Summarize by time":
                if self.select.currentText() == "All time":
                    expense_list_for_summary = expense_list
                else:
                    for entry in expense_list:
                        date = datetime.date.fromisoformat(entry.date)
                        date_string = str(date.month) + "/" + str(date.year)
                        if date_string == self.select.currentText():
                            expense_list_for_summary.append(entry)

        # Create copy so the original one is untouched.
        expense_type_copy = copy.deepcopy(expense_type)
        # Sum the spendings.
        match self.summary_type.currentText():
            case "Summarize a trip":
                # Sum the spending at the last child level.
                for category in PreOrderIter(expense_type_copy):
                    setattr(category, "total", 0)
                    for entry in expense_list_for_summary:
                        if category.name == entry.category:
                            category.total += entry.cost
                # Sum the spending of subcategories into categories.
                for category in PostOrderIter(expense_type_copy):
                    for child in category.children:
                        category.total += child.total
                    for category in PreOrderIter(expense_type_copy):
                        category.total = round(category.total, 2)

            case "Summarize by time":
                # Sum the spending at the last child level.
                for category in PreOrderIter(expense_type_copy):
                    setattr(category, "regular_total", 0)
                    setattr(category, "not_regular_total", 0)
                    for entry in expense_list_for_summary:
                        if category.name == entry.category:
                            if entry.regular == "Regular":
                                category.regular_total += entry.cost
                            else:
                                category.not_regular_total += entry.cost
                # Sum the spending of subcategories into categories.
                for category in PostOrderIter(expense_type_copy):
                    for child in category.children:
                        category.regular_total += child.regular_total
                        category.not_regular_total += child.not_regular_total

                for category in PostOrderIter(expense_type_copy):
                    category.regular_total = round(category.regular_total, 2)
                    category.not_regular_total = round(category.not_regular_total, 2)
                    setattr(
                        category,
                        "total",
                        round(category.regular_total + category.not_regular_total, 2),
                    )

        if self.summary_type.currentText() == "Summarize a trip":
            plot_category = []
            plot_value = []
            for category in PreOrderIter(expense_type_copy):
                if category.total > 0:
                    print(
                        f"{len(category.ancestors) * '   '}{category.name}: ${category.total}"
                    )
                    if len(category.children) == 0:
                        plot_category.append(category.name + f" ${category.total}")
                        plot_value.append(category.total)
        else:
            regular_labels = []
            regular_value = []
            regular_colors = []
            not_regular_labels = []
            not_regular_value = []
            not_regular_colors = []
            legend_entries = []  # (category name, colour) for the legend
            print("Total spending in each category:")

            for category in PreOrderIter(expense_type_copy):
                print(
                    f"{len(category.ancestors) * '   '}{category.name}: ${category.total}"
                )

            # A category keeps the same colour in both pies (and in every period),
            # so it is picked by its position among all top-level categories.
            palette = styles.CHART_CATEGORY_COLORS
            for i, child in enumerate(expense_type_copy.children):
                color = palette[i % len(palette)]
                if child.regular_total > 0:
                    regular_labels.append(f"${child.regular_total}")
                    regular_value.append(child.regular_total)
                    regular_colors.append(color)
                if child.not_regular_total > 0:
                    not_regular_labels.append(f"${child.not_regular_total}")
                    not_regular_value.append(child.not_regular_total)
                    not_regular_colors.append(color)
                if child.regular_total > 0 or child.not_regular_total > 0:
                    legend_entries.append((child.name, color))

            print("-" * 100)
            # Select income entries to summarize
            income_type_copy = copy.deepcopy(income_type)
            income_list_for_summary = []
            for entry in income_list:
                if self.select.currentText() == "All time":
                    income_list_for_summary = income_list
                else:
                    date = datetime.date.fromisoformat(entry.date)
                    date_string = str(date.month) + "/" + str(date.year)
                    if date_string == self.select.currentText():
                        income_list_for_summary.append(entry)

            # Sum the income at the last child level.
            for category in PreOrderIter(income_type_copy):
                setattr(category, "total", 0)
                for entry in income_list_for_summary:
                    if category.name == entry.category:
                        category.total += entry.amount
            # Sum the income of subcategories into categories.
            for category in PostOrderIter(income_type_copy):
                for child in category.children:
                    category.total += child.total

            for category in PreOrderIter(income_type_copy):
                category.total = round(category.total, 2)

            print("Total earning in each type of income:")

            for category in PreOrderIter(income_type_copy):
                print(
                    f"{len(category.ancestors) * '   '}{category.name}: ${category.total}"
                )

            # Compare price if quantity (weight) is noted.
            for category in PostOrderIter(expense_type):
                if WEIGHT_NOTE in category.notes:
                    print("-" * 100)
                    cheapest_per_lb = -1
                    most_expensive = 0
                    total_weight = 0
                    total_cost = 0
                    i = -1
                    for entry in expense_list_for_summary:
                        i += 1
                        if entry.category == category.name:
                            weight_in_lb = Q_(entry.notes[WEIGHT_NOTE]).to("lb")
                            price_per_lb = entry.cost / weight_in_lb.magnitude
                            total_weight += weight_in_lb.magnitude
                            total_cost += entry.cost
                            if cheapest_per_lb < 0 or price_per_lb < cheapest_per_lb:
                                cheapest_per_lb = price_per_lb
                                cheapest_index = i
                            if price_per_lb > most_expensive:
                                most_expensive = price_per_lb
                                most_expensive_index = i
                    try:
                        print(
                            f"The cheapest {category.name} is: ${round(cheapest_per_lb, 2)} per pound, with the following purchase:"
                        )
                        entry = expense_list_for_summary[cheapest_index]
                        print(expense_string(entry))
                        print(
                            f"The most expensive {category.name}  is: ${round(most_expensive, 2)} per pound, with the following purchase:"
                        )
                        entry = expense_list_for_summary[most_expensive_index]
                        print(expense_string(entry))
                        print(
                            f"You bought {round(total_weight, 1)} lb of {category.name} in total, ${round(total_cost / total_weight, 2)} per pound on average."
                        )
                        print(
                            f"You can save ${round(total_cost - cheapest_per_lb * total_weight, 2)} if you stick with the cheapest option."
                        )
                    except NameError:
                        print(f"No {category.name} was bought.")
                    else:
                        del cheapest_index

        # Clear the previous plot to prevent overlapping lines
        self.figure.clear()

        # Draw the pie charts.
        match self.summary_type.currentText():
            case "Summarize a trip":
                # Create an axes object and plot data
                ax = self.figure.add_subplot(111)
                plot_title = self.select.currentText() + f"\n${expense_type_copy.total}"
                ax.pie(plot_value, labels=plot_category, autopct="%1.1f%%")
                ax.set_title(plot_title)
            case "Summarize by time":
                regular_sum = sum(regular_value)
                not_regular_sum = sum(not_regular_value)
                combined = regular_sum + not_regular_sum

                def pie_radius(part):
                    # Pie area is proportional to its share of the spending; an
                    # even split gives 0.7 each. Never smaller than 0.2 so a tiny
                    # share stays visible. combined is 0 when no expense is counted
                    # (e.g. a month with only $0 entries), where both pies are empty.
                    if combined <= 0:
                        return 0.7
                    return max(0.2, 0.7 * math.sqrt(2 * part / combined))

                ax1 = self.figure.add_subplot(1, 2, 1)
                ax2 = self.figure.add_subplot(1, 2, 2)
                try:
                    ax1.pie(
                        regular_value,
                        labels=regular_labels,
                        colors=regular_colors,
                        autopct="%1.1f%%",
                        radius=pie_radius(regular_sum),
                    )
                except ValueError:
                    print("No regular expenses.")
                else:
                    ax1.set_title(f"Regular ${expense_type_copy.regular_total}")
                try:
                    ax2.pie(
                        not_regular_value,
                        labels=not_regular_labels,
                        colors=not_regular_colors,
                        autopct="%1.1f%%",
                        radius=pie_radius(not_regular_sum),
                    )
                except ValueError:
                    print("No non-regular expenses.")
                else:
                    ax2.set_title(f"Not regular ${expense_type_copy.not_regular_total}")

                if combined > 0:
                    # Same arithmetic matplotlib's autopct used for the old centre pie.
                    self.figure.suptitle(
                        f"Total Spending ${expense_type_copy.total}, "
                        f"{100.0 * (regular_sum / combined):.1f}% regular, "
                        f"{100.0 * (not_regular_sum / combined):.1f}% not regular"
                    )
                else:
                    print("No expenses.")

                if legend_entries:
                    self.figure.legend(
                        handles=[
                            Patch(facecolor=color, label=name)
                            for name, color in legend_entries
                        ],
                        loc="lower center",
                        ncol=min(len(legend_entries), 5),
                    )
                    self.figure.subplots_adjust(bottom=0.2)

        self.canvas.draw()


class PeriodicWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.label_title = QLabel("Periodic Expenses", self)
        self.label_title.setGeometry(40, 30, 400, 40)
        self.label_title.setStyleSheet("font-size: 22px; font-weight: bold;")

        self.list = QListWidget(self)
        self.list.setGeometry(40, 80, 600, 550)
        self.list.setStyleSheet(styles.LIST_WIDGET)
        self.refresh()

    def refresh(self):
        self.list.clear()
        periodic_expenses = [
            entry for entry in expense_list if PERIODIC_REGEX.match(entry.regular)
        ]
        self.list.addItems(expense_to_Qstring(periodic_expenses))


class GraphWindow(QWidget):
    GRAPH_TYPES = [
        "Expense by month",
        "Income minus expense by month",
        "Regular expense by month",
    ]

    def __init__(self):
        super().__init__()

        self.graph_type = QComboBox(self)
        self.graph_type.setStyleSheet("font-size: 18px;")
        self.graph_type.addItems(self.GRAPH_TYPES)
        self.graph_type.currentTextChanged.connect(self.draw)

        self.figure = Figure(layout="constrained")
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout(self)
        layout.addWidget(self.graph_type)
        layout.addWidget(self.canvas, stretch=1)

        self.draw()

    def refresh(self):
        """Redraw from the current data (called when the page is shown)."""
        self.draw()

    def draw(self, _=None):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        drawers = {
            "Expense by month": self.draw_expense_by_month,
            "Income minus expense by month": self.draw_net_by_month,
            "Regular expense by month": self.draw_regular_expense_by_month,
        }
        drawers[self.graph_type.currentText()](ax)
        ax.yaxis.set_major_formatter(FuncFormatter(self.format_dollars))
        # Horizontal grid lines behind the bars to make amounts easier to read.
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#d0d0d0", linewidth=0.8)
        self.canvas.draw()

    @staticmethod
    def format_dollars(value, _position=None):
        return f"-${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"

    def set_month_ticks(self, ax, months):
        # Thin the labels out when there are many months so they stay readable.
        step = max(1, len(months) // 24)
        positions = list(range(0, len(months), step))
        ax.set_xticks(positions, [months[i] for i in positions], rotation=45, ha="right")

    def draw_no_data(self, ax):
        ax.text(0.5, 0.5, "No data to graph", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])

    def draw_expense_by_month(self, ax):
        months, regular, not_regular = graph_data.expense_by_month(expense_list)
        if not months:
            self.draw_no_data(ax)
            return

        x = list(range(len(months)))
        # Regular on the bottom, not regular stacked on top of it.
        ax.bar(x, regular, color=styles.CHART_REGULAR, label="Regular")
        ax.bar(x, not_regular, bottom=regular, color=styles.CHART_NOT_REGULAR,
               label="Not regular")
        self.set_month_ticks(ax, months)
        ax.set_ylabel("Total expense")
        ax.legend()

    def draw_regular_expense_by_month(self, ax):
        months, regular = graph_data.regular_expense_by_month(expense_list)
        if not months:
            self.draw_no_data(ax)
            return

        ax.bar(range(len(months)), regular, color=styles.CHART_REGULAR)
        self.set_month_ticks(ax, months)
        ax.set_ylabel("Total regular expense")

    def draw_net_by_month(self, ax):
        months, net = graph_data.net_by_month(income_list, expense_list)
        if not months:
            self.draw_no_data(ax)
            return

        x = list(range(len(months)))
        colors = [
            styles.CHART_POSITIVE if value >= 0 else styles.CHART_NEGATIVE
            for value in net
        ]
        ax.bar(x, net, color=colors)
        ax.axhline(0, color="black", linewidth=0.8)
        self.set_month_ticks(ax, months)
        ax.set_ylabel("Income minus expense")


def main():
    app = QApplication(sys.argv)
    print(f"Data folder: {persistence.USER_DATA_DIR}")
    load_data()
    main_window = MainWindow()
    main_window.setWindowTitle("Money Tracker")
    main_window.setGeometry(500, 100, 790 + INPUT_SHIFT, 720)
    main_window.setFixedHeight(720)
    main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
