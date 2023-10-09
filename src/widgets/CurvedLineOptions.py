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
    QSizePolicy,
    QCheckBox
)

# This package
from .LabelEditSlider import LabelEditSlider
from .LabelEditRangeSlider import LabelEditRangeSlider
from .DegreeButtons import DegreeButtons
from .CenteredCheckBox import CenteredCheckBox


class CurvedLineOptions(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.line = None

        layout = QVBoxLayout()
        line_options_label = QLabel("Curved Line Options")
        line_options_label.setSizePolicy(QSizePolicy(QSizePolicy.Maximum,
                                                     QSizePolicy.Maximum))
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

        self.update_on_move_checkbox = QCheckBox("Update on move")
        self.update_on_move_checkbox.setToolTip("Updates the line to fit the particles every time a particle is moved."
                                                " Can be quite resource intensive.")
        layout.addWidget(self.update_on_move_checkbox)

        self.remove_deleted_particles_button = QPushButton("Remove Deleted Particles")
        self.remove_deleted_particles_button.setToolTip("Removes all deleted particles from defining the list. Useful"
                                                        " when some particles have been deleted and the path of the"
                                                        " line should be updated. Does nothing if less than two"
                                                        " particles remain.")
        layout.addWidget(self.remove_deleted_particles_button)

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

        # Move camera along line options
        self.camera_checkbox = QGroupBox("Move camera along line:")
        self.camera_checkbox.setCheckable(True)
        camera_checkbox_layout = QVBoxLayout()

        self.move_camera_button = QPushButton("Move Camera Along Line")
        self.move_camera_button.setToolTip("Moves the camera along the line, using the settings below to define the"
                                           " direction and facing of the camera. Useful for recording videos using the"
                                           " 'movie record' command. Use"
                                           " together with the 'update on move' setting to interactively change"
                                           " the path by moving the particles that define the line. ")
        direction_box = QGroupBox("Moving direction")
        direction_box_layout = QHBoxLayout()
        self.forwards_button = QRadioButton("Forwards")
        self.backwards_button = QRadioButton("Backwards")
        direction_box_layout.addWidget(self.forwards_button)
        direction_box_layout.addWidget(self.backwards_button)
        direction_box.setLayout(direction_box_layout)
        self.no_frames_slider = LabelEditRangeSlider([2, 100], "Numer of frames", step_size=1, min=2, max=self.resolution_slider.value)
        self.move_camera_slider = LabelEditSlider([0, self.no_frames_slider.value], "Move To Specific Frame", step_size=1)
        self.camera_distance_behind_line = LabelEditRangeSlider([0, 1000], "Camera distance behind line", step_size=1, min=0)
        self.camera_distance_behind_line.setToolTip("Use this to set the distance between the line and the camera,"
                                                    " useful for avoiding clipping. However, if the camera is to enter"
                                                    " a model, the distance needs to be short.")
        self.camera_top_rotation = LabelEditSlider((0, 360), "Camera Top Rotation [deg]:", step_size=0.01)
        self.camera_facing_rotation = LabelEditSlider((0, 360), "Camera Facing Rotation [deg]:", step_size=0.01)
        self.camera_rotation = LabelEditSlider((0, 360), "Camera Rotation [deg]:", step_size=0.01)

        self.camera_axes_checkbox = QGroupBox("Show camera orientation:")
        self.camera_axes_checkbox.setCheckable(True)
        self.camera_axes_checkbox.setChecked(False)
        self.camera_axes_checkbox.setToolTip("Shows the direction the camera will point. The axis is the facing"
                                             " direction, the yellow is the top of the camera.")
        camera_axes_checkbox_layout = QVBoxLayout()
        self.no_camera_axes = LabelEditRangeSlider([2, 100], "Number of axes", step_size=1, min=2, max=self.resolution_slider.value)
        self.camera_axes_size_slider = LabelEditRangeSlider((10, 20), "Axes Size:", min=0)
        camera_axes_checkbox_layout.addWidget(self.no_camera_axes)
        camera_axes_checkbox_layout.addWidget(self.camera_axes_size_slider)
        self.camera_axes_checkbox.setLayout(camera_axes_checkbox_layout)

        camera_checkbox_layout.addWidget(self.move_camera_button)
        camera_checkbox_layout.addWidget(self.move_camera_slider)
        camera_checkbox_layout.addWidget(direction_box)
        camera_checkbox_layout.addWidget(self.no_frames_slider)
        camera_checkbox_layout.addWidget(self.camera_distance_behind_line)
        camera_checkbox_layout.addWidget(self.camera_top_rotation)
        camera_checkbox_layout.addWidget(self.camera_facing_rotation)
        camera_checkbox_layout.addWidget(self.camera_rotation)
        camera_checkbox_layout.addWidget(self.camera_axes_checkbox)
        self.camera_checkbox.setLayout(camera_checkbox_layout)
        layout.addWidget(self.camera_checkbox)

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
        layout.addStretch()
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
        self.update_on_move_checkbox.blockSignals(True)
        self.camera_checkbox.blockSignals(True)
        self.forwards_button.blockSignals(True)
        self.backwards_button.blockSignals(True)
        self.no_frames_slider.blockSignals(True)
        self.camera_distance_behind_line.blockSignals(True)
        self.camera_top_rotation.blockSignals(True)
        self.camera_facing_rotation.blockSignals(True)
        self.camera_rotation.blockSignals(True)
        self.camera_axes_checkbox.blockSignals(True)
        self.camera_axes_size_slider.blockSignals(True)
        self.no_camera_axes.blockSignals(True)
        self.move_camera_button.blockSignals(True)
        self.move_camera_slider.blockSignals(True)

        if self.line is not None:
            self.spacing_checkbox.setChecked(line.has_particles)
            self.spacing_slider.set_range(line.spacing_edit_range)
            self.spacing_slider.value = line.spacing
        else:
            line.spacing_edit_range = self.spacing_slider.get_range()
            line.spacing = self.spacing_slider.value

        self.fitting_checkbox.setChecked(line.display_options)
        self.line_display_checkbox.setChecked(line.display_options)
        self.marker_axis_display_checkbox.setChecked(line.marker_axis_display_options)
        self.rotate_checkbox.setChecked(line.rotate)
        self.fitting_checkbox.setChecked(line.fitting_options)
        self.degree_buttons.degree = line.degree
        self.degree_buttons.max_degree = len(line.particle_pos) - 1
        self.update_on_move_checkbox.setChecked(line.update_on_move)
        self.camera_checkbox.setChecked(line.camera_options)
        self.forwards_button.setChecked(not line.backwards)
        self.backwards_button.setChecked(line.backwards)
        self.camera_axes_checkbox.setChecked(line.has_camera_markers)

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

            self.no_frames_slider.set_range(line.no_frames_edit_range)
            self.no_frames_slider.value = line.no_frames
            self.no_frames_slider.max_allowed = line.resolution
            self.move_camera_slider.set_range([0, line.no_frames], 0)
            self.move_camera_slider.setEnabled(self.camera_checkbox.isChecked())
            self.no_camera_axes.max_allowed = line.resolution
            self.camera_distance_behind_line.set_range(line.distance_behind_camera_edit_range)
            self.camera_distance_behind_line.value = line.distance_behind_camera
            self.camera_top_rotation.value = line.top_rotation
            self.camera_facing_rotation.value = line.facing_rotation
            self.camera_rotation.value = line.facing_rotation
            self.no_camera_axes.set_range(line.no_camera_axes_edit_range)
            self.no_camera_axes.value = line.no_camera_axes
            self.camera_axes_size_slider.set_range(line.camera_axes_size_edit_range)
            self.camera_axes_size_slider.value = line.camera_axes_size

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
        self.update_on_move_checkbox.blockSignals(False)
        self.camera_checkbox.blockSignals(False)
        self.forwards_button.blockSignals(False)
        self.backwards_button.blockSignals(False)
        self.no_frames_slider.blockSignals(False)
        self.camera_distance_behind_line.blockSignals(False)
        self.camera_top_rotation.blockSignals(False)
        self.camera_facing_rotation.blockSignals(False)
        self.camera_rotation.blockSignals(False)
        self.camera_axes_checkbox.blockSignals(False)
        self.camera_axes_size_slider.blockSignals(False)
        self.no_camera_axes.blockSignals(False)
        self.move_camera_button.blockSignals(False)
        self.move_camera_slider.blockSignals(False)
        self.line = line

    def _connect(self):
        self.line_display_checkbox.clicked.connect(self._display_toggled)
        self.line_radius_slider.valueChanged.connect(self._radius_changed)

        self.update_button.clicked.connect(self._update_button_clicked)
        self.update_on_move_checkbox.stateChanged.connect(self._update_on_move_clicked)
        self.remove_deleted_particles_button.clicked.connect(self._remove_deleted_particles)

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

        self.camera_checkbox.clicked.connect(self._camera_toggled)
        self.move_camera_button.clicked.connect(self._move_camera)
        self.move_camera_slider.valueChanged.connect(self._move_camera_to_specific_frame)
        self.forwards_button.clicked.connect(self._direction_pressed)
        self.backwards_button.clicked.connect(self._direction_pressed)
        self.no_frames_slider.valueChanged.connect(self._no_frames_changed)
        self.camera_distance_behind_line.valueChanged.connect(self._distance_behind_line_changed)
        self.camera_top_rotation.valueChanged.connect(self._top_rotation_changed)
        self.camera_facing_rotation.valueChanged.connect(self._facing_rotation_changed)
        self.camera_rotation.valueChanged.connect(self._rotation_changed)
        self.camera_axes_checkbox.clicked.connect(self._camera_axes_toggled)
        self.no_camera_axes.valueChanged.connect(self._no_axes_changed)
        self.camera_axes_size_slider.valueChanged.connect(self._camera_axes_size_changed)

    def _remove_deleted_particles(self):
        if self.line is not None:
            self.line.remove_deleted_particles()
            self.degree_buttons.degree = self.line.degree
            self.degree_buttons.max_degree = len(self.line.particles) - 1
            self.line.recalc_and_update()

    def _camera_toggled(self):
        if self.line is not None:
            self.line.camera_options = self.camera_checkbox.isChecked()
            self.move_camera_slider.setEnabled(self.camera_checkbox.isChecked())

    def _move_camera(self):
        from chimerax.core.commands import run
        run(self.session, "camera mono")
        if self.camera_checkbox.isChecked():
            self.line.move_camera_along_line(no_frames=self.line.no_frames, backwards=self.line.backwards,
                                             distance_behind=self.line.distance_behind_camera,
                                             x_rotation=self.line.top_rotation, z_rotation=self.line.facing_rotation, y_rotation=self.line.camera_rotation)
        from chimerax.core.commands import log_equivalent_command
        log_equivalent_command(self.session, "artiax moveCameraAlongLine #{} numframes {} backward {} distanceBehind {}"
                                             " topRotation {} facingRotation {} cameraRotation {} monoCamera {}".format(
                                              self.line.id_string, int(self.line.no_frames), self.line.backwards,
                                              self.line.distance_behind_camera, self.line.top_rotation,
                                              self.line.facing_rotation, self.line.camera_rotation, True))

    def _move_camera_to_specific_frame(self):
        if self.camera_checkbox.isChecked():
            self.line.move_camera_along_line(no_frames=self.line.no_frames, backwards=self.line.backwards,
                                             distance_behind=self.line.distance_behind_camera,
                                             x_rotation=self.line.top_rotation, z_rotation=self.line.facing_rotation,
                                             y_rotation=self.line.camera_rotation, specific_frame=self.move_camera_slider.value)

    def _direction_pressed(self):
        if self.camera_checkbox.isChecked():
            self.line.backwards = self.backwards_button.isChecked()
            self._camera_markers_updated()

    def _no_frames_changed(self):
        if self.camera_checkbox.isChecked():
            self.line.no_frames_edit_range = self.no_frames_slider.get_range()
            self.line.no_frames = self.no_frames_slider.value
            self.move_camera_slider.blockSignals(True)
            self.move_camera_slider.set_range([0, self.no_frames_slider.value], 0)
            self.move_camera_slider.blockSignals(False)

    def _distance_behind_line_changed(self):
        if self.camera_checkbox.isChecked():
            self.line.distance_behind_camera_edit_range = self.camera_distance_behind_line.get_range()
            self.line.distance_behind_camera = self.camera_distance_behind_line.value

    def _top_rotation_changed(self):
        if self.camera_checkbox.isChecked():
            self.line.top_rotation = self.camera_top_rotation.value
            self._camera_markers_updated()

    def _facing_rotation_changed(self):
        if self.camera_checkbox.isChecked():
            self.line.facing_rotation = self.camera_facing_rotation.value
            self._camera_markers_updated()

    def _rotation_changed(self):
        if self.camera_checkbox.isChecked():
            self.line.camera_rotation = self.camera_rotation.value
            self._camera_markers_updated()

    def _camera_markers_updated(self):
        if self.line.has_camera_markers:
            self.line.create_camera_markers()

    def _camera_axes_toggled(self):
        if self.line is not None:
            if self.camera_axes_checkbox.isChecked():
                if not self.line.has_camera_markers:
                    self.line.no_camera_axes = self.no_camera_axes.value
                    self.line.no_camera_axes_edit_range = self.no_camera_axes.get_range()
                    self.line.create_camera_markers()
            else:
                if self.line.has_camera_markers:
                    self.line.remove_camera_markers()

    def _no_axes_changed(self):
        if self.camera_checkbox.isChecked():
            self.line.no_camera_axes_edit_range = self.no_camera_axes.get_range()
            self.line.no_camera_axes = self.no_camera_axes.value
            self.line.create_camera_markers()

    def _camera_axes_size_changed(self):
        if self.camera_checkbox.isChecked():
            self.line.camera_axes_size_edit_range = self.camera_axes_size_slider.get_range()
            self.line.change_camera_axes_size(self.camera_axes_size_slider.value)

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

    def _update_on_move_clicked(self):
        if self.line is not None:
            self.line.update_on_move = self.update_on_move_checkbox.isChecked()

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
            resolution = self.resolution_slider.value
            self.no_frames_slider.blockSignals(True)
            self.no_camera_axes.blockSignals(True)
            self.no_frames_slider.max_allowed = resolution
            self.no_frames_slider.set_range((self.no_frames_slider.get_range()[0], resolution), self.no_frames_slider.value)
            self.no_camera_axes.max_allowed = resolution
            self.no_camera_axes.set_range((self.no_camera_axes.get_range()[0], resolution), self.no_camera_axes.value)
            self.no_frames_slider.blockSignals(False)
            self.no_camera_axes.blockSignals(False)
            self.line.change_resolution(resolution)
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
