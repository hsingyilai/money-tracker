from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QDateEdit,
    QLabel,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QLineEdit,
    QFormLayout,
    QStackedWidget,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QSpinBox,
)
from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator
import sys
import json
from anytree.importer import JsonImporter
from anytree.exporter import JsonExporter
from anytree import LevelOrderIter, Node, PreOrderIter, PostOrderIter, RenderTree
import copy
import datetime
from expense_module import ExpenseEntry, IncomeEntry
from expense_functions import (
    expense_to_Qstring,
    income_to_Qstring,
    expense_string,
    get_trip_list,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pint import UnitRegistry

ureg = UnitRegistry()
Q_ = ureg.Quantity


# Define a QDate object for today.
date_now = datetime.datetime.now()
qtoday = QDate(date_now.year, date_now.month, date_now.day)

# Load the list datas.
try:
    with open("my_expenses.json", "r") as f:
        expense_list_data = json.load(f)
except FileNotFoundError:
    expense_list = []
else:
    expense_list = [ExpenseEntry(**entry) for entry in expense_list_data]

try:
    with open("my_incomes.json", "r") as f:
        income_list_data = json.load(f)
except FileNotFoundError:
    income_list = []
else:
    income_list = [IncomeEntry(**entry) for entry in income_list_data]


# Load the categories.
importer = JsonImporter()
try:
    with open("expense_categories.json", "r") as f:
        expense_type = importer.read(f)
except FileNotFoundError:
    expense_type = Node("All Categories")
    setattr(expense_type, "notes", ["note"])

try:
    with open("income_categories.json", "r") as f:
        income_type = importer.read(f)
except FileNotFoundError:
    income_type = Node("All Income Types")


# Get the trip list.
trip_list = get_trip_list(expense_list)

# Stores the removed entry as a stack of ExpenseEntry or IncomeEntry
removed_expense = []
removed_income = []


# Main Window
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        main_display = MainStack()
        switch = FunctionSwitch()

        vbox = QVBoxLayout()
        vbox.addWidget(main_display, stretch=12)
        vbox.addWidget(switch, stretch=1)

        self.setLayout(vbox)

        switch.function_change.connect(main_display.set_function)

    def closeEvent(self, event):
        expense_list_data = [vars(entry) for entry in expense_list]
        with open("my_expenses.json", "w") as f:
            json.dump(expense_list_data, f, indent=4)

        income_list_data = [vars(entry) for entry in income_list]
        with open("my_incomes.json", "w") as f:
            json.dump(income_list_data, f, indent=4)

        # Remove the index which we don't need to save
        for node in LevelOrderIter(expense_type):
            del node.index

        for node in LevelOrderIter(income_type):
            del node.index

        # Save the new expense category tree.
        exporter = JsonExporter(indent=2)

        all_category_json_string = exporter.export(expense_type)
        with open("expense_categories.json", "w") as f:
            f.write(all_category_json_string)

        all_category_json_string = exporter.export(income_type)
        with open("income_categories.json", "w") as f:
            f.write(all_category_json_string)

        event.accept()
        super().closeEvent(event)


# Custom Widgets for the main window
class MainStack(QStackedWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        window_input = InputWindow()
        window_categories = CategoriesWindow()
        window_summary = SummaryWindow()
        window_periodic = PeriodicWindow()

        self.addWidget(window_input)
        self.addWidget(window_categories)
        self.addWidget(window_summary)
        self.addWidget(window_periodic)

    def set_function(self, function):
        match function:
            case "Input":
                self.setCurrentIndex(0)
                page = self.widget(0)
                page.refresh()
            case "Categories":
                self.setCurrentIndex(1)
                page = self.widget(1)
                page.reload_categories()
            case "Summary":
                self.setCurrentIndex(2)
                page = self.widget(2)
                page.load_options(page.summary_type.currentText())
            case "Periodic Expenses":
                self.setCurrentIndex(3)


class FunctionSwitch(QStackedWidget):
    function_change = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        input_mode = InputMode()
        categories_mode = CategoriesMode()
        summary_mode = SummaryMode()
        periodic_mode = PeriodicMode()

        self.addWidget(input_mode)
        self.addWidget(categories_mode)
        self.addWidget(summary_mode)
        self.addWidget(periodic_mode)

        input_mode.mode_change.connect(self.set_function)
        categories_mode.mode_change.connect(self.set_function)
        summary_mode.mode_change.connect(self.set_function)
        periodic_mode.mode_change.connect(self.set_function)

    def set_function(self, function):
        self.function_change.emit(function)
        match function:
            case "Input":
                self.setCurrentIndex(0)
            case "Categories":
                self.setCurrentIndex(1)
            case "Summary":
                self.setCurrentIndex(2)
            case "Periodic Expenses":
                self.setCurrentIndex(3)


class InputMode(QWidget):
    mode_change = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        label_input = QLabel("Input", self)
        label_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_input.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 18px;"
        )
        label_input.setFixedHeight(60)

        button_categories = QPushButton("Categories", self)
        button_categories.setStyleSheet("font-size: 18px;")
        button_categories.clicked.connect(self.go_to_categories)
        button_categories.setFixedHeight(50)

        button_summary = QPushButton("Summary", self)
        button_summary.setStyleSheet("font-size: 18px;")
        button_summary.clicked.connect(self.go_to_summary)
        button_summary.setFixedHeight(50)

        button_periodic = QPushButton("Periodic Expenses", self)
        button_periodic.setStyleSheet("font-size: 18px;")
        button_periodic.clicked.connect(self.go_to_periodic)
        button_periodic.setFixedHeight(50)

        hbox = QHBoxLayout()
        hbox.addWidget(label_input)
        hbox.addWidget(button_categories)
        hbox.addWidget(button_summary)
        hbox.addWidget(button_periodic)
        self.setLayout(hbox)

    def go_to_categories(self):
        self.mode_change.emit("Categories")

    def go_to_summary(self):
        self.mode_change.emit("Summary")

    def go_to_periodic(self):
        self.mode_change.emit("Periodic Expenses")


class CategoriesMode(QWidget):
    mode_change = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        button_input = QPushButton("Input", self)
        button_input.setStyleSheet("font-size: 18px;")
        button_input.clicked.connect(self.go_to_input)
        button_input.setFixedHeight(50)

        label_categories = QLabel("Categories", self)
        label_categories.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_categories.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 18px;"
        )
        label_categories.setFixedHeight(60)

        button_summary = QPushButton("Summary", self)
        button_summary.setStyleSheet("font-size: 18px;")
        button_summary.clicked.connect(self.go_to_summary)
        button_summary.setFixedHeight(50)

        button_periodic = QPushButton("Periodic Expenses", self)
        button_periodic.setStyleSheet("font-size: 18px;")
        button_periodic.clicked.connect(self.go_to_periodic)
        button_periodic.setFixedHeight(50)

        hbox = QHBoxLayout()
        hbox.addWidget(button_input)
        hbox.addWidget(label_categories)
        hbox.addWidget(button_summary)
        hbox.addWidget(button_periodic)
        self.setLayout(hbox)

    def go_to_input(self):
        self.mode_change.emit("Input")

    def go_to_summary(self):
        self.mode_change.emit("Summary")

    def go_to_periodic(self):
        self.mode_change.emit("Periodic Expenses")


