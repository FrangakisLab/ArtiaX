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
    QGroupBox, QRadioButton, QPushButton


class GenerateInSurfaceOptions(QWidget):
    """
    Widget for generating points in surface.

    """

    valueChanged = Signal()
    buttonPressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._method = 'uniform'
        self._num_pts = 100
        self._radius = 100

        layout = QVBoxLayout()
        from .NLabelValue import NLabelValue
        from .RadioButtonsStringOptions import RadioButtonsStringOptions
        self.method_buttons = RadioButtonsStringOptions('Method', ["Uniform", 'Poisson Disk', 'Regular Grid'])
        self.options_edits = NLabelValue(['Number of Points', 'Radius [Angstrom]'], only_pos_values=True)
        self.generate_button = QPushButton("Generate Points in Surface")
        layout.addWidget(self.method_buttons)
        layout.addWidget(self.options_edits)
        layout.addWidget(self.generate_button)

        self.setLayout(layout)
        self.options_edits.disable_fields([0], False)
        self.options_edits.disable_fields([1], True)
        self._connect()

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, v):
        self.method_buttons.blockSignals(True)
        self.options_edits.blockSignals(True)
        if v.lower() == 'uniform':
            self.options_edits.disable_fields([0], False)
            self.options_edits.disable_fields([1], True)
            self.method_buttons.set_value_checked('Uniform')
        elif v.lower() == 'poisson':
            self.options_edits.disable_fields([0], True)
            self.options_edits.disable_fields([1], False)
            self.method_buttons.set_value_checked('Poisson Disk')
        else:
            self.options_edits.disable_fields([0], False)
            self.options_edits.disable_fields([1], True)
            self.method_buttons.set_value_checked('Regular Grid')
        self.options_edits.blockSignals(False)
        self.method_buttons.blockSignals(False)
        self._method = v.lower()

    @property
    def num_pts(self):
        return int(self._num_pts)

    @num_pts.setter
    def num_pts(self, value):
        self._num_pts = value
        self.options_edits.blockSignals(True)
        self.options_edits.set_value(0, value)
        self.options_edits.blockSignals(False)

    @property
    def radius(self):
        return float(self._radius)

    @radius.setter
    def radius(self, value):
        self._radius = value
        self.options_edits.blockSignals(True)
        self.options_edits.set_value(1, value)
        self.options_edits.blockSignals(False)

    def _connect(self):
        """Connect child signals."""
        self.method_buttons.valueChanged.connect(self._method_changed)
        self.options_edits.valueChanged.connect(self._options_changed)
        self.generate_button.clicked.connect(self._generate_pressed)

    def _method_changed(self, value):
        if value.lower() == 'poisson disk':
            value = 'poisson'
        self.method = value
        self._emit_value_changed()

    def _options_changed(self, values):
        self._num_pts = int(values[0])
        self._radius = float(values[1])
        self._emit_value_changed()

    def _generate_pressed(self):
        self.buttonPressed.emit()

    def _emit_value_changed(self):
        self.valueChanged.emit()

