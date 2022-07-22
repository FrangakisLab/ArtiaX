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
        plane_options_label = QLabel("Surface Options")
        layout.addWidget(plane_options_label)

        self.update_button = QPushButton("Update Surface")
        self.update_button.setToolTip("Updates the surface to fit the particles. Useful when the surface doesn't match"
                                      "the desired surface; simply move the particles that define the surface and "
                                      "press this button to update the surface.")
        layout.addWidget(self.update_button)

        #Fitting options
        self.fitting_checkbox = QGroupBox("Change surface fitting:")
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

        # Populate with particles
        self.populate_checkbox = QGroupBox("Populate surface with particles in every vertex:")
        self.populate_checkbox.setCheckable(True)
        self.populate_checkbox.setChecked(False)
        populate_checkbox_layout = QVBoxLayout()
        self.update_particles_button = QPushButton("Update marker positions")
        populate_checkbox_layout.addWidget(self.update_particles_button)
        self.create_particle_button = QPushButton("Create particles")
        populate_checkbox_layout.addWidget(self.create_particle_button)
        self.rotation_slider = LabelEditSlider((0, 360), "Rotation [deg]:")
        populate_checkbox_layout.addWidget(self.rotation_slider)
        self.marker_axis_display_checkbox = QGroupBox("Marker/Axis Display")
        self.marker_axis_display_checkbox.setCheckable(True)
        marker_axis_display_checkbox_layout = QVBoxLayout()
        self.marker_radius_slider = LabelEditRangeSlider((1, 10), "Marker Radius:", min=0)
        self.axes_size_slider = LabelEditRangeSlider((10, 20), "Axes Size:", min=0)
        marker_axis_display_checkbox_layout.addWidget(self.marker_radius_slider)
        marker_axis_display_checkbox_layout.addWidget(self.axes_size_slider)
        self.marker_axis_display_checkbox.setLayout(marker_axis_display_checkbox_layout)
        populate_checkbox_layout.addWidget(self.marker_axis_display_checkbox)
        populate_checkbox_layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.populate_checkbox.setLayout(populate_checkbox_layout)
        layout.addWidget(self.populate_checkbox)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        self.setLayout(layout)

        self._connect()

    def set_plane(self, plane):
        self.fitting_checkbox.blockSignals(True)
        self.method_buttons.blockSignals(True)
        self.resolution_slider.blockSignals(True)
        self.base_checkbox.blockSignals(True)
        self.base_slider.blockSignals(True)

        self.populate_checkbox.blockSignals(True)
        self.rotation_slider.blockSignals(True)
        self.marker_axis_display_checkbox.blockSignals(True)
        self.marker_radius_slider.blockSignals(True)
        self.axes_size_slider.blockSignals(True)

        if self.plane != plane:
            self.fitting_checkbox.setChecked(plane.fitting_options)
            self.method_buttons.method = plane.method
            self.resolution_slider.set_range(plane.resolution_edit_range)
            self.resolution_slider.value = plane.resolution
            self.base_checkbox.setChecked(plane.use_base)
            self.base_slider.set_range(plane.base_level_edit_range)
            self.base_slider.value = plane.base_level

            self.populate_checkbox.setChecked(plane.has_particles)
            self.rotation_slider.value = plane.rotation
            self.marker_axis_display_checkbox.setChecked(plane.marker_axis_display_options)
            self.marker_radius_slider.set_range(plane.marker_size_edit_range)
            self.marker_radius_slider.value = plane.marker_size
            self.axes_size_slider.set_range(plane.axes_size_edit_range)
            self.axes_size_slider.value = plane.axes_size

        self.fitting_checkbox.blockSignals(False)
        self.method_buttons.blockSignals(False)
        self.resolution_slider.blockSignals(False)
        self.base_checkbox.blockSignals(False)
        self.base_slider.blockSignals(False)

        self.populate_checkbox.blockSignals(False)
        self.create_particle_button.blockSignals(False)
        self.rotation_slider.blockSignals(False)
        self.marker_axis_display_checkbox.blockSignals(False)
        self.marker_radius_slider.blockSignals(False)
        self.axes_size_slider.blockSignals(False)

        self.plane = plane

    def _connect(self):
        self.update_button.clicked.connect(self._update)
        self.fitting_checkbox.clicked.connect(self._fitting_toggled)
        self.method_buttons.valueChanged.connect(self._method_changed)
        self.resolution_slider.valueChanged.connect(self._resolution_changed)
        self.base_checkbox.clicked.connect(self._base_toggled)
        self.base_slider.valueChanged.connect(self._base_changed)
        self.populate_checkbox.clicked.connect(self._population_toggled)
        self.update_particles_button.clicked.connect(self._update_marker_position)
        self.create_particle_button.clicked.connect(self._create_particles)
        self.rotation_slider.valueChanged.connect(self._rotation_changed)
        self.marker_axis_display_checkbox.clicked.connect(self._marker_axis_display_toggled)
        self.marker_radius_slider.valueChanged.connect(self._marker_radius_changed)
        self.axes_size_slider.valueChanged.connect(self._axes_size_changed)

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

    def _population_toggled(self):
        if self.plane is not None:
            if self.plane.has_particles:
                self.plane.remove_spheres()
            else:
                self.plane.create_spheres()

    def _update_marker_position(self):
        if self.populate_checkbox.isChecked():
            self.plane.create_spheres()

    def _create_particles(self):
        if self.populate_checkbox.isChecked():
            self.plane.create_particle_list()

    def _rotation_changed(self):
        if self.plane is not None:
            self.plane.change_rotation(self.rotation_slider.value)

    def _marker_axis_display_toggled(self):
        if self.plane is not None:
            self.plane.marker_axis_display_options = self.marker_axis_display_checkbox.isChecked()

    def _marker_radius_changed(self):
        if self.populate_checkbox.isChecked():
            self.plane.marker_size_edit_range = self.marker_radius_slider.get_range()
            self.plane.change_marker_size(self.marker_radius_slider.value)

    def _axes_size_changed(self):
        if self.populate_checkbox.isChecked():
            self.plane.axes_size_edit_range = self.axes_size_slider.get_range()
            self.plane.change_axes_size(self.axes_size_slider.value)
