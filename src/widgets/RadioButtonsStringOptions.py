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


class RadioButtonsStringOptions(QWidget):
    """
    Widget providing radio buttons for each option given.

    """

    valueChanged = Signal(str)

    def __init__(self, label, options, parent=None):
        super().__init__(parent=parent)

        self._num_options = len(options)
        self._buttons = []

        layout = QHBoxLayout()
        label = QLabel(label)
        layout.addWidget(label)
        for option in options:
            button = QRadioButton(option)
            self._buttons.append(button)
            layout.addWidget(button)
            button.setChecked(False)

        self._buttons[0].setChecked(True)
        self._value = self._buttons[0].text()

        self.setLayout(layout)
        self._connect()

    @property
    def num_options(self):
        return self._num_options

    @property
    def value(self):
        return self._value

    def set_value_checked(self, value):
        self.uncheck()
        for button in self._buttons:
            if value.lower() == button.text().lower():
                button.blockSignals(True)
                button.setChecked(True)
                button.blockSignals(False)
            continue

    def _connect(self):
        """Connect child signals."""
        for button in self._buttons:
            button.toggled.connect(self._button_pressed)

    def _button_pressed(self):
        for button in self._buttons:
            if button.isChecked():
                self._value = button.text()
                break
        self._emit_value_changed()

    def uncheck(self):
        for button in self._buttons:
            button.setChecked(False)

    def _emit_value_changed(self):
        self.valueChanged.emit(self._value)