class SummaryMode(QWidget):
    mode_change = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        button_input = QPushButton("Input", self)
        button_input.setStyleSheet("font-size: 18px;")
        button_input.clicked.connect(self.go_to_input)
        button_input.setFixedHeight(50)

        button_categories = QPushButton("Categories", self)
        button_categories.setStyleSheet("font-size: 18px;")
        button_categories.clicked.connect(self.go_to_categories)
        button_categories.setFixedHeight(50)

        label_summary = QLabel("Summary", self)
        label_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_summary.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 18px;"
        )
        label_summary.setFixedHeight(60)

        button_periodic = QPushButton("Periodic Expenses", self)
        button_periodic.setStyleSheet("font-size: 18px;")
        button_periodic.clicked.connect(self.go_to_periodic)
        button_periodic.setFixedHeight(50)

        hbox = QHBoxLayout()
        hbox.addWidget(button_input)
        hbox.addWidget(button_categories)
        hbox.addWidget(label_summary)
        hbox.addWidget(button_periodic)
        self.setLayout(hbox)

    def go_to_input(self):
        self.mode_change.emit("Input")

    def go_to_categories(self):
        self.mode_change.emit("Categories")

    def go_to_periodic(self):
        self.mode_change.emit("Periodic Expenses")


class PeriodicMode(QWidget):
    mode_change = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        button_input = QPushButton("Input", self)
        button_input.setStyleSheet("font-size: 18px;")
        button_input.clicked.connect(self.go_to_input)
        button_input.setFixedHeight(50)

        button_categories = QPushButton("Categories", self)
        button_categories.setStyleSheet("font-size: 18px;")
        button_categories.clicked.connect(self.go_to_categories)
        button_categories.setFixedHeight(50)

        button_summary = QPushButton("Summary", self)
        button_summary.setStyleSheet("font-size: 18px;")
        button_summary.clicked.connect(self.go_to_summary)
        button_summary.setFixedHeight(50)

        label_periodic = QLabel("Periodic Expenses", self)
        label_periodic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_periodic.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 18px;"
        )
        label_periodic.setFixedHeight(60)

        hbox = QHBoxLayout()
        hbox.addWidget(button_input)
        hbox.addWidget(button_categories)
        hbox.addWidget(button_summary)
        hbox.addWidget(label_periodic)
        self.setLayout(hbox)

    def go_to_input(self):
        self.mode_change.emit("Input")

    def go_to_categories(self):
        self.mode_change.emit("Categories")

    def go_to_summary(self):
        self.mode_change.emit("Summary")


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


