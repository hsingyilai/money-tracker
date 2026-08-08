from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
import sys


app = QApplication(sys.argv)
top_widget = QWidget()
top_label = QLabel("Hi", top_widget)

bottom_widget = QWidget()
bottom_label = QLabel("Hello", bottom_widget)

layout = QVBoxLayout()
layout.addWidget(top_widget)
layout.addWidget(bottom_widget)

main_widget = QWidget()
main_widget.setLayout(layout)

main_widget.show()
sys.exit(app.exec())
