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


class AutoManualWidget(QWidget):
    """
    Widget providing radio buttons for auto/manual choice, where checking the manual button enables a text field.

    """

    valueChanged = Signal()

    def __init__(self, name, parent=None):
        super().__init__(parent=parent)

        self._auto = True
        self._value = 0

        layout = QHBoxLayout()
        label = QLabel(name)
        self.auto_button = QRadioButton("Auto")
        self.manual_button = QRadioButton("Manual")
        self.value_field = QLineEdit()
        layout.addWidget(label)
        layout.addWidget(self.auto_button)
        layout.addWidget(self.manual_button)
        layout.addWidget(self.value_field)

        self.setLayout(layout)
        self._connect()

    @property
    def auto(self):
        return self._auto

    @auto.setter
    def auto(self, auto):
        self._auto = auto
        self.auto_button.blockSignals(True)
        self.manual_button.blockSignals(True)
        self.manual_button.setChecked(not auto)
        self.auto_button.setChecked(auto)
        self.value_field.blockSignals(True)
        self.value_field.setEnabled(not auto)
        self.value_field.blockSignals(False)
        self.auto_button.blockSignals(False)
        self.manual_button.blockSignals(False)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.value_field.blockSignals(True)
        self.value_field.setText(str(value))
        self.value_field.blockSignals(False)

    def _connect(self):
        """Connect child signals."""
        self.auto_button.toggled.connect(self._button_pressed)
        self.manual_button.toggled.connect(self._button_pressed)
        self.value_field.editingFinished.connect(self._value_changed)

    def _button_pressed(self):
        self._auto = self.auto_button.isChecked()
        self.value_field.blockSignals(True)
        self.value_field.setEnabled(not self.auto_button.isChecked())
        self.value_field.blockSignals(False)
        self._emit_value_changed()

    def _value_changed(self):
        value = self.value_field.text()
        self._value = float(value)
        self._emit_value_changed()

    def _emit_value_changed(self):
        self.valueChanged.emit()
