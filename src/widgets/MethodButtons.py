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


class MethodButtons(QWidget):
    """
    Widget providing three radio buttons.

    """

    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._method = 'cubic'

        layout = QVBoxLayout()

        self._method_box = QGroupBox("Fitting method")
        self._method_box_layout = QHBoxLayout()
        self._nearest = QRadioButton("Nearest Neighbor")
        self._linear = QRadioButton("Linear")
        self._cubic = QRadioButton("Cubic")
        self._method_box_layout.addWidget(self._nearest)
        self._method_box_layout.addWidget(self._linear)
        self._method_box_layout.addWidget(self._cubic)
        self._method_box.setLayout(self._method_box_layout)
        layout.addWidget(self._method_box)

        self.setLayout(layout)
        self._connect()

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, val):
        self._method_box.blockSignals(True)
        allowed_values = ['cubic', 'linear', 'nearest']
        if val in allowed_values:
            self._method = val

            self._nearest.setChecked(val == 'nearest')
            self._linear.setChecked(val == 'linear')
            self._cubic.setChecked(val == 'cubic')
        self._method_box.blockSignals(False)

        self.valueChanged.emit(0)

    def _connect(self):
        """Connect child signals."""
        self._nearest.clicked.connect(self._button_pressed)
        self._linear.clicked.connect(self._button_pressed)
        self._cubic.clicked.connect(self._button_pressed)

    def _button_pressed(self):
        if self._nearest.isChecked():
            self.method = 'nearest'
        elif self._linear.isChecked():
            self.method = 'linear'
        elif self._cubic.isChecked():
            self.method = 'cubic'

    def uncheck(self):
        self._nearest.setChecked(False)
        self._linear.setChecked(False)
        self._cubic.setChecked(False)

