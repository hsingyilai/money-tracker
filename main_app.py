from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QDateEdit, QLabel
from PyQt6 import QtWidgets
import sys
from datetime import datetime
from PyQt6.QtCore import QDate, Qt

# define a QDate object for today
qtoday = QDate(datetime.now().year, datetime.now().month, datetime.now().day)


class InputWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.label_input = QLabel("Input", self)
        self.label_input.setGeometry(40, 590, 110, 70)
        self.label_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_input.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 18px;"
        )

        self.button_categories = QPushButton("Categories", self)
        self.button_categories.setGeometry(160, 590, 110, 70)
        self.button_categories.setStyleSheet("font-size: 18px;")

        self.button_categories.clicked.connect(self.go_to_categories)

        self.button_summary = QPushButton("Summary", self)
        self.button_summary.setGeometry(280, 590, 110, 70)
        self.button_summary.setStyleSheet("font-size: 18px;")

        self.button_summary.clicked.connect(self.go_to_summary)

        self.calender = QDateEdit(self)
        self.calender.setGeometry(90, 200, 200, 40)
        self.calender.setDate(qtoday)
        self.calender.setStyleSheet("font-size: 20px;")

        self.label_date = QLabel("Date:", self)
        self.label_date.setGeometry(40, 200, 50, 40)
        self.label_date.setStyleSheet("font-size: 20px;")

        self.button_submit = QPushButton("Submit", self)
        self.button_submit.setGeometry(40, 510, 230, 45)
        self.button_submit.setStyleSheet("""
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
                                    """)

    def go_to_categories(self):
        widget.setCurrentIndex(1)

    def go_to_summary(self):
        widget.setCurrentIndex(2)


class CategoriesWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.button_input = QPushButton("Input", self)
        self.button_input.setGeometry(40, 590, 110, 70)
        self.button_input.setStyleSheet("font-size: 18px;")

        self.button_input.clicked.connect(self.go_to_input)

        self.label_categories = QLabel("Categories", self)
        self.label_categories.setGeometry(160, 590, 110, 70)
        self.label_categories.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_categories.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 18px"
        )

        self.button_summary = QPushButton("Summary", self)
        self.button_summary.setGeometry(280, 590, 110, 70)
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
        self.button_input = QPushButton("Input", self)
        self.button_input.setGeometry(40, 590, 110, 70)
        self.button_input.setStyleSheet("font-size: 18px;")

        self.button_input.clicked.connect(self.go_to_input)

        self.label_summary = QLabel("Summary", self)
        self.label_summary.setGeometry(280, 590, 110, 70)
        self.label_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_summary.setStyleSheet(
            "background-color: #41e8a0;font-weight: bold;font-size: 18px"
        )

        self.button_categories = QPushButton("Categories", self)
        self.button_categories.setGeometry(160, 590, 110, 70)
        self.button_categories.setStyleSheet("font-size: 18px;")

        self.button_categories.clicked.connect(self.go_to_categories)

    def go_to_input(self):
        widget.setCurrentIndex(0)

    def go_to_categories(self):
        widget.setCurrentIndex(1)


app = QApplication(sys.argv)
widget = QtWidgets.QStackedWidget()
window_input = InputWindow()
window_categories = CategoriesWindow()
window_summary = SummaryWindow()

widget.addWidget(window_input)
widget.addWidget(window_categories)
widget.addWidget(window_summary)
widget.setGeometry(600, 200, 800, 700)

widget.setWindowTitle("Money Tracker")


widget.show()
sys.exit(app.exec())
