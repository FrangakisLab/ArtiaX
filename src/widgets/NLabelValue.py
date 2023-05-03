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


class NLabelValue(QWidget):
    """
    Widget providing labels with accompanying value fields.

    """

    valueChanged = Signal(list)

    def __init__(self, labels, only_pos_values=True, parent=None):
        super().__init__(parent=parent)

        self._num_fields = len(labels)
        self._labels = []
        self._fields = []
        self._values = [0 for i in range(self._num_fields)]

        layout = QHBoxLayout()
        for label in labels:
            label_widget = QLabel(label)
            field_widget = QLineEdit()
            field_widget.setText(str(0))
            self._labels.append(label_widget)
            self._fields.append(field_widget)
            layout.addWidget(label_widget)
            layout.addWidget(field_widget)

        self.setLayout(layout)
        self._connect()

    @property
    def num_options(self):
        return self._num_fields

    @property
    def values(self):
        return self._values

    @property
    def labels(self):
        return [label.text() for label in self._labels]

    def _connect(self):
        """Connect child signals."""
        for field in self._fields:
            field.editingFinished.connect(self._field_changed)

    def _field_changed(self):
        for i, field in enumerate(self._fields):
            if not is_float(field.text()) or float(field.text()) < 0:
                field.blockSignals(True)
                field.setText(str(self.values[i]))
                field.blockSignals(False)

        self._values = [field.text() for field in self._fields]

        self._emit_value_changed()

    def _emit_value_changed(self):
        self.valueChanged.emit(self._values)

def is_float(s):
    """Return true if text convertible to float."""
    try:
        float(s)
        return True
    except ValueError:
        return False
