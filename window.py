from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QCalendarWidget
from PyQt6 import QtWidgets
import sys
from datetime import datetime
from PyQt6.QtCore import QDate

# define a QDate object for today
qtoday = QDate(datetime.now().year, datetime.now().month, datetime.now().day)


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.create_widgets()

    def create_widgets(self):
        self.button = QPushButton("window", self)
        self.button.setGeometry(100, 100, 100, 100)

        self.button.clicked.connect(self.go_to_window2)

        self.calender = QCalendarWidget(self)
        self.calender.setGeometry(100, 300, 400, 300)
        self.calender.setSelectedDate(qtoday)

        self.calender.clicked.connect(lambda dateval: print(dateval))

    def go_to_window2(self):
        widget.setCurrentIndex(widget.currentIndex() + 1)


class Window2(QWidget):
    def __init__(self):
        super().__init__()

        self.create_widgets()

    def create_widgets(self):
        self.button = QPushButton("window 2", self)
        self.button.setGeometry(300, 100, 100, 100)

        self.button.clicked.connect(self.go_to_window2)

    def go_to_window2(self):
        widget.setCurrentIndex(widget.currentIndex() - 1)
        window.calender.setSelectedDate(qtoday)


app = QApplication(sys.argv)
widget = QtWidgets.QStackedWidget()
window = Window()
window2 = Window2()

widget.addWidget(window)
widget.addWidget(window2)
widget.setGeometry(600, 200, 600, 700)

widget.setWindowTitle("Simple Window Switcher")


widget.show()
sys.exit(app.exec())
