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
    Widget providing radio buttons for cutoff methods and text fields for pass and decay frequencies.

    """

    valueChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._method = 'uniform'
        self._num_pts = 100
        self._radius = 10

        layout = QVBoxLayout()
        from .NLabelValue import NLabelValue
        from .RadioButtonsStringOptions import RadioButtonsStringOptions
        self.method_buttons = RadioButtonsStringOptions('Method', ["Uniform", 'Poisson Disk', 'Regular Grid'])
        self.options_edits = NLabelValue(['Number of Points', 'Radius'], only_pos_values=True)
        self.generate_button = QPushButton("Generate Points")
        layout.addWidget(self.method_buttons)
        layout.addWidget(self.options_edits)
        layout.addWidget(self.generate_button)

        self.setLayout(layout)
        self._connect()

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, v):
        self.method_buttons.blockSignals(True)
        self.method_buttons.set_value_checked(v)
        self.method_buttons.blockSignals(False)
        self._method = v

    @property
    def num_pts(self):
        return float(self._num_pts)

    @num_pts.setter
    def num_pts(self, value):
        self._num_pts = value
        self.pf_edit.blockSignals(True)
        self.pf_edit.set_value(0, value)
        self.pf_edit.blockSignals(False)

    @property
    def decay_freq(self):
        return float(self._decay_freq)

    @decay_freq.setter
    def decay_freq(self, value):
        self._decay_freq = value
        self.decay_edit.blockSignals(True)
        self.decay_edit.value = value
        self.decay_edit.blockSignals(False)

    @property
    def auto_decay(self):
        return self._auto_decay

    @auto_decay.setter
    def auto_decay(self, auto):
        self._auto_decay = auto
        self.decay_edit.blockSignals(True)
        self.decay_edit.auto = auto
        self.decay_edit.blockSignals(False)

    def _connect(self):
        """Connect child signals."""
        self.decay_method_buttons.valueChanged.connect(self._method_changed)
        self.pf_edit.valueChanged.connect(self._pf_changed)
        self.decay_edit.valueChanged.connect(self._decay_changed)

    def _method_changed(self, value):
        self._cutoff = value
        self._emit_value_changed()

    def _pf_changed(self, value):
        self._pass_freq = value[0].lower()
        self._emit_value_changed()

    def _decay_changed(self):
        self._auto_decay = self.decay_edit.auto
        self._decay_freq = self.decay_edit.value
        self._emit_value_changed()

    def _emit_value_changed(self):
        self.valueChanged.emit()
