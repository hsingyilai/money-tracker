from PyQt6.QtWidgets import QApplication, QWidget, QPushButton
from PyQt6 import QtWidgets
import sys


class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.create_widgets()

    def create_widgets(self):
        button = QPushButton("window", self)
        button.setGeometry(100, 100, 100, 100)

        button.clicked.connect(self.go_to_window2)

    def go_to_window2(self):
        widget.setCurrentIndex(widget.currentIndex() + 1)


class Window2(QWidget):
    def __init__(self):
        super().__init__()

        self.create_widgets()

    def create_widgets(self):
        button = QPushButton("window 2", self)
        button.setGeometry(300, 100, 100, 100)

        button.clicked.connect(self.go_to_window2)

    def go_to_window2(self):
        widget.setCurrentIndex(widget.currentIndex() - 1)


app = QApplication(sys.argv)
widget = QtWidgets.QStackedWidget()
window = Window()
window2 = Window2()

widget.addWidget(window)
widget.addWidget(window2)
widget.setGeometry(600, 300, 500, 300)

widget.setWindowTitle("Simple Window Switcher")

widget.show()
sys.exit(app.exec())