class MyTreeWidgetItem(QTreeWidgetItem):
    def __init__(self):
        super().__init__()
        self.anytree_node = None  # The corresponding anytree.Node


# The stacked child-windows.
class InputWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()
        self.expense_mode = True

    def initUI(self):
        self.switch_x = 40
        self.switch_y = 30
        self.index_selected = None  # The index of selected entry on the list
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
        self.label_switch_expense.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 20px;"
        )

        self.label_switch_income = QLabel("Income", self)
        self.label_switch_income.setGeometry(self.switch_x + 230, self.switch_y, 95, 30)
        self.label_switch_income.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_switch_income.setStyleSheet(
            "background-color: #ecffe6;font-size: 16px;"
        )

        self.switch = QCheckBox("", self)
        self.switch.setGeometry(self.switch_x + 230, self.switch_y, 95, 30)
        self.switch.setStyleSheet(
            """
                                  QCheckBox::indicator{
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
        )

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
            self.button_delete.setDisabled(True)
            self.index_selected = None
            self.list.addItems(income_to_Qstring(income_list))
            self.expense_mode = False
            self.income_tree.setVisible(True)
            self.expense_tree.setVisible(False)
            self.label_amount.setText("Income:    $")
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
            self.button_delete.setDisabled(True)
            self.index_selected = None
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

    def init_select_date(self):
        self.calender = QDateEdit(self)
        self.calender.setGeometry(90, 80, 200, 40)
        self.calender.setDate(qtoday)
        self.calender.setStyleSheet("font-size: 20px;")

        self.label_date = QLabel("Date:", self)
        self.label_date.setGeometry(40, 80, 50, 40)
        self.label_date.setStyleSheet("font-size: 20px;")

        self.button_today = QPushButton("Today", self)
        self.button_today.setGeometry(295, 80, 70, 40)
        self.button_today.setStyleSheet("font-size: 16px;")

        self.button_today.clicked.connect(self.set_today)

    def set_today(self):
        self.calender.setDate(qtoday)

    def init_amount(self):
        self.label_amount = QLabel("Expense: $", self)
        self.label_amount.setGeometry(40, 130, 100, 35)
        self.label_amount.setStyleSheet("font-size: 20px;")

        self.amount = QLineEdit(self)
        self.amount.setGeometry(140, 128, 110, 40)
        self.amount.setPlaceholderText("0.00")
        self.amount.setStyleSheet("font-size: 20px;")
        validator = QDoubleValidator(0.00, 999999.99, 2, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.amount.setValidator(validator)

    def init_irregular(self):
        self.irregular = QComboBox(self)
        self.irregular.setGeometry(260, 128, 110, 40)
        self.irregular.setStyleSheet("font-size: 18px;")
        self.irregular.addItem("Regular")
        self.irregular.addItem("Irregular")
        self.irregular.addItem("Regular but not monthly")
        self.irregular.setPlaceholderText("period")

        self.irregular.activated.connect(self.irregular_clicked)

        self.spin_period = QSpinBox(self)
        self.spin_period.setGeometry(270, 146, 50, 30)
        self.spin_period.setMinimum(2)
        self.spin_period.setMaximum(999)
        self.spin_period.setVisible(False)
        self.label_month = QLabel("months", self)
        self.label_month.setGeometry(325, 146, 50, 30)
        self.label_month.setVisible(False)

    def irregular_clicked(self, index):
        if index == 2:
            self.irregular.setGeometry(260, 114, 110, 40)
            self.irregular.removeItem(2)
            self.irregular.setCurrentIndex(-1)
            self.spin_period.setVisible(True)
            self.label_month.setVisible(True)
        else:
            self.irregular.setGeometry(260, 128, 110, 40)
            self.irregular.setEditable(False)
            self.spin_period.setVisible(False)
            self.label_month.setVisible(False)
            if self.irregular.count() == 2:
                self.irregular.addItem("Regular but not monthly")

    def init_category_tree(self):
        self.expense_type_pointer = []  # Load expense categories.
        i = 0
        for category in LevelOrderIter(expense_type):
            self.expense_type_pointer.append(MyTreeWidgetItem())
            self.expense_type_pointer[-1].setText(0, category.name)
            self.expense_type_pointer[-1].anytree_node = category
            category.index = i  # Points from the anytree.Node to the QTreeWidgetItem
            i += 1
        self.next_pointer = i  # For adding new category

        # Connect the nodes in PyQt following anytree.
        for category in LevelOrderIter(expense_type):
            for child_category in category.children:
                self.expense_type_pointer[category.index].addChild(
                    self.expense_type_pointer[child_category.index]
                )

        self.expense_tree = QTreeWidget(self)
        self.expense_tree.setStyleSheet("font-size: 18px;")
        self.expense_tree.setColumnCount(1)
        self.expense_tree.setGeometry(self.switch_x, self.switch_y + 145, 324, 170)
        self.expense_tree.setHeaderHidden(True)
        self.expense_tree.addTopLevelItem(
            self.expense_type_pointer[0]
        )  # The 0th pointer is All Categories
        self.expense_tree.setCurrentItem(self.expense_type_pointer[0])
        self.expense_type_pointer[0].setExpanded(True)

        self.expense_tree.currentItemChanged.connect(self.load_notes)

        self.income_type_pointer = []  # Load income categories.
        i = 0
        for category in LevelOrderIter(income_type):
            self.income_type_pointer.append(MyTreeWidgetItem())
            self.income_type_pointer[-1].setText(0, category.name)
            self.income_type_pointer[-1].anytree_node = category
            category.index = i  # Points from the anytree.Node to the QTreeWidgetItem
            i += 1
        self.next_income_pointer = i  # For adding new income category

        # Connect the nodes in PyQt following anytree.
        for category in LevelOrderIter(income_type):
            for child_category in category.children:
                self.income_type_pointer[category.index].addChild(
                    self.income_type_pointer[child_category.index]
                )

        self.income_tree = QTreeWidget(self)
        self.income_tree.setStyleSheet("font-size: 18px;")
        self.income_tree.setColumnCount(1)
        self.income_tree.setGeometry(self.switch_x, self.switch_y + 145, 324, 170)
        self.income_tree.setHeaderHidden(True)
        self.income_tree.addTopLevelItem(self.income_type_pointer[0])
        self.income_tree.setCurrentItem(self.income_type_pointer[0])
        self.income_type_pointer[0].setExpanded(True)
        self.income_tree.setVisible(False)

        self.income_tree.currentItemChanged.connect(self.load_notes)

    def load_notes(self, previous):
        self.new_category.clear()
        self.add_category.setEnabled(False)
        if self.expense_mode:
            try:
                self.expense_notes.assign_content(
                    self.expense_tree.currentItem().anytree_node.notes
                )
            except AttributeError:
                pass

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

    def entering_category(self):
        if self.new_category.text() == "":
            self.add_category.setEnabled(False)
        else:
            self.add_category.setEnabled(True)

        if self.expense_mode:
            self.expense_notes.enable_button()

    def add_new_category(self):
        self.add_category.setEnabled(False)

        # Update the anytree cateogry tree
        if self.expense_mode:
            current_category = self.expense_tree.currentItem().anytree_node
            notes_list = [
                self.expense_notes.form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
                .widget()
                .text()
                for i in range(0, self.expense_notes.form_layout.rowCount() - 1)
            ]

            new_node = Node(
                self.new_category.text(), parent=current_category, notes=notes_list
            )

            new_node.index = self.next_pointer
            self.next_pointer += 1

            # Update the PyQt tree
            self.expense_type_pointer.append(MyTreeWidgetItem())
            self.expense_type_pointer[-1].setText(0, new_node.name)
            self.expense_type_pointer[current_category.index].addChild(
                self.expense_type_pointer[-1]
            )

            self.expense_type_pointer[-1].anytree_node = new_node

            self.expense_tree.setCurrentItem(self.expense_type_pointer[-1])

            self.expense_notes.assign_content(
                self.expense_tree.currentItem().anytree_node.notes
            )
        else:
            current_category = self.income_tree.currentItem().anytree_node

            new_node = Node(self.new_category.text(), parent=current_category)

            new_node.index = self.next_income_pointer
            self.next_income_pointer += 1

            # Update the PyQt tree
            self.income_type_pointer.append(MyTreeWidgetItem())
            self.income_type_pointer[-1].setText(0, new_node.name)
            self.income_type_pointer[current_category.index].addChild(
                self.income_type_pointer[-1]
            )

            self.income_type_pointer[-1].anytree_node = new_node

            self.income_tree.setCurrentItem(self.income_type_pointer[-1])

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
        self.button_submit.setGeometry(40, 535, 325, 50)
        self.button_submit.setStyleSheet(
            """
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
        )

        self.button_submit.clicked.connect(self.submit_entry)

    def submit_entry(self):
        list_add(self)
        self.amount.clear()
        # update trip list
        selected_trip = self.trip_selector.currentText()
        if selected_trip in trip_list:
            pass
        elif selected_trip != "":
            self.trip_selector.addItem(selected_trip)
            trip_list.append(selected_trip)
            trip_list.sort()
        self.list.clearSelection()
        self.index_selected = None

    def init_list(self):
        self.label_find = QLabel("Find:", self)
        self.label_find.setGeometry(380, 30, 40, 30)
        self.label_find.setStyleSheet("font-size: 18px;")

        self.text_find = QLineEdit(self)
        self.text_find.setGeometry(425, 30, 285, 30)
        self.text_find.setStyleSheet("font-size: 18px;")
        self.text_find.textChanged.connect(self.filter_list)

        self.list = QListWidget(self)
        self.list.setGeometry(380, 65, 330, 475)
        self.list.addItems(expense_to_Qstring(expense_list))
        self.list.setStyleSheet(
            """
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
        )
        self.list.itemClicked.connect(self.list_clicked)

        self.button_add_back = QPushButton("Add back", self)
        self.button_add_back.setStyleSheet(
            """
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
        )
        self.button_add_back.setGeometry(385, 550, 100, 30)
        self.button_add_back.setDisabled(True)
        self.button_add_back.clicked.connect(self.add_back)

        self.button_delete = QPushButton("Delete", self)
        self.button_delete.setStyleSheet(
            """
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
        )
        self.button_delete.setGeometry(495, 550, 100, 30)
        self.button_delete.setDisabled(True)
        self.button_delete.clicked.connect(self.delete_entry)

        self.button_new_entry = QPushButton("New Entry", self)
        self.button_new_entry.setStyleSheet(
            """
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
        )
        self.button_new_entry.setGeometry(605, 550, 100, 30)
        self.button_new_entry.clicked.connect(self.new_entry)

    def list_clicked(self, item):
        self.index_selected = self.list.row(item)
        self.button_delete.setDisabled(False)

    def new_entry(self):
        self.list.clearSelection()
        self.index_selected = None
        self.button_delete.setDisabled(True)

    def delete_entry(self):
        list_remove(self)
        self.list.clearSelection()
        self.index_selected = None
        self.button_add_back.setDisabled(False)

    def add_back(self):
        if self.expense_mode:
            expense_list.append(removed_expense.pop(-1))
            q_list_entry = expense_to_Qstring([expense_list[-1]])
            if len(removed_expense) == 0:
                self.button_add_back.setDisabled(True)
        else:
            income_list.append(removed_income.pop(-1))
            q_list_entry = income_to_Qstring([income_list[-1]])
            if len(removed_income) == 0:
                self.button_add_back.setDisabled(True)

        self.list.insertItem(0, QListWidgetItem(q_list_entry[0]))

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
        # Reload categories.
        self.expense_tree.clear()
        self.expense_type_pointer = []  # Load expense categories.
        i = 0
        for category in LevelOrderIter(expense_type):
            self.expense_type_pointer.append(MyTreeWidgetItem())
            self.expense_type_pointer[-1].setText(0, category.name)
            self.expense_type_pointer[-1].anytree_node = category
            category.index = i  # Points from the anytree.Node to the QTreeWidgetItem
            i += 1
        self.next_pointer = i  # For adding new category

        # Connect the nodes in PyQt following anytree.
        for category in LevelOrderIter(expense_type):
            for child_category in category.children:
                self.expense_type_pointer[category.index].addChild(
                    self.expense_type_pointer[child_category.index]
                )

        self.expense_tree.addTopLevelItem(
            self.expense_type_pointer[0]
        )  # The 0th pointer is All Categories

        self.income_tree.clear()
        self.income_type_pointer = []  # Load income categories.
        i = 0
        for category in LevelOrderIter(income_type):
            self.income_type_pointer.append(MyTreeWidgetItem())
            self.income_type_pointer[-1].setText(0, category.name)
            self.income_type_pointer[-1].anytree_node = category
            category.index = i  # Points from the anytree.Node to the QTreeWidgetItem
            i += 1
        self.next_income_pointer = i  # For adding new income category

        # Connect the nodes in PyQt following anytree.
        for category in LevelOrderIter(income_type):
            for child_category in category.children:
                self.income_type_pointer[category.index].addChild(
                    self.income_type_pointer[child_category.index]
                )

        self.income_tree.addTopLevelItem(self.income_type_pointer[0])

        self.expense_tree.setCurrentItem(self.expense_type_pointer[0])
        self.expense_type_pointer[0].setExpanded(True)

        self.income_tree.setCurrentItem(self.income_type_pointer[0])
        self.income_type_pointer[0].setExpanded(True)

        # Reload the list.
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
    date = inputwindow.calender.date().toString("yyyy-MM-dd")
    if inputwindow.expense_mode:
        cost = float(inputwindow.amount.text())
        category = inputwindow.expense_tree.currentItem().text(0)
        notes_q_pair = (
            inputwindow.expense_notes.form_layout
        )  # QFormLayout storing (key, value) for notes.
        notes = {}
        for i in range(notes_q_pair.rowCount()):
            # Get the label item/widget for the row
            label = notes_q_pair.itemAt(i, QFormLayout.ItemRole.LabelRole)
            # Get the field item/widget for the row
            line_entry = notes_q_pair.itemAt(i, QFormLayout.ItemRole.FieldRole)
            notes[label.widget().text()] = line_entry.widget().text()

        if inputwindow.irregular.currentIndex() == -1:
            regular = "Every " + str(inputwindow.spin_period.value()) + " months"
        else:
            regular = inputwindow.irregular.currentText()
        trip = inputwindow.trip_selector.currentText()
        expense_list.append(ExpenseEntry(date, cost, category, notes, regular, trip))
    else:
        amount = float(inputwindow.amount.text())
        category = inputwindow.income_tree.currentItem().text(0)
        note = inputwindow.income_note_entry.text()
        income_list.append(IncomeEntry(date, amount, category, note))

    # Update QListWidget
    if inputwindow.expense_mode:
        q_list_entry = expense_to_Qstring([expense_list[-1]])
    else:
        q_list_entry = income_to_Qstring([income_list[-1]])

    inputwindow.list.insertItem(0, QListWidgetItem(q_list_entry[0]))


