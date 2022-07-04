# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
import math
from superqt import QDoubleSlider
from functools import partial
import numpy as np

# Qt
from Qt.QtCore import Qt, Signal
from Qt.QtGui import *
from Qt.QtWidgets import QGridLayout, QLabel, QLineEdit, QSizePolicy, QWidget, QLayout, QVBoxLayout, QHBoxLayout, \
    QGroupBox, QRadioButton


class DegreeButtons(QWidget):
    """
    Widget providing three radio buttons.

    """

    valueChanged = Signal(float)

    def __init__(self, max_degree, parent=None):
        super().__init__(parent=parent)

        self._degree = 3
        self._max_degree = max_degree

        layout = QVBoxLayout()

        self._degree_box = QGroupBox("Polynomial degree")
        self._degree_box_layout = QHBoxLayout()
        self._degree_one = QRadioButton("1")
        self._degree_three = QRadioButton("3")
        self._degree_five = QRadioButton("5")
        self._degree_box_layout.addWidget(self._degree_one)
        self._degree_box_layout.addWidget(self._degree_three)
        self._degree_box_layout.addWidget(self._degree_five)
        self._degree_box.setLayout(self._degree_box_layout)
        layout.addWidget(self._degree_box)

        self.setLayout(layout)
        self._connect()

    @property
    def degree(self):
        return self._degree

    @degree.setter
    def degree(self, val):
        self._degree_box.blockSignals(True)
        allowed_values = [1, 3, 5]
        if val in allowed_values:
            self._degree = val

            self._degree_one.setChecked(val == 1)
            self._degree_three.setChecked(val == 3)
            self._degree_five.setChecked(val == 5)
        self._degree_box.blockSignals(False)

        self._emit_value_changed()

    @property
    def max_degree(self):
        return self._max_degree

    @max_degree.setter
    def max_degree(self, val):
        self._degree_box.blockSignals(True)
        self._degree_three.setEnabled(val > 3)
        self._degree_five.setEnabled(val > 5)
        self._degree_box.blockSignals(False)

    def _connect(self):
        """Connect child signals."""
        self._degree_one.clicked.connect(self._button_pressed)
        self._degree_three.clicked.connect(self._button_pressed)
        self._degree_five.clicked.connect(self._button_pressed)

    def _button_pressed(self):
        if self._degree_one.isChecked():
            self.degree = 1
        elif self._degree_three.isChecked():
            self.degree = 3
        elif self._degree_five.isChecked():
            self.degree = 5

    def uncheck(self):
        self._degree_one.setChecked(False)
        self._degree_three.setChecked(False)
        self._degree_five.setChecked(False)

    def _emit_value_changed(self):
        self.valueChanged.emit(self._degree)
