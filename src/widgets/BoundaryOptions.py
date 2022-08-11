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

class BoundaryOptions(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.boundary = None

        layout = QVBoxLayout()
        boundary_options_label = QLabel("Boundary Options")
        layout.addWidget(boundary_options_label)

        self.update_button = QPushButton("Update Boundary")
        self.update_button.setToolTip("Updates the boundary to fit the particles. Useful when the boundary doesn't "
                                      "match the desired boundary; simply move the particles that define the boundary "
                                      "and press this button to update the boundary.")
        layout.addWidget(self.update_button)

        self.reorient_button = QPushButton("Reorient particles")
        self.reorient_button.setToolTip("Reorient the selected particles that define the boundary so that the z-axis "
                                        "points along the average normal of the corner.")
        layout.addWidget(self.reorient_button)

        #Fitting options
        self.fitting_checkbox = QGroupBox("Change boundary fitting:")
        self.fitting_checkbox.setCheckable(True)
        fitting_checkbox_layout = QVBoxLayout()
        self.alpha_slider = LabelEditSlider((0,1), "alpha: ")
        fitting_checkbox_layout.addWidget(self.alpha_slider)
        self.fitting_checkbox.setLayout(fitting_checkbox_layout)

        layout.addWidget(self.fitting_checkbox)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        self.setLayout(layout)

        self._connect()

    def set_boundary(self, boundary):
        self.fitting_checkbox.blockSignals(True)
        self.alpha_slider.blockSignals(True)

        if self.boundary != boundary:
            self.fitting_checkbox.setChecked(boundary.fitting_options)
            self.alpha_slider.value = boundary.alpha

        self.fitting_checkbox.blockSignals(False)
        self.alpha_slider.blockSignals(False)

        self.boundary = boundary

    def _connect(self):
        self.update_button.clicked.connect(self._update)
        self.fitting_checkbox.clicked.connect(self._fitting_toggled)
        self.alpha_slider.valueChanged.connect(self._alpha_changed)
        self.reorient_button.clicked.connect(self._reorient)

    def _update(self):
        if self.boundary is not None:
            self.boundary.recalc_and_update()

    def _fitting_toggled(self):
        if self.boundary is not None:
            self.boundary.fitting_options = self.fitting_checkbox.isChecked()

    def _alpha_changed(self):
        if self.boundary is not None:
            self.boundary.change_alpha(self.alpha_slider.value)

    def _reorient(self):
        if self.boundary is not None:
            from ..geometricmodel.GeoModel import get_curr_selected_particles
            s_particles = get_curr_selected_particles(self.session, return_particles=True, return_pos=False)
            self.boundary.reorient_particles_to_surface(s_particles)
