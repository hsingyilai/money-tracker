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
)
from PyQt6 import QtWidgets
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QDoubleValidator
import sys
import json
from anytree.importer import JsonImporter
from anytree import LevelOrderIter
from datetime import datetime


# define a QDate object for today
qtoday = QDate(datetime.now().year, datetime.now().month, datetime.now().day)

# load the list datas
with open("my_expenses.json", "r") as f:
    expense_list = json.load(f)

with open("my_incomes.json", "r") as f:
    income_list = json.load(f)

# load the categories
importer = JsonImporter()
with open("expense_categories.json", "r") as f:
    expense_type = importer.read(f)

with open("income_categories.json", "r") as f:
    income_type = importer.read(f)


class MainWidget(QtWidgets.QStackedWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        window_input = InputWindow()
        window_categories = CategoriesWindow()
        window_summary = SummaryWindow()

        self.addWidget(window_input)
        self.addWidget(window_categories)
        self.addWidget(window_summary)
        self.setGeometry(600, 200, 740, 700)
        self.setFixedHeight(700)
        self.setFixedWidth(740)

        self.setWindowTitle("Money Tracker")

    def closeEvent(self, event):
        with open("my_expenses.json", "w") as f:
            json.dump(expense_list, f, indent=4)

        with open("my_incomes.json", "w") as f:
            json.dump(income_list, f, indent=4)

        event.accept()
        super().closeEvent(event)


class InputWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()
        self.expense_mode = True

    def initUI(self):
        self.switch_x = 40
        self.switch_y = 30
        self.init_expense_income_switch()
        self.init_select_date()
        self.init_amount()
        self.init_irregular()
        self.init_category_tree()
        self.init_add_subcategory()
        self.init_button_submit()
        self.init_list()
        self.init_label_input()
        self.init_button_categories()
        self.init_button_summary()

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
            self.list.addItems(income_list)
            self.expense_mode = False
            self.income_tree.setVisible(True)
            self.expense_tree.setVisible(False)
            self.label_amount.setText("Income:    $")
            self.irregular.setVisible(False)
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
            self.list.addItems(expense_list)
            self.expense_mode = True
            self.income_tree.setVisible(False)
            self.expense_tree.setVisible(True)
            self.label_amount.setText("Expense: $")
            self.irregular.setVisible(True)

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
        validator = QDoubleValidator(0.00, 999999.99, 2)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.amount.setValidator(validator)

    def init_irregular(self):
        self.irregular = QCheckBox("Irregular", self)
        self.irregular.setGeometry(270, 128, 200, 40)
        self.irregular.setStyleSheet("font-size: 18px;")

    def init_category_tree(self):
        self.expense_type_pointer = []  # Load expense categories.
        i = 0
        for category in LevelOrderIter(expense_type):
            self.expense_type_pointer.append(QTreeWidgetItem([category.name]))
            category.index = i
            i += 1

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
        self.expense_tree.addTopLevelItem(self.expense_type_pointer[0])
        self.expense_tree.setCurrentItem(self.expense_type_pointer[0])
        self.expense_type_pointer[0].setExpanded(True)

        self.income_type_pointer = []  # Load income categories.
        i = 0
        for category in LevelOrderIter(income_type):
            self.income_type_pointer.append(QTreeWidgetItem([category.name]))
            category.index = i
            i += 1

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

    def init_add_subcategory(self):
        self.new_category = QLineEdit(self)
        self.new_category.setGeometry(self.switch_x, self.switch_y + 320, 200, 30)
        self.new_category.setPlaceholderText("new subcategory")
        self.add_category = QPushButton("Add", self)
        self.add_category.setEnabled(False)
        self.add_category.setGeometry(self.switch_x + 210, self.switch_y + 315, 114, 40)

        self.new_category.textChanged.connect(self.entering_category)
        self.add_category.clicked.connect(self.add_new_category)

    def entering_category(self):
        self.add_category.setEnabled(True)

    def add_new_category(self):
        self.new_category.clear()
        self.add_category.setEnabled(False)

    def init_button_submit(self):
        self.button_submit = QPushButton("Submit", self)
        self.button_submit.setGeometry(40, 530, 325, 45)
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
        list_add(expense_list, income_list, self)
        self.amount.clear()

    def init_list(self):
        self.list = QListWidget(self)
        self.list.setGeometry(380, 30, 325, 545)
        self.list.addItems(expense_list)
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

    def init_label_input(self):
        self.label_input = QLabel("Input", self)
        self.label_input.setGeometry(40, 590, 110, 70)
        self.label_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_input.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 18px;"
        )

    def init_button_categories(self):
        self.button_categories = QPushButton("Categories", self)
        self.button_categories.setGeometry(150, 600, 110, 60)
        self.button_categories.setStyleSheet("font-size: 18px;")

        self.button_categories.clicked.connect(self.go_to_categories)

    def init_button_summary(self):
        self.button_summary = QPushButton("Summary", self)
        self.button_summary.setGeometry(260, 600, 110, 60)
        self.button_summary.setStyleSheet("font-size: 18px;")

        self.button_summary.clicked.connect(self.go_to_summary)

    def go_to_categories(self):
        widget.setCurrentIndex(1)

    def go_to_summary(self):
        widget.setCurrentIndex(2)


