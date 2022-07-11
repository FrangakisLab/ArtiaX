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
from .DegreeButtons import DegreeButtons


class CurvedLineOptions(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.line = None

        layout = QVBoxLayout()
        line_options_label = QLabel("Curved Line Options")
        layout.addWidget(line_options_label)

        self.line_display_checkbox = QGroupBox("Line display:")
        self.line_display_checkbox.setCheckable(True)
        line_display_layout = QVBoxLayout()
        self.line_radius_slider = LabelEditRangeSlider([0,2], "Line radius:", min=0)
        line_display_layout.addWidget(self.line_radius_slider)
        self.line_display_checkbox.setLayout(line_display_layout)
        layout.addWidget(self.line_display_checkbox)

        self.update_button = QPushButton("Update Line")
        self.update_button.setToolTip("Updates the line to fit the particles. Useful when line doesn't follow the "
                                      "desired path; simply move the particles that define the line and press this"
                                      "button to update the line.")
        layout.addWidget(self.update_button)

        # Fitting options
        self.fitting_checkbox = QGroupBox("Change line fitting:")
        self.fitting_checkbox.setCheckable(True)
        fitting_checkbox_layout = QVBoxLayout()

        self.degree_buttons = DegreeButtons(5)
        fitting_checkbox_layout.addWidget(self.degree_buttons)

        self.resolution_slider = LabelEditRangeSlider([100, 1000], "Resolution:", step_size=10, min=1)
        fitting_checkbox_layout.addWidget(self.resolution_slider)

        self.smoothing_checkbox = QGroupBox("Smoothen line:")
        self.smoothing_checkbox.setCheckable(True)
        self.smoothing_checkbox.setChecked(False)
        smoothing_checkbox_layout = QHBoxLayout()
        self.smoothing_slider = LabelEditRangeSlider([10, 20], "Smoothing", step_size=1, min=0)
        smoothing_checkbox_layout.addWidget(self.smoothing_slider)
        self.smoothing_checkbox.setLayout(smoothing_checkbox_layout)
        fitting_checkbox_layout.addWidget(self.smoothing_checkbox)

        self.fitting_checkbox.setLayout(fitting_checkbox_layout)
        layout.addWidget(self.fitting_checkbox)

        # Populate line with particles
        self.spacing_checkbox = QGroupBox("Populate line with evenly spaced particles:")
        self.spacing_checkbox.setCheckable(True)
        self.spacing_checkbox.setChecked(False)

        spacing_checkbox_layout = QVBoxLayout()

        self.spacing_slider = LabelEditRangeSlider((1, 100), "Spacing [Å]:", min=0.1)
        spacing_checkbox_layout.addWidget(self.spacing_slider)

        self.create_particle_button = QPushButton("Create particles")
        spacing_checkbox_layout.addWidget(self.create_particle_button)

        self.rotate_checkbox = QGroupBox("Rotate particles:")
        self.rotate_checkbox.setCheckable(True)
        self.rotate_checkbox.setChecked(False)
        rotate_checkbox_layout = QVBoxLayout()
        self.rotation_slider = LabelEditRangeSlider((0, 1), "Rotation [deg/Å]:", min=0)
        self.start_rotation = LabelEditSlider((0, 360), "Start Rotation [deg]:")
        rotate_checkbox_layout.addWidget(self.rotation_slider)
        rotate_checkbox_layout.addWidget(self.start_rotation)
        self.rotate_checkbox.setLayout(rotate_checkbox_layout)
        spacing_checkbox_layout.addWidget(self.rotate_checkbox)

        self.marker_axis_display_checkbox = QGroupBox("Marker/Axis Display")
        self.marker_axis_display_checkbox.setCheckable(True)
        marker_axis_display_checkbox_layout = QVBoxLayout()
        self.marker_radius_slider = LabelEditRangeSlider((1, 10), "Marker Radius:", min=0)
        self.axes_size_slider = LabelEditRangeSlider((10, 20), "Axes Size:", min=0)
        marker_axis_display_checkbox_layout.addWidget(self.marker_radius_slider)
        marker_axis_display_checkbox_layout.addWidget(self.axes_size_slider)
        self.marker_axis_display_checkbox.setLayout(marker_axis_display_checkbox_layout)
        spacing_checkbox_layout.addWidget(self.marker_axis_display_checkbox)

        spacing_checkbox_layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.spacing_checkbox.setLayout(spacing_checkbox_layout)

        layout.addWidget(self.spacing_checkbox)

        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._connect()

    def set_line(self, line):
        self.line_display_checkbox.blockSignals(True)
        self.line_radius_slider.blockSignals(True)
        self.marker_axis_display_checkbox.blockSignals(True)
        self.marker_radius_slider.blockSignals(True)
        self.axes_size_slider.blockSignals(True)
        self.spacing_slider.blockSignals(True)
        self.fitting_checkbox.blockSignals(True)
        self.degree_buttons.blockSignals(True)
        self.resolution_slider.blockSignals(True)
        self.smoothing_checkbox.blockSignals(True)
        self.smoothing_slider.blockSignals(True)
        self.rotate_checkbox.blockSignals(True)
        self.rotation_slider.blockSignals(True)
        self.start_rotation.blockSignals(True)

        if self.line is not None:
            self.spacing_checkbox.setChecked(line.has_particles)
            self.spacing_slider.set_range(line.spacing_edit_range)
            self.spacing_slider.value = line.spacing

        else:
            line.spacing_edit_range = self.spacing_slider.get_range()
            line.spacing = self.spacing_slider.value

        self.fitting_checkbox.setChecked(line.display_options)
        self.marker_axis_display_checkbox.setChecked(line.marker_axis_display_options)
        self.rotate_checkbox.setChecked(line.rotate)
        self.fitting_checkbox.setChecked(line.fitting_options)
        self.degree_buttons.degree = line.degree
        self.degree_buttons.max_degree = len(line.particles) - 1

        if self.line != line:
            self.line_radius_slider.set_range(line.radius_edit_range)
            self.line_radius_slider.value = line.radius

            self.marker_radius_slider.set_range(line.marker_size_edit_range)
            self.marker_radius_slider.value = line.marker_size
            self.axes_size_slider.set_range(line.axes_size_edit_range)
            self.axes_size_slider.value = line.axes_size
            self.rotation_slider.set_range(line.rotation_edit_range)
            self.rotation_slider.value = line.rotation
            self.start_rotation.value = line.start_rotation

            self.resolution_slider.set_range(line.resolution_edit_range)
            self.resolution_slider.value = line.resolution

            self.smoothing_checkbox.setChecked(line.smooth != 0)
            self.smoothing_slider.set_range(line.smooth_edit_range)
            self.smoothing_slider.value = line.smooth

        self.line_display_checkbox.blockSignals(False)
        self.line_radius_slider.blockSignals(False)
        self.marker_axis_display_checkbox.blockSignals(False)
        self.marker_radius_slider.blockSignals(False)
        self.axes_size_slider.blockSignals(False)
        self.spacing_slider.blockSignals(False)
        self.fitting_checkbox.blockSignals(False)
        self.degree_buttons.blockSignals(False)
        self.resolution_slider.blockSignals(False)
        self.smoothing_slider.blockSignals(False)
        self.smoothing_checkbox.blockSignals(False)
        self.rotate_checkbox.blockSignals(False)
        self.rotation_slider.blockSignals(False)
        self.start_rotation.blockSignals(False)
        self.line = line

    def _connect(self):
        self.line_display_checkbox.clicked.connect(self._display_toggled)
        self.line_radius_slider.valueChanged.connect(self._radius_changed)

        self.update_button.clicked.connect(self._update_button_clicked)

        self.spacing_checkbox.clicked.connect(self._spacing_toggled)
        self.marker_axis_display_checkbox.clicked.connect(self._marker_axis_display_toggled)
        self.marker_radius_slider.valueChanged.connect(self._marker_radius_changed)
        self.axes_size_slider.valueChanged.connect(self._axes_size_changed)
        self.spacing_slider.valueChanged.connect(self.spacing_value_changed)
        #self.spacing_slider.editingFinished.connect(self._range_changed)
        self.create_particle_button.clicked.connect(self._create_particles)
        self.rotate_checkbox.clicked.connect(self._rotation_toggled)
        self.rotation_slider.valueChanged.connect(self._rotation_value_changed)
        self.start_rotation.valueChanged.connect(self._start_rotation_value_changed)

        self.fitting_checkbox.clicked.connect(self._fitting_toggled)
        self.degree_buttons.valueChanged.connect(self._change_degree)
        self.resolution_slider.valueChanged.connect(self._resolution_changed)
        self.smoothing_checkbox.clicked.connect(self._smoothing_toggled)
        self.smoothing_slider.valueChanged.connect(self._smoothing_changed)

    def _display_toggled(self):
        if self.line is not None:
            self.line.display_options = self.line_display_checkbox.isChecked()

    def _radius_changed(self):
        if self.line_display_checkbox.isChecked():
            self.line.radius_edit_range = self.line_radius_slider.get_range()
            self.line.change_radius(self.line_radius_slider.value)

    def _update_button_clicked(self):
        if self.line is not None:
            self.line.recalc_and_update()

    def _spacing_toggled(self):
        if self.spacing_checkbox.isChecked():
            if not self.line.has_particles:
                self.line.spacing = self.spacing_slider.value
                self.line.spacing_edit_range = self.spacing_slider.get_range()
                self.line.create_spheres()
        else:
            if self.line.has_particles:
                self.line.remove_spheres()

    def _marker_axis_display_toggled(self):
        if self.line is not None:
            self.line.marker_axis_display_options = self.marker_axis_display_checkbox.isChecked()

    def _marker_radius_changed(self):
        if self.spacing_checkbox.isChecked():
            self.line.marker_size_edit_range = self.marker_radius_slider.get_range()
            self.line.change_marker_size(self.marker_radius_slider.value)

    def _axes_size_changed(self):
        if self.spacing_checkbox.isChecked():
            self.line.axes_size_edit_range = self.axes_size_slider.get_range()
            self.line.change_axes_size(self.axes_size_slider.value)

    def spacing_value_changed(self):
        if self.line.has_particles:
            self.line.spacing = self.spacing_slider.value
            self.line.create_spheres()
            self.line.spacing_edit_range = self.spacing_slider.get_range()

    def _range_changed(self):
        if self.spacing_checkbox.isChecked():
            self.line.spacing_edit_range = self.spacing_slider.get_range()

    def _create_particles(self):
        if self.spacing_checkbox.isChecked():
            self.line.create_particle_list()

    def _rotation_toggled(self):
        if self.line is not None:
            self.line.rotate = self.rotate_checkbox.isChecked()
            self.line.create_spheres()

    def _rotation_value_changed(self):
        if self.line is not None and self.rotate_checkbox.isChecked():
            self.line.change_rotation(self.rotation_slider.value)
            self.line.rotation_edit_range = self.rotation_slider.get_range()

    def _start_rotation_value_changed(self):
        if self.line is not None and self.rotate_checkbox.isChecked():
            self.line.change_start_rotation(self.start_rotation.value)

    def _fitting_toggled(self):
        if self.line is not None:
            self.line.fitting_options = self.fitting_checkbox.isChecked()

    def _change_degree(self):
        if self.line is not None and self.fitting_checkbox.isChecked():
            self.line.change_degree(self.degree_buttons.degree)

    def _resolution_changed(self):
        if self.line is not None and self.fitting_checkbox.isChecked():
            self.line.change_resolution(self.resolution_slider.value)
            self.line.resolution_edit_range = self.resolution_slider.get_range()

    def _smoothing_toggled(self):
        if self.smoothing_checkbox.isChecked():
            self.line.change_smoothing(self.smoothing_slider.value)
        else:
            self.line.change_smoothing(0)

    def _smoothing_changed(self):
        if self.line is not None and self.fitting_checkbox.isChecked() and self.smoothing_checkbox.isChecked():
            self.line.change_smoothing(self.smoothing_slider.value)
            self.line.smooth_edit_range = self.smoothing_slider.get_range()
