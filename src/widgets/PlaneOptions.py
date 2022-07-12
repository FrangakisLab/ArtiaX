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
from .MethodButtons import MethodButtons


class PlaneOptions(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.plane = None

        layout = QVBoxLayout()
        line_options_label = QLabel("Plane Options")
        layout.addWidget(line_options_label)

        self.update_button = QPushButton("Update Plane")
        self.update_button.setToolTip("Updates the plane to fit the particles. Useful when the plane doesn't match the "
                                      "desired plane; simply move the particles that define the plane and press this "
                                      "button to update the plane.")
        layout.addWidget(self.update_button)

        #Fitting options
        self.fitting_checkbox = QGroupBox("Change line fitting:")
        self.fitting_checkbox.setCheckable(True)
        fitting_checkbox_layout = QVBoxLayout()
        self.method_buttons = MethodButtons()
        fitting_checkbox_layout.addWidget(self.method_buttons)
        self.resolution_slider = LabelEditRangeSlider((10, 200), 'Resolution: ', step_size=1, min=1)
        fitting_checkbox_layout.addWidget(self.resolution_slider)
        self.base_checkbox = QGroupBox("Set a base level:")
        self.base_checkbox.setCheckable(True)
        self.base_checkbox.setChecked(False)
        base_checkbox_layout = QVBoxLayout()
        self.base_slider = LabelEditRangeSlider((-10,10), "Base level: ")
        base_checkbox_layout.addWidget(self.base_slider)
        self.base_checkbox.setLayout(base_checkbox_layout)
        fitting_checkbox_layout.addWidget(self.base_checkbox)
        self.fitting_checkbox.setLayout(fitting_checkbox_layout)
        layout.addWidget(self.fitting_checkbox)

        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._connect()

    def set_line(self, plane):
        self.fitting_checkbox.blockSignals(True)
        self.method_buttons.blockSignals(True)
        self.resolution_slider.blockSignals(True)
        self.base_checkbox.blockSignals(True)
        self.base_slider.blockSignals(True)

        if self.plane != plane:
            self.fitting_checkbox.setChecked(plane.fitting_options)
            self.method_buttons.method = plane.method
            self.resolution_slider.set_range(plane.resolution_edit_range)
            self.resolution_slider.value = plane.resolution
            self.base_checkbox.setChecked(plane.use_base)
            self.base_slider.set_range(plane.base_level_edit_range)
            self.base_slider.value = plane.base_level

        self.fitting_checkbox.blockSignals(False)
        self.method_buttons.blockSignals(False)
        self.resolution_slider.blockSignals(False)
        self.base_checkbox.blockSignals(False)
        self.base_slider.blockSignals(False)
        self.plane = plane

    def _connect(self):
        self.update_button.clicked.connect(self._update)
        self.fitting_checkbox.clicked.connect(self._fitting_toggled)
        self.method_buttons.valueChanged.connect(self._method_changed)
        self.resolution_slider.valueChanged.connect(self._resolution_changed)
        self.base_checkbox.clicked.connect(self._base_toggled)
        self.base_slider.valueChanged.connect(self._base_changed)

    def _update(self):
        if self.plane is not None:
            self.plane.recalc_and_update()

    def _fitting_toggled(self):
        if self.plane is not None:
            self.plane.fitting_options = self.fitting_checkbox.isChecked()

    def _method_changed(self):
        if self.plane is not None:
            self.plane.change_method(self.method_buttons.method)

    def _resolution_changed(self):
        if self.plane is not None:
            self.plane.change_resolution(self.resolution_slider.value)
            self.plane.resolution_edit_range = self.resolution_slider.get_range()

    def _base_toggled(self):
        if self.plane is not None:
            self.plane.use_base = self.base_checkbox.isChecked()
            self.plane.change_base(self.base_slider.value)

    def _base_changed(self):
        if self.plane is not None:
            self.plane.change_base(self.base_slider.value)
            self.plane.base_level_edit_range = self.base_slider.get_range()
