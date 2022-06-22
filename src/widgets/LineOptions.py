# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
import numpy as np
from functools import partial

# Qt
from Qt.QtCore import Qt, Signal
from Qt.QtGui import QColor
from Qt.QtWidgets import (
    QWidget,
    QStackedLayout,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QToolButton,
    QGroupBox,
    QLabel,
    QLineEdit,
    QLayout,
    QSizePolicy
)

# This package
from .LabelEditSlider import LabelEditSlider
from .LabelEditRangeSlider import LabelEditRangeSlider


class LineOptions(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.line = None

        self.layout = QVBoxLayout()
        self.line_options_label = QLabel("Line Options")
        self.layout.addWidget(self.line_options_label)

        self.spacing_checkbox = QGroupBox("Populate line with evenly spaced particles:")
        self.spacing_checkbox.setCheckable(True)
        self.spacing_checkbox.setChecked(False)


        self.spacing_checkbox_layout = QVBoxLayout()
        self.spacing_slider = LabelEditRangeSlider((1, 100), "Spacing [Å]:", min=0.1)
        self.spacing_checkbox_layout.addWidget(self.spacing_slider)

        self.create_particle_button = QPushButton("Create particles")
        self.spacing_checkbox_layout.addWidget(self.create_particle_button)

        self.spacing_checkbox_layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.spacing_checkbox.setLayout(self.spacing_checkbox_layout)

        self.layout.addWidget(self.spacing_checkbox)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self._connect()

    def set_line(self, line):
        self.spacing_slider.blockSignals(True)
        if self.line is not None:
            self.spacing_checkbox.setChecked(line.has_particles)
            self.spacing_slider.set_range(line.spacing_edit_range)
            self.spacing_slider.value = line.spacing
        else:
            line.spacing_edit_range = self.spacing_slider.get_range()
            line.spacing = self.spacing_slider.value
        self.spacing_slider.blockSignals(False)
        self.line = line

    def _connect(self):
        self.spacing_checkbox.clicked.connect(self._toggled)
        self.spacing_slider.valueChanged.connect(self._value_changed)
        #self.spacing_slider.editingFinished.connect(self._range_changed)
        self.create_particle_button.clicked.connect(self._create_particles)

    def _toggled(self):
        if self.spacing_checkbox.isChecked():
            if not self.line.has_particles:
                self.line.spacing = self.spacing_slider.value
                self.line.spacing_edit_range = self.spacing_slider.get_range()
                self.line.create_spheres()
        else:
            if self.line.has_particles:
                self.line.remove_spheres()

    def _value_changed(self):
        if self.line.has_particles:
            self.line.spacing = self.spacing_slider.value
            self.line.create_spheres()
            self.line.spacing_edit_range = self.spacing_slider.get_range()

    def _range_changed(self):
        print("range changed")
        if self.spacing_checkbox.isChecked():
            self.line.spacing_edit_range = self.spacing_slider.get_range()

    def _create_particles(self):
        if self.spacing_checkbox.isChecked():
            self.line.create_particle_list()