def list_remove(inputwindow: InputWindow):
    # Put item into removed list to be restored
    if inputwindow.expense_mode:
        # Convert the index since the order of two lists are reversed
        index = len(expense_list) - 1 - inputwindow.index_selected
        removed_expense.append(expense_list.pop(index))
        # Update trip list
        global trip_list
        trip_list = get_trip_list(expense_list)
    else:
        # Convert the index since the order of two lists are reversed
        index = len(income_list) - 1 - inputwindow.index_selected
        removed_income.append(income_list.pop(index))

    # Update QListWidget, need to do this after the above because the removing row in q_list will update the idex
    q_list_entry = inputwindow.list.takeItem(inputwindow.index_selected)
    del q_list_entry


class CategoriesWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.expense_mode = True
        self.switch_x = 200
        self.switch_y = 20
        self.initUI()

    def initUI(self):
        self.init_expense_income_switch()
        self.init_category_tree()
        self.init_button_delete()

    def init_expense_income_switch(self):
        self.label_switch_expense = QLabel("Expense", self)
        self.label_switch_expense.setGeometry(self.switch_x, self.switch_y, 230, 40)

        self.label_switch_expense.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_switch_expense.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 20px;"
        )

        self.label_switch_income = QLabel("Income", self)
        self.label_switch_income.setGeometry(self.switch_x + 230, self.switch_y, 95, 30)
        self.label_switch_income.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_switch_income.setStyleSheet(
            "background-color: #ecffe6;font-size: 16px;"
        )

        self.switch = QCheckBox("", self)
        self.switch.setGeometry(self.switch_x + 230, self.switch_y, 95, 30)
        self.switch.setStyleSheet(
            """
                                  QCheckBox::indicator{
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
        )

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
            self.expense_tree.clearSelection()
            self.button_delete.setDisabled(True)

    def init_category_tree(self):
        self.expense_type_pointer = []  # Load expense categories.
        i = 0
        for category in LevelOrderIter(expense_type):
            self.expense_type_pointer.append(MyTreeWidgetItem())
            self.expense_type_pointer[-1].setText(0, category.name)
            self.expense_type_pointer[-1].anytree_node = category
            category.index = i  # Points from the anytree.Node to the QTreeWidgetItem
            i += 1
        self.next_pointer = i  # For adding new category

        # Connect the nodes in PyQt following anytree.
        for category in LevelOrderIter(expense_type):
            for child_category in category.children:
                self.expense_type_pointer[category.index].addChild(
                    self.expense_type_pointer[child_category.index]
                )

        self.expense_tree = QTreeWidget(self)
        self.expense_tree.setStyleSheet("font-size: 18px;")
        self.expense_tree.setColumnCount(1)
        self.expense_tree.setGeometry(40, self.switch_y + 50, 324, 200)
        self.expense_tree.setHeaderHidden(True)
        self.expense_tree.addTopLevelItem(
            self.expense_type_pointer[0]
        )  # The 0th pointer is All Categories
        self.expense_type_pointer[0].setExpanded(True)

        self.expense_tree.itemClicked.connect(self.category_selected)

        self.income_type_pointer = []  # Load income categories.
        i = 0
        for category in LevelOrderIter(income_type):
            self.income_type_pointer.append(MyTreeWidgetItem())
            self.income_type_pointer[-1].setText(0, category.name)
            self.income_type_pointer[-1].anytree_node = category
            category.index = i  # Points from the anytree.Node to the QTreeWidgetItem
            i += 1
        self.next_income_pointer = i  # For adding new income category

        # Connect the nodes in PyQt following anytree.
        for category in LevelOrderIter(income_type):
            for child_category in category.children:
                self.income_type_pointer[category.index].addChild(
                    self.income_type_pointer[child_category.index]
                )

        self.income_tree = QTreeWidget(self)
        self.income_tree.setStyleSheet("font-size: 18px;")
        self.income_tree.setColumnCount(1)
        self.income_tree.setGeometry(40, self.switch_y + 50, 324, 200)
        self.income_tree.setHeaderHidden(True)
        self.income_tree.addTopLevelItem(self.income_type_pointer[0])
        self.income_type_pointer[0].setExpanded(True)
        self.income_tree.setVisible(False)

        self.income_tree.itemClicked.connect(self.category_selected)

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
        self.expense_tree.clear()
        self.expense_type_pointer = []  # Load expense categories.
        i = 0
        for category in LevelOrderIter(expense_type):
            self.expense_type_pointer.append(MyTreeWidgetItem())
            self.expense_type_pointer[-1].setText(0, category.name)
            self.expense_type_pointer[-1].anytree_node = category
            category.index = i  # Points from the anytree.Node to the QTreeWidgetItem
            i += 1
        self.next_pointer = i  # For adding new category

        # Connect the nodes in PyQt following anytree.
        for category in LevelOrderIter(expense_type):
            for child_category in category.children:
                self.expense_type_pointer[category.index].addChild(
                    self.expense_type_pointer[child_category.index]
                )

        self.expense_tree.addTopLevelItem(
            self.expense_type_pointer[0]
        )  # The 0th pointer is All Categories
        self.expense_type_pointer[0].setExpanded(True)

        self.income_tree.clear()
        self.income_type_pointer = []  # Load income categories.
        i = 0
        for category in LevelOrderIter(income_type):
            self.income_type_pointer.append(MyTreeWidgetItem())
            self.income_type_pointer[-1].setText(0, category.name)
            self.income_type_pointer[-1].anytree_node = category
            category.index = i  # Points from the anytree.Node to the QTreeWidgetItem
            i += 1
        self.next_income_pointer = i  # For adding new income category

        # Connect the nodes in PyQt following anytree.
        for category in LevelOrderIter(income_type):
            for child_category in category.children:
                self.income_type_pointer[category.index].addChild(
                    self.income_type_pointer[child_category.index]
                )

        self.income_tree.addTopLevelItem(self.income_type_pointer[0])
        self.income_type_pointer[0].setExpanded(True)

    def init_button_delete(self):
        self.button_delete = QPushButton("Delete", self)
        self.button_delete.setGeometry(self.switch_x + 240, self.switch_y + 90, 120, 60)
        self.button_delete.setStyleSheet("font-size: 20px;")
        self.button_delete.setDisabled(True)

        self.button_delete.clicked.connect(self.delete_category)

    def delete_category(self):
        self.button_delete.setDisabled(True)

        # Update the anytree cateogry tree
        if self.expense_mode:
            current_category = self.expense_tree.currentItem().anytree_node

            # Update the entries in the deleted category
            parent_name = current_category.parent.name
            for entry in expense_list:
                if entry.category == current_category.name:
                    entry.category = parent_name

            current_category.parent = None

            # Update the PyQt tree
            current_item = self.expense_tree.currentItem()
            parent = current_item.parent()
            parent.removeChild(current_item)
        else:
            current_category = self.income_tree.currentItem().anytree_node

            # Update the entries in the deleted category
            parent_name = current_category.parent.name
            for entry in income_list:
                if entry.category == current_category.name:
                    entry.category = parent_name

            current_category.parent = None

            # Update the PyQt tree
            current_item = self.income_tree.currentItem()
            parent = current_item.parent()
            parent.removeChild(current_item)

        if self.expense_mode:
            self.expense_tree.clearSelection()
        else:
            self.income_tree.clearSelection()


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
            regular_category = []
            regular_value = []
            not_regular_category = []
            not_regular_value = []
            print("Total spending in each category:")

            for category in PreOrderIter(expense_type_copy):
                print(
                    f"{len(category.ancestors) * '   '}{category.name}: ${category.total}"
                )

            for child in expense_type_copy.children:
                if child.regular_total > 0:
                    regular_category.append(child.name + f" ${child.regular_total}")
                    regular_value.append(child.regular_total)
                if child.not_regular_total > 0:
                    not_regular_category.append(
                        child.name + f" ${child.not_regular_total}"
                    )
                    not_regular_value.append(child.not_regular_total)

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
                if "quantity (weight)" in category.notes:
                    print("-" * 100)
                    cheapest_per_lb = -1
                    most_expensive = 0
                    total_weight = 0
                    total_cost = 0
                    i = -1
                    for entry in expense_list_for_summary:
                        i += 1
                        if entry.category == category.name:
                            weight_in_lb = Q_(entry.notes["quantity (weight)"]).to("lb")
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
                center_value = [sum(regular_value), sum(not_regular_value)]
                ax1 = self.figure.add_subplot(1, 3, 1)
                ax2 = self.figure.add_subplot(1, 3, 2)
                ax3 = self.figure.add_subplot(1, 3, 3)
                try:
                    ax1.pie(
                        regular_value,
                        labels=regular_category,
                        autopct="%1.1f%%",
                        radius=0.7,
                    )
                except ValueError:
                    print("No regular expenses.")
                else:
                    ax1.set_title(f"Regular ${expense_type_copy.regular_total}")
                try:
                    ax2.pie(center_value, autopct="%1.1f%%", startangle=90, radius=0.7)
                except ValueError:
                    print("No expenses.")
                else:
                    ax2.set_title(f"Total Spending\n${expense_type_copy.total}")
                try:
                    ax3.pie(
                        not_regular_value,
                        labels=not_regular_category,
                        autopct="%1.1f%%",
                        radius=0.7,
                    )
                except ValueError:
                    print("No non-regular expenses.")
                else:
                    ax3.set_title(f"Not regular ${expense_type_copy.not_regular_total}")

        self.canvas.draw()


class PeriodicWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        QLabel("The Periodic Expenses page is under construction", self)


app = QApplication(sys.argv)
main_window = MainWindow()
main_window.setWindowTitle("Money Tracker")
main_window.setGeometry(500, 100, 790, 720)
main_window.setFixedHeight(720)

main_window.show()
sys.exit(app.exec())