# wrap list editing into a single function to prevent mistake
def list_add(expense_list, income_list, inputwindow: InputWindow):
    entry = inputwindow.calender.date().toString("MM/dd/yyyy")
    text = inputwindow.amount.text()
    if not text:
        inputwindow.amount.setText("0.00")

    try:
        # Convert to float and format to 2 decimal places
        value = float(text)
        inputwindow.amount.setText(f"{value:.2f}")
    except ValueError:
        inputwindow.amount.setText("0.00")

    if inputwindow.expense_mode:
        if inputwindow.irregular.isChecked():
            entry += "  Irregular"
        entry += "\n$" + inputwindow.amount.text() + "  "
        entry += inputwindow.expense_tree.currentItem().text(0)

        expense_list.insert(0, entry)
    else:
        entry += "\n$" + inputwindow.amount.text() + "  "
        entry += inputwindow.income_tree.currentItem().text(0)
        income_list.insert(0, entry)

    inputwindow.list.insertItem(0, QListWidgetItem(entry))


class CategoriesWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.init_button_input()
        self.init_label_categories()
        self.init_button_summary()

    def init_button_input(self):
        self.button_input = QPushButton("Input", self)
        self.button_input.setGeometry(40, 600, 110, 60)
        self.button_input.setStyleSheet("font-size: 18px;")

        self.button_input.clicked.connect(self.go_to_input)

    def init_label_categories(self):
        self.label_categories = QLabel("Categories", self)
        self.label_categories.setGeometry(150, 590, 110, 70)
        self.label_categories.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_categories.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 18px"
        )

    def init_button_summary(self):
        self.button_summary = QPushButton("Summary", self)
        self.button_summary.setGeometry(260, 600, 110, 60)
        self.button_summary.setStyleSheet("font-size: 18px;")

        self.button_summary.clicked.connect(self.go_to_summary)

    def go_to_input(self):
        widget.setCurrentIndex(0)

    def go_to_summary(self):
        widget.setCurrentIndex(2)


class SummaryWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.init_button_input()
        self.init_button_categories()
        self.init_label_summary()

    def init_button_input(self):
        self.button_input = QPushButton("Input", self)
        self.button_input.setGeometry(40, 600, 110, 60)
        self.button_input.setStyleSheet("font-size: 18px;")

        self.button_input.clicked.connect(self.go_to_input)

    def init_button_categories(self):
        self.button_categories = QPushButton("Categories", self)
        self.button_categories.setGeometry(150, 600, 110, 60)
        self.button_categories.setStyleSheet("font-size: 18px;")

        self.button_categories.clicked.connect(self.go_to_categories)

    def init_label_summary(self):
        self.label_summary = QLabel("Summary", self)
        self.label_summary.setGeometry(260, 590, 110, 70)
        self.label_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_summary.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 18px"
        )

    def go_to_input(self):
        widget.setCurrentIndex(0)

    def go_to_categories(self):
        widget.setCurrentIndex(1)


app = QApplication(sys.argv)
widget = MainWidget()

widget.show()
sys.exit(app.exec())
