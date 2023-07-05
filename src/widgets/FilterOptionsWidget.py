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


class FilterOptionsWidget(QWidget):
    """
    Widget providing radio buttons for cutoff methods and text fields for pass and decay frequencies.

    """

    valueChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self._cutoff = 'gaussian'
        self._pass_freq = 0
        self._decay_freq = 0

        layout = QVBoxLayout()
        from .NLabelValue import NLabelValue
        from .RadioButtonsStringOptions import RadioButtonsStringOptions
        self.decay_method_buttons = RadioButtonsStringOptions('Decay', ["Gaussian", 'Raised Cosine', 'Box'])
        self.pf_and_decay_edits = NLabelValue(['Pass Frequency', 'Decay Size'], only_pos_values=True)
        layout.addWidget(self.decay_method_buttons)
        layout.addWidget(self.pf_and_decay_edits)

        self.setLayout(layout)
        self._connect()

    @property
    def cutoff(self):
        return self._cutoff

    @cutoff.setter
    def cutoff(self, method):
        self.decay_method_buttons.set_value_checked(method)
        self._cutoff = method

    @property
    def pass_freq(self):
        return float(self._pass_freq)

    @pass_freq.setter
    def pass_freq(self, value):
        self.pf_and_decay_edits.set_value(0, value)

    @property
    def decay_freq(self):
        return float(self._decay_freq)

    @decay_freq.setter
    def decay_freq(self, value):
        self.pf_and_decay_edits.set_value(1, value)

    def _connect(self):
        """Connect child signals."""
        self.decay_method_buttons.valueChanged.connect(self._method_changed)
        self.pf_and_decay_edits.valueChanged.connect(self._pf_and_decay_changed)

    def _method_changed(self, value):
        self._cutoff = value
        self._emit_value_changed()

    def _pf_and_decay_changed(self, values):
        self._pass_freq = values[0].lower()
        self._decay_freq = values[1].lower()
        self._emit_value_changed()

    def _emit_value_changed(self):
        self.valueChanged.emit()
