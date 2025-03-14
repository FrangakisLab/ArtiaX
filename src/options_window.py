# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
from functools import partial
from pathlib import Path
from sys import platform
import os
import numpy as np
from PyQt6.QtWidgets import QButtonGroup

# ChimeraX
from chimerax.core.commands import run
from chimerax.core.errors import UserError
from chimerax.core.tools import ToolInstance
from chimerax.map import open_map, Volume
from chimerax.geometry import find_closest_points

# Qt
from Qt.QtCore import Qt, QSize
from Qt.QtGui import QFont, QIcon
from Qt.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QTabWidget,
    QScrollArea,
    QSizePolicy,
    QLayout,
    QWidget,
    QStackedLayout,
    QStackedWidget,
    QListWidget,
    QListWidgetItem,
    QCheckBox

)
from chimerax.surface.texture import color_image

# This package
from .volume.Tomogram import orthoplane_cmd
from .widgets import LabelEditSlider, SelectionTableWidget, ColorRangeWidget, ColorGeomodelWidget, PlaneOptions,\
    CurvedLineOptions, BoundaryOptions, SphereOptions, TriangulateOptions, ArbitraryModelOptions
from .ArtiaX import (
    OPTIONS_TOMO_CHANGED,
    OPTIONS_GEOMODEL_CHANGED,
    OPTIONS_PARTLIST_CHANGED
)


def slider_to_value(slider_value, slider_max, min, max):
    dist = max - min
    step = dist / slider_max
    return slider_value * step + min


def value_to_slider(value, slider_max, min, max):
    dist = max - min
    step = dist / slider_max
    return round((value - min) / step)


def is_float(s):
    """Return true if text convertible to float."""
    try:
        float(s)
        return True
    except ValueError:
        return False


class OptionsWindow(ToolInstance):
    DEBUG = False

    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = False        # We do save/restore in sessions
    help = "help:user/tools/artiax_options.html"
                            # Let ChimeraX know about our help page

# ==============================================================================
# Instance Initialization ======================================================
# ==============================================================================

    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)

        self.display_name = "ArtiaX Options"

        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self, close_destroys=False)

        # Set the font
        if platform == "darwin":
            self.font = QFont("Arial", 10)
        else:
            self.font = QFont("Arial", 7)

        # Icon path
        self.iconpath = Path(__file__).parent / 'icons'

        # Build the user interfaces
        self._build_tomo_widget()
        self._build_geomodel_widget()
        self._build_visualization_widget()
        self._build_manipulation_widget()
        self._build_reorient_widget()

        # Build the final gui
        self._build_full_ui()
        self._connect_ui()

        # Set the layout
        self.tool_window.ui_area.setLayout(self.main_layout)

        # Show the window on the right side of main window, dock everything else below for space
        self.tool_window.manage("right")

        from chimerax.log.tool import Log
        from chimerax.model_panel.tool import ModelPanel
        from chimerax.map.volume_viewer import VolumeViewer
        from chimerax.markers.markergui import MarkerModeSettings

        # Make sure volume viewer is there
        run(self.session, 'ui tool show "Volume Viewer"', log=False)
        # Make sure marker tool is there (also workaround for it overwriting marker_settings on launch)
        run(self.session, 'ui tool show "Marker Placement"', log=False)

        if len(self.session.tools.find_by_class(Log)) > 0:
            log_window = self.session.tools.find_by_class(Log)[0].tool_window
            log_window.manage(self.tool_window)

        if len(self.session.tools.find_by_class(ModelPanel)) > 0:
            model_panel = self.session.tools.find_by_class(ModelPanel)[0].tool_window
            model_panel.manage(self.tool_window)

        if len(self.session.tools.find_by_class(VolumeViewer)) > 0:
            vol_viewer = self.session.tools.find_by_class(VolumeViewer)[0].tool_window
            vol_viewer.manage(self.tool_window)

        if len(self.session.tools.find_by_class(MarkerModeSettings)) > 0:
            vol_viewer = self.session.tools.find_by_class(MarkerModeSettings)[0].tool_window
            vol_viewer.manage(self.tool_window)

        # We are on top
        run(self.session, 'ui tool show "ArtiaX Options"', log=False)

        self._connect_triggers()

    def _connect_triggers(self):
        artia = self.session.ArtiaX
        artia.triggers.add_handler(OPTIONS_TOMO_CHANGED, self._update_tomo_options)
        artia.triggers.add_handler(OPTIONS_PARTLIST_CHANGED, self._update_partlist_options)
        artia.triggers.add_handler(OPTIONS_GEOMODEL_CHANGED, self._update_geomodel_options)

    def update_root(self):
        self._connect_triggers()

# ==============================================================================
# Show selected GUI ============================================================
# ==============================================================================

    def _build_full_ui(self):
        # Define a stacked layout and only show the selected layout
        self.main_layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # Add the Tabs
        self.tabs.addTab(self.tomo_area, 'Tomogram')
        self.tabs.addTab(self.vis_area, 'Visualization')
        self.tabs.addTab(self.manip_area, 'Select/Manipulate')
        self.tabs.addTab(self.reorient_area, 'Reorient')
        self.tabs.addTab(self.geomodel_area, 'Geometric Model')
        self.tabs.widget(0).setEnabled(False)
        self.tabs.widget(1).setEnabled(False)
        self.tabs.widget(2).setEnabled(False)
        self.tabs.widget(3).setEnabled(False)
        self.tabs.widget(4).setEnabled(False)
        self.tabs.setCurrentIndex(0)
        self.main_layout.addWidget(self.tabs)

        # Volume open dialog
        caption = 'Choose a volume.'
        self.volume_open_dialog = QFileDialog(caption=caption, parent=self.session.ui.main_window)
        self.volume_open_dialog.setFileMode(QFileDialog.ExistingFiles)
        self.volume_open_dialog.setNameFilters(["Volume (*.em *.mrc *.mrcs *.rec *.map *.hdf)"])
        self.volume_open_dialog.setAcceptMode(QFileDialog.AcceptOpen)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # Callback for trigger OPTIONS_TOMO_CHANGED
    def _update_tomo_options(self, name, data):
        if data is None:
            self.tabs.widget(0).setEnabled(False)
            self.current_tomo_label.setText('')
        else:
            self._show_tab("tomogram")

    # Callback for trigger OPTIONS_PARTLIST_CHANGED
    def _update_partlist_options(self, name, data):
        if data is None:
            self.tabs.widget(1).setEnabled(False)
            self.tabs.widget(2).setEnabled(False)
            self.tabs.widget(3).setEnabled(False)
            self.part_toolbar_1.set_name(None)
            self.part_toolbar_2.set_name(None)
            self.part_toolbar_3.set_name(None)
        else:
            self._show_tab("partlist")

    # Callback for trigger OPTIONS_GEOMODEL_CHANGED
    def _update_geomodel_options(self, name, data):
        if data is None:
            self.tabs.widget(4).setEnabled(False)
            self.current_geomodel_label.setText('')
        else:
            self._show_tab("geomodel")

    def _show_tab(self, obj):
        artia = self.session.ArtiaX

        if obj == "tomogram":
            ct = artia.tomograms.get(artia.options_tomogram)
            text = '#{} -- {}'.format(ct.id_string, ct.name)
            self.current_tomo_label.setText(text)
            self.tabs.setCurrentIndex(0)
            self.tabs.widget(0).setEnabled(True)

            # Update the ui
            self._update_tomo_ui()

            # Connect triggers
            from .volume.VolumePlus import RENDERING_OPTIONS_CHANGED
            ct.triggers.add_handler(RENDERING_OPTIONS_CHANGED, self._models_changed)

        elif obj == "partlist":
            cpl = artia.partlists.get(artia.options_partlist)
            self.tabs.setCurrentIndex(1)
            self.tabs.widget(1).setEnabled(True)
            self.tabs.widget(2).setEnabled(True)
            self.tabs.widget(3).setEnabled(True)

            # Update the ui
            self._update_partlist_ui()

            from .particle.ParticleList import PARTLIST_CHANGED
            cpl.triggers.add_handler(PARTLIST_CHANGED, self._partlist_changed)

        elif obj == "geomodel":
            geomodel = artia.geomodels.get(artia.options_geomodel)
            text = '#{} -- {}'.format(geomodel.id_string, geomodel.name)
            self.current_geomodel_label.setText(text)
            self.tabs.setCurrentIndex(4)
            self.tabs.widget(4).setEnabled(True)
            self.curr_model = type(geomodel).__name__

            # Update the ui
            self._update_geomodel_ui()

            from .geometricmodel.GeoModel import GEOMODEL_CHANGED
            geomodel.triggers.add_handler(GEOMODEL_CHANGED, self._geomodel_changed)

        # Make sure we are on top
        run(self.session, 'ui tool show "ArtiaX Options"', log=False)

# ==============================================================================
# Options Menu for Tomograms ===================================================
# ==============================================================================

    def _build_tomo_widget(self):
        # This widget is the Select/Manipulate lists tab
        self.tomo_area = QScrollArea()
        self.tomo_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tomo_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tomo_area.setWidgetResizable(True)

        #self.tomo_widget = QScrollArea()
        # Define the overall layout
        tomo_layout = QVBoxLayout()
        tomo_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        #### Current Tomogram Box ####
        group_current_tomo = QGroupBox("Current Tomogram")
        group_current_tomo.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                     QSizePolicy.Maximum))
        group_current_tomo.setFont(self.font)
        current_tomo_layout = QHBoxLayout()
        self.current_tomo_label = QLabel("")
        self.current_tomo_label.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                          QSizePolicy.Maximum))
        current_tomo_layout.addWidget(self.current_tomo_label)
        group_current_tomo.setLayout(current_tomo_layout)
        #### Current Tomogram Box ####

        #### Physical coordinates Box ####
        group_pixelsize = QGroupBox("Physical Coordinates")
        group_pixelsize.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                  QSizePolicy.Maximum))
        group_pixelsize.setFont(self.font)
        group_pixelsize.setCheckable(True)
        group_pixelsize_layout = QGridLayout()

        group_pixelsize_label = QLabel("Pixel Size:")
        group_pixelsize_label.setFont(self.font)
        self.group_pixelsize_edit = QLineEdit("")
        self.group_pixelsize_button_apply = QPushButton("Apply")

        group_pixelsize_layout.addWidget(group_pixelsize_label, 0, 0, 1, 1)
        group_pixelsize_layout.addWidget(self.group_pixelsize_edit, 0, 1, 1, 1)
        group_pixelsize_layout.addWidget(self.group_pixelsize_button_apply, 0, 2, 1, 1)

        # Add grid to group
        group_pixelsize.setLayout(group_pixelsize_layout)
        #### Physical coordinates Box ####

        #### Contrast Box ####
        group_contrast = QGroupBox("Contrast Settings")
        group_contrast.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                  QSizePolicy.Maximum))
        group_contrast.setFont(self.font)
        group_contrast.setCheckable(True)

        group_contrast_layout = QVBoxLayout()

        # Define two sliders that control the contrast
        from .widgets import LabelEditSlider
        self.contrast_center_widget = LabelEditSlider((-2, 2), 'Center:')
        self.contrast_width_widget = LabelEditSlider((-2, 2), 'Width:')

        group_contrast_layout.addWidget(self.contrast_center_widget)
        group_contrast_layout.addWidget(self.contrast_width_widget)

        # Add an "Invert Contrast" button below the sliders
        self.invert_contrast_button = QPushButton("Invert Contrast")
        self.invert_contrast_button.setToolTip("Invert the contrast of the selected tomogram. A new tomogram is created for which the density values are inverted.")
        self.invert_contrast_button.clicked.connect(self.invert_contrast)

        group_contrast_layout.addWidget(self.invert_contrast_button)

        # Add grid to group
        group_contrast.setLayout(group_contrast_layout)
        #### Contrast Box ####

        # Define a group for different orthoplanes of a tomogram
        group_orthoplanes = QGroupBox("Orthoplanes")
        group_orthoplanes.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                    QSizePolicy.Maximum))
        group_orthoplanes.setFont(self.font)
        group_orthoplanes.setCheckable(True)
        # Set the layout of the group
        group_orthoplanes_layout = QGridLayout()
        # Define different buttons to press for the different orthoslices
        self.group_orthoplanes_buttonxy = QPushButton("xy")
        self.group_orthoplanes_buttonxz = QPushButton("xz")
        self.group_orthoplanes_buttonyz = QPushButton("yz")
        self.group_orthoplanes_buttonxyz = QPushButton("xyz")
        # Add to the grid layout
        group_orthoplanes_layout.addWidget(self.group_orthoplanes_buttonxy, 0, 0)
        group_orthoplanes_layout.addWidget(self.group_orthoplanes_buttonxz, 0, 1)
        group_orthoplanes_layout.addWidget(self.group_orthoplanes_buttonyz, 0, 2)
        # group_orthoplanes_layout.addWidget(self.group_orthoplanes_buttonxyz, 0, 3)
        # Add grid to group
        group_orthoplanes.setLayout(group_orthoplanes_layout)

        # Define a group for the fourier transform of a volume
        group_fourier_transform = QGroupBox("Fourier transformation")
        group_fourier_transform.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                          QSizePolicy.Maximum))
        group_fourier_transform.setFont(self.font)
        group_fourier_transform_layout = QGridLayout()
        # Define Button to press for execute the transformation
        group_fourier_transform_execute_label = QLabel("FT current volume:")
        group_fourier_transform_execute_label.setFont(self.font)
        self.group_fourier_transform_execute_button = QPushButton("FT Execute")
        # Add to the grid layout
        group_fourier_transform_layout.addWidget(group_fourier_transform_execute_label, 0, 0)
        group_fourier_transform_layout.addWidget(self.group_fourier_transform_execute_button, 0, 1)
        # Add grid to group
        group_fourier_transform.setLayout(group_fourier_transform_layout)

        #### Process Tomogram ####
        group_process = QGroupBox("Processing")
        group_process.setFont(self.font)
        group_process.setCheckable(True)
        group_process_layout = QVBoxLayout()

        process_average_group = QGroupBox("Averaging")
        process_average_group.setToolTip("Create a copy of the tomogram averaged in the set direction, using the number"
                                         " of slab nearest slabs for the averaging")
        process_average_layout = QVBoxLayout()
        from .widgets import ThreeFieldsAndButton
        self.process_average_axis_widget = ThreeFieldsAndButton(maintext='Averaging Direction:',
                                                             label_1='X:',
                                                             label_2='Y:',
                                                             label_3='Z:',
                                                             button='Copy Slice Direction',
                                                             value=(0, 0, 1))
        self.process_average_num_slabs_widget = LabelEditSlider([1, 100], "Number of slabs to average:", step_size=1)
        self.process_average_create_button = QPushButton("Create Averaged Tomogram")
        process_average_layout.addWidget(self.process_average_axis_widget)
        process_average_layout.addWidget(self.process_average_num_slabs_widget)
        process_average_layout.addWidget(self.process_average_create_button)
        process_average_group.setLayout(process_average_layout)

        group_process_layout.addWidget(process_average_group)

        process_filter_group = QGroupBox("Filtering")
        process_filter_group.setToolTip("Create a copy of the tomogram that is filtered using a LP, BP, or HP filter.")
        process_filter_layout = QVBoxLayout()

        from .widgets import RadioButtonsStringOptions
        self.filtering_unit_buttons = RadioButtonsStringOptions('Unit', ['angstrom', 'pixels'])

        self.lp_box = QGroupBox('Low pass')
        self.lp_box.setCheckable(True)
        tooltip = 'Low pass or High Pass filter the current tomogram. Use Gaussian or Cosine decay. If the unit is set to pixels and the ' \
                  'pass frequency is set to zero the center of decay will be at zero. If decay size is set to zero a box ' \
                  'filter is used. If the unit is set to "angstrom", the decay size is always set to 1/pass*0.25.'
        self.lp_box.setToolTip(tooltip)
        lp_box_layout = QVBoxLayout()
        from .widgets import FilterOptionsWidget
        self.lp_filter_options = FilterOptionsWidget()
        lp_box_layout.addWidget(self.lp_filter_options)
        self.lp_box.setLayout(lp_box_layout)

        self.hp_box = QGroupBox('High pass')
        self.hp_box.setCheckable(True)
        self.hp_box.setToolTip(tooltip)
        hp_box_layout = QVBoxLayout()
        from .widgets import FilterOptionsWidget
        self.hp_filter_options = FilterOptionsWidget()
        hp_box_layout.addWidget(self.hp_filter_options)
        self.hp_box.setLayout(hp_box_layout)

        self.filter_tomo_button = QPushButton("Create Filtered Tomogram")

        process_filter_layout.addWidget(self.filtering_unit_buttons)
        process_filter_layout.addWidget(self.lp_box)
        process_filter_layout.addWidget(self.hp_box)
        process_filter_layout.addWidget(self.filter_tomo_button)
        process_filter_group.setLayout(process_filter_layout)

        group_process_layout.addWidget(process_filter_group)
        group_process.setLayout(group_process_layout)


        #### Slice Box ####
        group_slices = QGroupBox("Navigation")
        group_slices.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                               QSizePolicy.Maximum))
        group_slices.setFont(self.font)
        group_slices.setCheckable(True)

        # Set the layout for the group
        group_slices_layout = QVBoxLayout()

        group_slices_label = QLabel("Slice:")
        group_slices_label.setFont(self.font)

        # Normal vector
        from .widgets import LabeledVectorEdit
        self.normal_vector_widget = LabeledVectorEdit(maintext='Slice Direction:',
                                                      label_1='X:',
                                                      label_2='Y:',
                                                      label_3='Z:',
                                                      button='Set',
                                                      value=(0, 0, 1))

        # Sep
        from Qt.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        # Slider
        self.slice_widget = LabelEditSlider((0, 100), 'Slice:', step_size=1)

        group_slices_second_row = QHBoxLayout()
        self.group_slices_previous_10 = QPushButton("<<")
        self.group_slices_previous_10.setToolTip("-10 [F7]")
        self.group_slices_previous_1 = QPushButton("<")
        self.group_slices_previous_10.setToolTip("-1 [F3]")
        self.group_slices_next_1 = QPushButton(">")
        self.group_slices_previous_10.setToolTip("+1 [F4]")
        self.group_slices_next_10 = QPushButton(">>")
        self.group_slices_previous_10.setToolTip("+10 [F8]")

        group_slices_second_row.addWidget(self.group_slices_previous_10)
        group_slices_second_row.addWidget(self.group_slices_previous_1)
        group_slices_second_row.addWidget(self.group_slices_next_1)
        group_slices_second_row.addWidget(self.group_slices_next_10)
        # Add to the grid layout
        group_slices_layout.addWidget(self.normal_vector_widget)
        group_slices_layout.addWidget(line)
        group_slices_layout.addWidget(self.slice_widget)
        group_slices_layout.addLayout(group_slices_second_row)

        # Add grid to group
        group_slices.setLayout(group_slices_layout)
        #### Slice Box ####


        #### Tomogram arithmetics ####
        # Create a group box to hold the arithmetics-related widgets
        self.arithmetics_group = QGroupBox("Tomogram Arithmetics")
        self.arithmetics_group.setCheckable(True)
        self.arithmetics_group.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))

        # Create a layout for the group box
        arithmetics_layout = QVBoxLayout()

        # Section: "Select Tomogram"
        self.select_tomogram_group = QGroupBox("Select Tomogram for Arithmetics")
        self.select_tomogram_group.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))

        # Create a layout for the "Select Tomogram" group
        select_tomogram_layout = QVBoxLayout()

        # Tomogram selection list
        self.tomogram_list_widget = QListWidget()
        self.populate_tomogram_list()

        # Add the list widget to the selection layout
        select_tomogram_layout.addWidget(self.tomogram_list_widget)

        # Set the layout for the "Select Tomogram" group
        self.select_tomogram_group.setLayout(select_tomogram_layout)

        # Add the "Select Tomogram" group to the arithmetics layout
        arithmetics_layout.addWidget(self.select_tomogram_group)


        # Add the checkboxes for operations (Addition, Subtraction, Multiplication)
        operations_layout = QHBoxLayout()  # Use a horizontal layout for checkboxes
        self.addition_checkbox = QCheckBox("Addition")
        self.subtraction_checkbox = QCheckBox("Subtraction")
        self.multiplication_checkbox = QCheckBox("Multiplication")
        self.division_checkbox = QCheckBox("Division")

        # Add checkboxes to the operations layout
        operations_layout.addWidget(self.addition_checkbox)
        operations_layout.addWidget(self.subtraction_checkbox)
        operations_layout.addWidget(self.multiplication_checkbox)
        operations_layout.addWidget(self.division_checkbox)

        # Connect each checkbox to both the handler and the update function
        self.addition_checkbox.stateChanged.connect(
            lambda: (self.on_checkbox_toggled(self.addition_checkbox), self.update_operation_info()))
        self.subtraction_checkbox.stateChanged.connect(
            lambda: (self.on_checkbox_toggled(self.subtraction_checkbox), self.update_operation_info()))
        self.multiplication_checkbox.stateChanged.connect(
            lambda: (self.on_checkbox_toggled(self.multiplication_checkbox), self.update_operation_info()))
        self.division_checkbox.stateChanged.connect(
            lambda: (self.on_checkbox_toggled(self.division_checkbox), self.update_operation_info()))

        # Add the operations layout to the arithmetics layout
        arithmetics_layout.addLayout(operations_layout)


        # Add a QLabel to show the current operation and selected tomograms
        self.operation_info_label = QLabel("Current operation: None")
        self.operation_info_label.setAlignment(Qt.AlignCenter)

        # Add the label to the layout
        arithmetics_layout.addWidget(self.operation_info_label)


        # Create the "Compute"  button
        self.compute_button = QPushButton("Compute")

        # Connect the button to the method
        self.compute_button.clicked.connect(self.tomo_arithmetics)

        # Add the button to the arithmetics layout
        arithmetics_layout.addWidget(self.compute_button)

        # Set the layout for the arithmetics group box
        self.arithmetics_group.setLayout(arithmetics_layout)

        #### Tomogram arithmetics ####


        # Add groups to layout
        tomo_layout.addWidget(group_current_tomo)
        tomo_layout.addWidget(group_pixelsize)
        tomo_layout.addWidget(group_contrast)
        tomo_layout.addWidget(group_slices)
        tomo_layout.addWidget(group_orthoplanes)
        tomo_layout.addWidget(group_process)
        tomo_layout.addWidget(self.arithmetics_group)
        #tomo_layout.addWidget(group_fourier_transform)

        # And finally set the layout of the widget
        self.tomo_widget = QWidget()
        self.tomo_widget.setFont(self.font)
        self.tomo_widget.setContentsMargins(0, 0, 0, 0)
        self.tomo_widget.setLayout(tomo_layout)
        self.tomo_area.setWidget(self.tomo_widget)

        # And finally set the layout of the widget
        # self.tomo_widget.setLayout(tomo_layout)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Tomo Window Functions ++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _connect_ui(self):
        ow = self
        artia = self.session.ArtiaX

        ### Options window
        ## Tomo Tab
        # Pixel size
        ow.group_pixelsize_button_apply.clicked.connect(ow._set_tomo_pixelsize)
        ow.group_pixelsize_edit.editingFinished.connect(ow._set_tomo_pixelsize)

        # Center
        ow.contrast_center_widget.valueChanged.connect(ow._contrast_center_changed)
        ow.contrast_center_widget.editingFinished.connect(partial(ow._contrast_center_changed, log=True))

        # Width
        ow.contrast_width_widget.valueChanged.connect(ow._contrast_width_changed)
        ow.contrast_width_widget.editingFinished.connect(partial(ow._contrast_width_changed, log=True))

        # Slice
        ow.normal_vector_widget.valueChanged.connect(ow._normal_changed)
        ow.slice_widget.valueChanged.connect(ow._slice_changed)
        ow.slice_widget.editingFinished.connect(partial(ow._slice_changed, log=True))

        # Define the shortcuts
        from Qt.QtGui import QKeySequence
        from Qt.QtWidgets import QShortcut
        ua = ow.tool_window.ui_area
        self.jump_1_forwards = QShortcut(QKeySequence(Qt.Key.Key_F4), ua)
        self.jump_10_forwards = QShortcut(QKeySequence(Qt.Key.Key_F8), ua)
        self.jump_1_backwards = QShortcut(QKeySequence(Qt.Key.Key_F3), ua)
        self.jump_10_backwards = QShortcut(QKeySequence(Qt.Key.Key_F7), ua)
        self.jump_1_forwards.activated.connect(partial(ow._skip_planes, 1))
        self.jump_10_forwards.activated.connect(partial(ow._skip_planes, 10))
        self.jump_1_backwards.activated.connect(partial(ow._skip_planes, -1))
        self.jump_10_backwards.activated.connect(partial(ow._skip_planes, -10))

        # Slices buttons
        ow.group_slices_previous_10.clicked.connect(partial(ow._skip_planes, -10))
        ow.group_slices_previous_1.clicked.connect(partial(ow._skip_planes, -1))
        ow.group_slices_next_1.clicked.connect(partial(ow._skip_planes, 1))
        ow.group_slices_next_10.clicked.connect(partial(ow._skip_planes, 10))

        # Processing
        ow.process_average_axis_widget.valueChanged.connect(ow._average_axis_changed)
        ow.process_average_axis_widget.buttonPressed.connect(ow._average_axis_copy_slice_direction)
        ow.process_average_num_slabs_widget.valueChanged.connect(ow._average_num_slabs_changed)
        ow.process_average_create_button.clicked.connect(ow._create_averaged_tomogram)

        ow.lp_box.toggled.connect(ow._lp_box_clicked)
        ow.hp_box.toggled.connect(ow._hp_box_clicked)
        ow.filtering_unit_buttons.valueChanged.connect(ow._filtering_unit_changed)
        ow.lp_filter_options.valueChanged.connect(ow._lp_filter_changed)
        ow.hp_filter_options.valueChanged.connect(ow._hp_filter_changed)
        ow.filter_tomo_button.clicked.connect(ow._create_filtered_tomogram)

        # Orthoplanes
        ow.group_orthoplanes_buttonxy.clicked.connect(partial(ow._set_xy_orthoplanes))
        ow.group_orthoplanes_buttonxz.clicked.connect(partial(ow._set_xz_orthoplanes))
        ow.group_orthoplanes_buttonyz.clicked.connect(partial(ow._set_yz_orthoplanes))
        #ow.group_orthoplanes_buttonxyz.clicked.connect(partial(ow.orthoplanes_buttonxyz_execute))

        # Fourier transform
        #ow.group_fourier_transform_execute_button.clicked.connect(partial(ow._fourier_transform))

        ## Partlist Tabs
        # Connect lock buttons
        ow.translation_lock_button_1.stateChanged.connect(ow._lock_translation)
        ow.translation_lock_button_2.stateChanged.connect(ow._lock_translation)
        ow.translation_lock_button_3.stateChanged.connect(ow._lock_translation)
        ow.rotation_lock_button_1.stateChanged.connect(ow._lock_rotation)
        ow.rotation_lock_button_2.stateChanged.connect(ow._lock_rotation)
        ow.rotation_lock_button_3.stateChanged.connect(ow._lock_rotation)

        # Connect partlist pixelsize
        ow.pf_edit_ori.editingFinished.connect(ow._origin_pixelsize_changed)
        ow.pf_edit_tra.editingFinished.connect(ow._trans_pixelsize_changed)

        # Connect manipulation buttons
        ow.group_manipulation_delete_button.clicked.connect(ow._delete_selected)
        ow.group_manipulation_reset_selected_button.clicked.connect(ow._reset_selected)
        ow.group_manipulation_reset_all_button.clicked.connect(ow._reset_all)
        ow.group_manipulation_button_delete_duplicates.clicked.connect(partial(ow._remove_duplicates, ow.input_distance))

        # Adding an object
        ow.browse_edit.returnPressed.connect(ow._enter_display_volume)
        ow.browse_button.clicked.connect(ow._browse_display_volume)
        ow.add_from_session.clicked.connect(ow._add_display_volume)

        # Connect selector
        ow.partlist_selection.displayChanged.connect(ow._show_particles)
        ow.partlist_selection.selectionChanged.connect(ow._select_particles)

        # Connect colors
        ow.color_selection.colorChanged.connect(ow._color_particles)
        ow.color_selection.colormapChanged.connect(ow._color_particles_byattribute)

        ow.color_selection.colorChangeFinished.connect(partial(ow._color_particles, log=True))
        ow.color_selection.colormapChangeFinished.connect(partial(ow._color_particles_byattribute, log=True))

        # Connect sliders
        ow.radius_widget.valueChanged.connect(ow._radius_changed)
        ow.radius_widget.editingFinished.connect(partial(ow._radius_changed, log=True))

        ow.axes_size_widget.valueChanged.connect(ow._axes_size_changed)
        ow.axes_size_widget.editingFinished.connect(partial(ow._axes_size_changed, log=True))

        ow.surface_level_widget.valueChanged.connect(ow._surface_level_changed)
        ow.surface_level_widget.editingFinished.connect(partial(ow._surface_level_changed, log=True))

        # Connect reorientation
        ow.reorient_from_order_button.clicked.connect(ow._reorient_from_order)
        ow.reorder_from_links_button.clicked.connect(ow._reorder_from_links)
        ow.reorder_to_closest_button.clicked.connect(ow._reorder_to_closest)

        ## Geometric Model Tab
        # Connect colors
        ow.geomodel_color_selection.colorChanged.connect(ow._color_geomodel)
        ow.geomodel_color_selection.colorChangeFinished.connect(partial(ow._color_geomodel, log=True))

        # Generate particles options
        ow.generate_in_surface_widget.buttonPressed.connect(ow._generate_in_surface)
        ow.generate_in_surface_widget.valueChanged.connect(ow._generate_in_surface_options_changed)
        ow.generate_on_surface_widget.buttonPressed.connect(ow._generate_on_surface)
        ow.generate_on_surface_widget.valueChanged.connect(ow._generate_on_surface_options_changed)

    def _update_tomo_ui(self):
        self._update_tomo_sliders()
        self._update_pixelsize_edit()
        self._update_analysis()

    def _models_changed(self, name, model):
        artia = self.session.ArtiaX
        ot = artia.tomograms.get(artia.options_tomogram)

        if model is ot:
            self._update_tomo_ui()

    def _update_tomo_sliders(self):
        # Center goes in 100 steps from the minimal value to the maximal value of the data grid
        artia = self.session.ArtiaX
        idx = artia.options_tomogram
        tomo = artia.tomograms.get(idx)

        prev = self.contrast_center_widget.blockSignals(True)
        self.contrast_center_widget.set_range(range=[tomo.min, tomo.max], value=tomo.contrast_center)
        self.contrast_center_widget.blockSignals(prev)

        prev = self.contrast_width_widget.blockSignals(True)
        self.contrast_width_widget.set_range(range=[0.000001, tomo.range], value=tomo.contrast_width)
        self.contrast_width_widget.blockSignals(prev)

        prev = self.slice_widget.blockSignals(True)
        self.slice_widget.set_range(range=[0, tomo.slab_count-1], value=tomo.integer_slab_position)
        self.slice_widget.blockSignals(prev)

        self.normal_vector_widget.set_value(tomo.normal)

        self.process_average_axis_widget.set_value(tomo.averaging_axis)
        self.process_average_num_slabs_widget.set_range([1,tomo.slab_count], value=tomo.num_averaging_slabs)

        self.filtering_unit_buttons.set_value_checked(tomo.unit)
        self.lp_box.setChecked(tomo.use_low_pass)
        self.hp_box.setChecked(tomo.use_high_pass)
        self.lp_filter_options.cutoff = tomo.lp_method
        self.lp_filter_options.pass_freq = tomo.lp
        self.lp_filter_options.decay_freq = tomo.lpd
        self.lp_filter_options.auto_decay = tomo.auto_lpd
        self.hp_filter_options.cutoff = tomo.hp_method
        self.hp_filter_options.pass_freq = tomo.hp
        self.hp_filter_options.decay_freq = tomo.hpd
        self.hp_filter_options.auto_decay = tomo.auto_hpd


    def _update_pixelsize_edit(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        self.group_pixelsize_edit.setText(str(tomo.pixelsize[0]))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _set_tomo_pixelsize(self):
        ow = self
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        if not is_float(self.group_pixelsize_edit.text()):
            self.group_pixelsize_edit.setText(str(tomo.pixelsize))
            raise UserError('Please enter a valid number for the pixelsize.')

        pixel_size = float(self.group_pixelsize_edit.text())

        if pixel_size <= 0:
            raise UserError("Pixelsize needs to be positive and non-zero.")

        tomo.pixelsize = pixel_size
        tomo.integer_slab_position = tomo.slab_count / 2 + 1

        from chimerax.core.commands import log_equivalent_command
        log_equivalent_command(self.session, "artiax tomo #{} pixelSize {}".format(tomo.id_string, pixel_size))
        run(self.session, 'artiax view xy')

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _contrast_center_changed(self, value, log=False):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        #run(self.session, 'volume #{} step 4'.format(tomo.id_string))
        tomo.contrast_center = value

        if log:
            from chimerax.core.commands import log_equivalent_command
            log_equivalent_command(self.session, 'artiax tomo #{} contrastCenter {}'.format(tomo.id_string, value))
            #run(self.session, 'volume #{} step 1'.format(tomo.id_string))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _contrast_width_changed(self, value, log=False):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.contrast_width = value

        if log:
            from chimerax.core.commands import log_equivalent_command
            log_equivalent_command(self.session, 'artiax tomo #{} contrastWidth {}'.format(tomo.id_string, value))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _slice_changed(self, value, log=False):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.integer_slab_position = value

        if log:
            from chimerax.core.commands import log_equivalent_command
            log_equivalent_command(self.session, 'artiax tomo #{} slice {}'.format(tomo.id_string, round(value)))

    def _normal_changed(self, value):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.normal = value

        from chimerax.core.commands import log_equivalent_command
        log_equivalent_command(self.session, 'artiax tomo #{} sliceDirection {},{},{}'.format(tomo.id_string,
                                                                                              value[0],
                                                                                              value[1],
                                                                                              value[2]))

    def _create_averaged_tomogram(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        from functools import reduce
        num_voxels = reduce(lambda x, y: x * y, tomo.size)
        if num_voxels > 100000000:
            self.session.logger.warning("Large Tomogram, might take time.")

        tomo.create_averaged_tomogram(num_slabs=tomo.num_averaging_slabs, axis=tomo.averaging_axis)

    def _lp_box_clicked(self, on):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.use_low_pass = on

    def _hp_box_clicked(self, on):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.use_high_pass = on

    def _filtering_unit_changed(self, value):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.unit = value.lower()

        self.lp_filter_options.blockSignals(True)
        self.hp_filter_options.blockSignals(True)
        if value == 'angstrom':
            self.lp_filter_options.enable_decay_setter(False)
            self.hp_filter_options.enable_decay_setter(False)
        else:
            self.lp_filter_options.enable_decay_setter(True)
            self.hp_filter_options.enable_decay_setter(True)
        self.lp_filter_options.blockSignals(False)
        self.hp_filter_options.blockSignals(False)

    def _lp_filter_changed(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.lp_method = self.lp_filter_options.cutoff
        tomo.lp = self.lp_filter_options.pass_freq
        tomo.lpd = self.lp_filter_options.decay_freq
        tomo.auto_lpd = self.lp_filter_options.auto_decay

    def _hp_filter_changed(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.hp_method = self.hp_filter_options.cutoff
        tomo.hp = self.hp_filter_options.pass_freq
        tomo.hpd = self.hp_filter_options.decay_freq
        tomo.auto_hpd = self.hp_filter_options.auto_decay

    def _create_filtered_tomogram(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        from functools import reduce
        num_voxels = reduce(lambda x, y: x * y, tomo.size)
        if num_voxels > 100000000:
            self.session.logger.warning("Large Tomogram, might take time.")

        if tomo.use_low_pass:
            lp = tomo.lp
            lpd = None if tomo.auto_lpd else tomo.lpd
        else:
            lp, lpd = 0, 0
        if tomo.use_high_pass:
            hp = tomo.hp
            hpd = None if tomo.auto_hpd else tomo.hpd
        else:
            hp, hpd = 0, 0

        lp_method = 'cosine' if tomo.lp_method.lower() == 'raised cosine' else tomo.lp_method.lower()
        hp_method = 'cosine' if tomo.hp_method.lower() == 'raised cosine' else tomo.hp_method.lower()


        tomo.create_filtered_tomogram(lp, hp, lpd, hpd, tomo.thresh, tomo.unit, lp_method, hp_method)

        from chimerax.core.commands import log_equivalent_command
        if lp_method == 'gaussian' or hp_method == 'gaussian':
            log_equivalent_command(self.session, "artiax filter #{} {} {} lpd {} hpd {} unit {} lp_cutoff {} hp_cutoff {} threshold {}".format(
                                              tomo.id_string, lp, hp, lpd, hpd, tomo.unit, lp_method, hp_method, tomo.thresh))
        else:
            log_equivalent_command(self.session,
                                   "artiax filter #{} {} {} lpd {} hpd {} unit {} lp_cutoff {} hp_cutoff {}".format(
                                       tomo.id_string, lp, hp, lpd, hpd, tomo.unit, lp_method, hp_method))

    def _average_axis_changed(self, axis):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.averaging_axis = axis

    def _average_axis_copy_slice_direction(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.averaging_axis = tomo.normal
        self.process_average_axis_widget.set_value(tomo.averaging_axis)

    def _average_num_slabs_changed(self, num_slabs):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        tomo.num_averaging_slabs = int(num_slabs)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _skip_planes(self, number):

        # Extra checks because it's a callback to keyboard shortcuts.
        if not hasattr(self.session, 'ArtiaX'):
            return

        if self.session.ArtiaX.options_tomogram is None:
            return

        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        tomo_slice = tomo.integer_slab_position + number
        tomo_slice = max(0, tomo_slice)
        tomo_slice = min(tomo.slab_count, tomo_slice)
        tomo.integer_slab_position = tomo_slice
        self._update_tomo_sliders()

        from chimerax.core.commands import log_equivalent_command
        log_equivalent_command(self.session, 'artiax tomo #{} slice {}'.format(tomo.id_string, round(tomo_slice)))

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _set_xy_orthoplanes(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        run(self.session, 'artiax tomo #{} sliceDirection 0,0,1'.format(tomo.id_string))
        run(self.session, 'artiax view xy')
        run(self.session, 'mousemode rightMode "move planes"')
        self._update_tomo_sliders()

    def _set_xz_orthoplanes(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        run(self.session, 'artiax tomo #{} sliceDirection 0,1,0'.format(tomo.id_string))
        run(self.session, 'artiax view xz')
        run(self.session, 'mousemode rightMode "move planes"')
        self._update_tomo_sliders()

    def _set_yz_orthoplanes(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        run(self.session, 'artiax tomo #{} sliceDirection 1,0,0'.format(tomo.id_string))
        run(self.session, 'artiax view yz')
        run(self.session, 'mousemode rightMode "move planes"')
        self._update_tomo_sliders()

    def orthoplanes_buttonxyz_execute(self):
        pass

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _fourier_transform(self):
        # Execute the fourier transform of the current volume
        artia = self.session.ArtiaX
        id = artia.tomograms.get(artia.options_tomogram).id_string
        command = "volume fourier #{} phase true".format(id)
        run(self.session, command)


    def tomo_arithmetics(self):

        # Get current tomogram
        artia = self.session.ArtiaX
        self.tomo_math = artia.tomograms.get(artia.options_tomogram)
        matrix_1 = self.tomo_math.data.matrix()

        print("Array Excerpt (first 5 elements):")
        print(matrix_1.ravel()[:5])  # Flatten the array and print the first 5 elements
        print("\nBasic Information:")
        print(f"Shape: {matrix_1.shape}")
        print(f"Data type: {matrix_1.dtype}")
        print(f"Size (number of elements): {matrix_1.size}")
        print(f"Memory (bytes): {matrix_1.nbytes}")
        print(f"Max value: {matrix_1.max()}")
        print(f"Min value: {matrix_1.min()}")


        # Get selected segmentation/tomogram
        selected_tomograms = self.get_selected_tomograms()

        # Loop through selected tomograms
        for tomo_id_string in selected_tomograms:
            self.selected_tomo_math = None
            for tomo in self.session.ArtiaX.tomograms.iter():
                if f"#{tomo.id_string} - {tomo.name}" == tomo_id_string:
                    self.selected_tomo_math = tomo
                    break

        # Ensure a segmentation is selected
        if not self.selected_tomo_math:
            print("No valid segmentation selected.")
            return

        matrix_2 = self.selected_tomo_math.data.matrix()

        print("Array Excerpt (first 5 elements):")
        print(matrix_2.ravel()[:5])  # Flatten the array and print the first 5 elements
        print("\nBasic Information:")
        print(f"Shape: {matrix_2.shape}")
        print(f"Data type: {matrix_2.dtype}")
        print(f"Size (number of elements): {matrix_2.size}")
        print(f"Memory (bytes): {matrix_2.nbytes}")
        print(f"Max value: {matrix_2.max()}")
        print(f"Min value: {matrix_2.min()}")

        arrays_match=False
        if matrix_1.shape == matrix_2.shape:
            print("The dimensions match!")
            arrays_match=True
        else:
            raise UserError (f"Dimension mismatch: array1 shape {matrix_1.shape} != array2 shape {matrix_2.shape}")

        addition=False
        subtraction=False
        multiplication=False
        division=False
        #check which mode
        if self.addition_checkbox.isChecked():
            addition=True
            print("Addition mode selected")
        if self.subtraction_checkbox.isChecked():
            print("Subtraction mode selected")
            subtraction=True
        if self.multiplication_checkbox.isChecked():
            print("Multiplication mode selected")
            multiplication=True
        if self.division_checkbox.isChecked():
            print("Division mode selected")
            division=True

        if sum([addition, subtraction, multiplication, division]) > 1:
            raise UserError("More than one operation selected. Please select only one.")

        if sum([addition, subtraction, multiplication, division]) == 0:
            raise UserError("Please select one arithmetic operation.")

        if arrays_match:

            if addition:
                array=matrix_1 + matrix_2
                key="addition"

            if subtraction:
                array=matrix_1 - matrix_2
                key="subtraction"
                min=array.min()
                max=array.max()
                if min==max:
                    raise UserError (f"Subtraction led to empty array. Cannot produce new tomogram")

            if multiplication:
                array=matrix_1 * matrix_2
                key="multiplication"

            if division:

                # Check if matrix_2 contains any zero elements
                if np.any(matrix_2 == 0):
                    raise UserError("Matrix 2 contains zero(s), division by zero in the denominator is not allowed")

                # Perform the division
                array = matrix_1 / matrix_2
                key = "division"

            name1=self.tomo_math.name
            name2=self.selected_tomo_math.name
            # Remove file extensions from the tomogram names
            name1_base = os.path.splitext(name1)[0]
            name2_base = os.path.splitext(name2)[0]

            # Build the new tomogram name dynamically without file extensions
            name = f"{name1_base}_{name2_base}_{key}"

            self.tomo_math.create_tomo_from_array(array,name)

    def populate_tomogram_list(self):
        # Clear the current items
        self.tomogram_list_widget.clear()

        # Retrieve the currently selected tomogram
        artia = self.session.ArtiaX
        current_tomogram = artia.tomograms.get(artia.options_tomogram)

        # Iterate through the available tomograms
        for vol in self.session.ArtiaX.tomograms.iter():
            # Skip the current tomogram to avoid adding it to the list
            if vol == current_tomogram:
                continue

            # Retrieve id_string and name attributes
            vol_id = getattr(vol, 'id_string', 'Unknown ID')  # Default to 'Unknown ID' if missing
            vol_name = getattr(vol, 'name', 'Unnamed Tomogram')  # Default to 'Unnamed Tomogram' if missing

            # Combine id and name for the display text
            item_text = f"#{vol_id} - {vol_name}"

            # Create the list widget item with the display text
            item = QListWidgetItem(item_text)
            item.setCheckState(Qt.Unchecked)  # Unchecked by default
            item.setData(Qt.UserRole, vol)  # Store the volume object in the item for later access

            # Add the item to the list widget
            self.tomogram_list_widget.addItem(item)

            # Connect the itemChanged signal of the QListWidget to update_operation_info
        self.tomogram_list_widget.itemChanged.connect(self.update_operation_info)

    def get_selected_tomograms(self):
        #collect checked tomograms
        selected_tomograms = []
        for index in range(self.tomogram_list_widget.count()):
            item = self.tomogram_list_widget.item(index)
            if item.checkState() == Qt.Checked:
                selected_tomograms.append(item.data(0))  # Access stored volume object
        return selected_tomograms

    def _update_analysis(self):
        self.populate_tomogram_list()
        for chbx in [self.addition_checkbox, self.subtraction_checkbox, self.multiplication_checkbox,self.division_checkbox]:
                chbx.setChecked(False)
        self.update_operation_info()


    def update_operation_info(self):
        # Get the names of the current tomogram
        artia = self.session.ArtiaX
        tomo1 = artia.tomograms.get(artia.options_tomogram)
        if tomo1:
            name1=tomo1.name
            id_1=tomo1.id_string
        else:
            name1=""
            id_1=""
        # Get the second selected tomogram name
        selected_tomograms = self.get_selected_tomograms()

        if selected_tomograms:
            # Loop through selected tomograms
            for tomo_id_string in selected_tomograms:
                self.selected_tomo_math = None
                for tomo in self.session.ArtiaX.tomograms.iter():
                    if f"#{tomo.id_string} - {tomo.name}" == tomo_id_string:
                        name2=tomo.name
                        id_2=f"#{tomo.id_string}"
                        break
        else:
            name2=""
            id_2=""

        # Check the operation being performed
        operation_str = "Operation not defined"
        if self.addition_checkbox.isChecked():
            operation_str = "+"
        elif self.subtraction_checkbox.isChecked():
            operation_str = "-"
        elif self.multiplication_checkbox.isChecked():
            operation_str = "*"
        elif self.division_checkbox.isChecked():
            operation_str = "/"

        if operation_str == "None":
            self.operation_info_label.setText(f"No operation selected")
        # Update the QLabel text to show the current operation
        if hasattr(self, 'operation_info_label') and self.operation_info_label:
            self.operation_info_label.setText(
                f"#{id_1} {name1}    {operation_str}    {id_2} {name2}")

    def invert_contrast(self):

        # Get current tomogram
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)
        matrix_1 = tomo.data.matrix()
        # volume = tomo
        # surface = volume.surfaces[0]
        # matrix_1=surface.data.matrix()
        print("Array Excerpt (first 5 elements):")
        print(matrix_1.ravel()[:5])  # Flatten the array and print the first 5 elements

        print("\nBasic Information:")
        print(f"Shape: {matrix_1.shape}")
        print(f"Data type: {matrix_1.dtype}")
        print(f"Size (number of elements): {matrix_1.size}")
        print(f"Memory (bytes): {matrix_1.nbytes}")
        print(f"Max value: {matrix_1.max()}")
        print(f"Min value: {matrix_1.min()}")

        # Find the max and min values of the array
        max_value = matrix_1.max()
        min_value = matrix_1.min()

        # Check if the values are binary (0 and 1)
        if max_value == 1 and min_value == 0:
            print("Binary values detected, performing binary inversion.")
            # Invert the contrast by flipping 0s and 1s
            array_invert = 1 - matrix_1
        else:
            print(f"Max value: {max_value}")
            print(f"Min value: {min_value}")
            # Calculate the midpoint
            midpoint = (max_value + min_value) / 2
            print(f"Midpoint: {midpoint}")

            # Option 1: Invert around the max value
            #array_invert = max_value - matrix_1

            # Invert around the midpoint
            array_invert = 2 * midpoint - matrix_1

        # Print the first 5 elements of the inverted array for verification
        print("Inverted array (first 5 elements):")
        print(array_invert.ravel()[:5])

        name1 = tomo.name
        # Remove file extensions from the tomogram names
        name1_base = os.path.splitext(name1)[0]

        key="invert"

        # Build the new tomogram name dynamically without file extensions
        name = f"{name1_base}_{key}"

        tomo.create_tomo_from_array(array_invert, name)

    # Common handler to ensure only one arithmetic operation checkbox is selected at a time
    def on_checkbox_toggled(self, checkbox):
        # If the checkbox is checked, uncheck the others
        if checkbox.isChecked():
            # Uncheck all other checkboxes
            for chbx in [self.addition_checkbox, self.subtraction_checkbox, self.multiplication_checkbox,
                         self.division_checkbox]:
                if chbx != checkbox:
                    chbx.setChecked(False)


    # ==============================================================================
# Options Menus for Motivelists =================================================
# ==============================================================================

    def _build_manipulation_widget(self):
        # This widget is the Select/Manipulate lists tab
        self.manip_area = QScrollArea()
        self.manip_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.manip_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.manip_area.setWidgetResizable(True)

        # Define the overall layout for group boxes
        self.manip_layout = QVBoxLayout()
        self.manip_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        #### Top bar with label and tool buttons ####
        from .widgets import StateButton
        self.translation_lock_button_2 = StateButton(icon_true='lock_translation.png',
                                                     icon_false='unlock_translation.png',
                                                     tooltip_true='Translation locked.',
                                                     tooltip_false='Translation unlocked.',
                                                     init_state=False)

        self.rotation_lock_button_2 = StateButton(icon_true='lock_rotation.png',
                                                  icon_false='unlock_rotation.png',
                                                  tooltip_true='Rotation locked.',
                                                  tooltip_false='Rotation unlocked.',
                                                  init_state=False)

        buttons = [self.translation_lock_button_2, self.rotation_lock_button_2]

        from .widgets import PartlistToolbarWidget
        self.part_toolbar_2 = PartlistToolbarWidget(self.font, buttons)
        #### Top bar with label and tool buttons ####

        #### Scaling group box ####
        self.group_scale = QGroupBox("Scaling:")
        self.group_scale.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                   QSizePolicy.Maximum))

        self.group_scale.setFont(self.font)
        self.group_scale.setCheckable(True)
        self.group_scale.setChecked(True)

        # Pixelsize
        self.pixel_factor_layout = QHBoxLayout()
        self.pf_label_both = QLabel("Pixelsize Factors:")
        self.pf_label_ori = QLabel("Origin")
        self.pf_edit_ori = QLineEdit()
        self.pf_label_tra = QLabel("Shift")
        self.pf_edit_tra = QLineEdit()
        self.pixel_factor_layout.addWidget(self.pf_label_both)
        self.pixel_factor_layout.addWidget(self.pf_label_ori)
        self.pixel_factor_layout.addWidget(self.pf_edit_ori)
        self.pixel_factor_layout.addWidget(self.pf_label_tra)
        self.pixel_factor_layout.addWidget(self.pf_edit_tra)

        self.group_scale.setLayout(self.pixel_factor_layout)
        #### Scaling group box ####

        #### Manipulation group box ####
        self.group_manipulation = QGroupBox("Manipulation:")
        self.group_manipulation.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                          QSizePolicy.Maximum))
        self.group_manipulation.setFont(self.font)
        self.group_manipulation.setCheckable(True)
        self.group_manipulation.setChecked(False)

        # Main layout for the group box
        manipulation_layout = QVBoxLayout()

        # First row of buttons
        self.manipulation_buttons_1 = QHBoxLayout()
        self.group_manipulation_delete_button = QPushButton("Delete selected")
        self.group_manipulation_delete_button.setFont(self.font)
        self.group_manipulation_reset_selected_button = QPushButton("Reset selected")
        self.group_manipulation_reset_selected_button.setFont(self.font)
        self.group_manipulation_reset_all_button = QPushButton("Reset all")
        self.group_manipulation_reset_all_button.setFont(self.font)
        self.manipulation_buttons_1.addWidget(self.group_manipulation_delete_button)
        self.manipulation_buttons_1.addWidget(self.group_manipulation_reset_selected_button)
        self.manipulation_buttons_1.addWidget(self.group_manipulation_reset_all_button)

        # Add first row of buttons to the main layout
        manipulation_layout.addLayout(self.manipulation_buttons_1)

        # Subgroup: Remove duplicates
        self.subgroup_remove_duplicates = QGroupBox("Remove duplicates")
        self.subgroup_remove_duplicates.setFont(self.font)

        # Layout for the subgroup
        remove_duplicates_layout = QHBoxLayout()
        self.label_distance = QLabel("Distance [angstrom]:")
        self.label_distance.setFont(self.font)
        self.input_distance = QLineEdit()
        self.input_distance.setFont(self.font)
        self.group_manipulation_button_delete_duplicates = QPushButton("Delete")
        self.group_manipulation_button_delete_duplicates.setToolTip("Deletes particle duplicates or particles that are within a specified radius (in angstrom) to each other.")
        self.group_manipulation_button_delete_duplicates.setFont(self.font)

        # Add widgets to the subgroup layout
        remove_duplicates_layout.addWidget(self.label_distance)
        remove_duplicates_layout.addWidget(self.input_distance)
        remove_duplicates_layout.addWidget(self.group_manipulation_button_delete_duplicates)

        # Set layout for the subgroup
        self.subgroup_remove_duplicates.setLayout(remove_duplicates_layout)

        # Add subgroup to the main layout
        manipulation_layout.addWidget(self.subgroup_remove_duplicates)

        # Set the main layout for the group box
        self.group_manipulation.setLayout(manipulation_layout)
        #### Manipulation group box ####

        #### Selection group box ####
        self.group_select = QGroupBox("Selection/Display:")
        self.group_select.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                    QSizePolicy.MinimumExpanding))
        self.group_select.setFont(self.font)
        self.group_select.setCheckable(True)

        # Set the layout of the group
        self.group_select_layout = QGridLayout()
        self.group_select_layout.setSizeConstraint(QLayout.SetMinimumSize)

        # SelectionTable
        self.partlist_selection = SelectionTableWidget()

        self.group_select_layout.addWidget(self.partlist_selection, 0, 0, 9, 6)
        self.group_select.setLayout(self.group_select_layout)
        #### Selection group box ####

        # Add groups to layout
        self.manip_layout.addWidget(self.part_toolbar_2)
        self.manip_layout.addWidget(self.group_scale)
        self.manip_layout.addWidget(self.group_manipulation)
        self.manip_layout.addWidget(self.group_select)

        # And finally set the layout of the widget
        self.manip_widget = QWidget()
        self.manip_widget.setFont(self.font)
        self.manip_widget.setContentsMargins(0, 0, 0, 0)
        self.manip_widget.setLayout(self.manip_layout)
        self.manip_area.setWidget(self.manip_widget)

    # def _build_particlelist_widget(self):
    def _build_visualization_widget(self):
        # This widget is the Visualize particle lists tab
        self.vis_area = QScrollArea()
        self.vis_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.vis_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.vis_area.setWidgetResizable(True)

        # Define the overall layout
        self.vis_layout = QVBoxLayout()
        self.vis_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        #### Top bar with label and tool buttons ####
        from .widgets import StateButton
        self.translation_lock_button_1 = StateButton(icon_true='lock_translation.png',
                                                     icon_false='unlock_translation.png',
                                                     tooltip_true='Translation locked.',
                                                     tooltip_false='Translation unlocked.',
                                                     init_state=False)

        self.rotation_lock_button_1 = StateButton(icon_true='lock_rotation.png',
                                                  icon_false='unlock_rotation.png',
                                                  tooltip_true='Rotation locked.',
                                                  tooltip_false='Rotation unlocked.',
                                                  init_state=False)

        buttons = [self.translation_lock_button_1, self.rotation_lock_button_1]

        from .widgets import PartlistToolbarWidget
        self.part_toolbar_1 = PartlistToolbarWidget(self.font, buttons)
        #### Top bar with label and tool buttons ####

        #### Color Group box ####
        self.color_selection = ColorRangeWidget(self.session)
        self.color_selection.setFont(self.font)
        #### Color Group box ####

        #### Marker/Axes Group box ####
        self.group_marker_axes = QGroupBox("Marker/Axes Display:")
        self.group_marker_axes.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                         QSizePolicy.Maximum))
        self.group_marker_axes.setFont(self.font)
        self.group_marker_axes.setCheckable(True)

        self.group_marker_axes_layout = QVBoxLayout()
        self.radius_widget = LabelEditSlider((0.1, 200), 'Marker Radius')
        self.axes_size_widget = LabelEditSlider((0.1, 200), 'Axes Size')

        self.group_marker_axes_layout.addWidget(self.radius_widget)
        self.group_marker_axes_layout.addWidget(self.axes_size_widget)

        self.group_marker_axes.setLayout(self.group_marker_axes_layout)
        #### Marker/Axes Group box ####

        #### Surface Group box ####
        self.group_surf = QGroupBox("Surface Display:")
        self.group_surf.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                  QSizePolicy.Maximum))
        self.group_surf.setFont(self.font)
        self.group_surf.setCheckable(True)

        self.group_surf_layout = QVBoxLayout()
        self.group_surf_layout.setSizeConstraint(QLayout.SetMinimumSize)

        # Current surface
        self.current_surface_label = QLabel("Current Surface: ")

        # New surface
        from Qt.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        new_surface_label = QLabel('Add new surface')

        # Add from session row
        from .widgets import ModelChooserWidget
        from chimerax.map import Volume
        self.add_from_session = ModelChooserWidget(self.session,
                                                   labeltext='Use Model: ',
                                                   buttontext='Attach Model',
                                                   type=Volume,
                                                   exclude=self.session.ArtiaX)

        # Add a browse row
        self.browse_layout = QHBoxLayout()
        self.browse_label = QLabel("Load file:")
        self.browse_label.setFont(self.font)
        self.browse_edit = QLineEdit("")
        self.browse_edit.setPlaceholderText('volume filename')
        self.browse_edit.setFont(self.font)
        self.browse_button = QPushButton("Browse")
        self.browse_layout.addWidget(self.browse_label)
        self.browse_layout.addWidget(self.browse_edit)
        self.browse_layout.addWidget(self.browse_button)

        self.surface_level_widget = LabelEditSlider((0, 1), 'Surface Level')

        self.group_surf_layout.addWidget(self.current_surface_label)
        self.group_surf_layout.addWidget(self.surface_level_widget)
        self.group_surf_layout.addWidget(line)
        self.group_surf_layout.addWidget(new_surface_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.group_surf_layout.addWidget(self.add_from_session)
        self.group_surf_layout.addLayout(self.browse_layout)


        self.group_surf.setLayout(self.group_surf_layout)
        #### Surface Group box ####

        # Add groups to layout
        self.vis_layout.addWidget(self.part_toolbar_1)
        self.vis_layout.addWidget(self.color_selection)
        self.vis_layout.addWidget(self.group_marker_axes)
        self.vis_layout.addWidget(self.group_surf)

        # And finally set the layout of the widget
        self.vis_widget = QWidget()
        self.vis_widget.setContentsMargins(0, 0, 0, 0)
        self.vis_widget.setLayout(self.vis_layout)
        self.vis_area.setWidget(self.vis_widget)

    def _build_reorient_widget(self):
        # This widget is the Visualize particle lists tab
        self.reorient_area = QScrollArea()
        self.reorient_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.reorient_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.reorient_area.setWidgetResizable(True)

        # Define the overall layout
        reorient_layout = QVBoxLayout()
        reorient_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        #### Top bar with label and tool buttons ####
        from .widgets import StateButton
        self.translation_lock_button_3 = StateButton(icon_true='lock_translation.png',
                                                     icon_false='unlock_translation.png',
                                                     tooltip_true='Translation locked.',
                                                     tooltip_false='Translation unlocked.',
                                                     init_state=False)

        self.rotation_lock_button_3 = StateButton(icon_true='lock_rotation.png',
                                                  icon_false='unlock_rotation.png',
                                                  tooltip_true='Rotation locked.',
                                                  tooltip_false='Rotation unlocked.',
                                                  init_state=False)

        buttons = [self.translation_lock_button_3, self.rotation_lock_button_3]

        from .widgets import PartlistToolbarWidget
        self.part_toolbar_3 = PartlistToolbarWidget(self.font, buttons)
        reorient_layout.addWidget(self.part_toolbar_3)
        #### Top bar with label and tool buttons ####

        #### Reorient buttons ####
        reorient_label = QLabel("Reorient particles:")
        self.reorient_from_order_button = QPushButton("From Particle List Order")
        self.reorient_from_order_button.setToolTip("Use the reorder buttons to order the particle list if necessary. "
                                                   "Then use this button to reorient the particles to point to the next"
                                                   " one in the particle list.")
        reorient_layout.addWidget(reorient_label)
        reorient_layout.addWidget(self.reorient_from_order_button)
        #### Reorient buttons ####

        #### Reorder buttons ####
        reorder_label = QLabel("Create new, reordered particle list:")
        self.reorder_from_links_button = QPushButton("From Selected Links")
        self.reorder_to_closest_button = QPushButton("To Closest")
        self.reorder_to_closest_button.setToolTip("Creates a new list with particles identical to this one, except they"
                                                  " are reordered according to proximity. Select one particle as the"
                                                  " starting point, which will be the first particle in the new list,"
                                                  " with the closest particle to the selected one being the second"
                                                  " particle in the list, etc.")
        reorient_layout.addWidget(reorder_label)
        reorient_layout.addWidget(self.reorder_from_links_button)
        reorient_layout.addWidget(self.reorder_to_closest_button)
        #### Reorient buttons ####

        # And finally set the layout of the widget
        self.reorient_widget = QWidget()
        self.reorient_widget.setContentsMargins(0, 0, 0, 0)
        self.reorient_widget.setLayout(reorient_layout)
        self.reorient_area.setWidget(self.reorient_widget)

    def _update_partlist_ui(self):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)

        # Toolbar
        self.part_toolbar_1.set_name(pl)
        self.part_toolbar_2.set_name(pl)
        self.part_toolbar_3.set_name(pl)
        self.translation_lock_button_1.setState(pl.translation_locked)
        self.translation_lock_button_2.setState(pl.translation_locked)
        self.translation_lock_button_3.setState(pl.translation_locked)
        self.rotation_lock_button_1.setState(pl.rotation_locked)
        self.rotation_lock_button_2.setState(pl.rotation_locked)
        self.rotation_lock_button_3.setState(pl.rotation_locked)

        # Set new list
        self.partlist_selection.clear(trigger_update=False)
        self.partlist_selection.set_partlist(pl)
        self.color_selection.set_partlist(pl)

        # Set sliders
        self.radius_widget.value = pl.radius
        prev = self.axes_size_widget.blockSignals(True)
        self.axes_size_widget.value = pl.axes_size
        self.axes_size_widget.blockSignals(prev)

        if pl.has_display_model() and pl.display_is_volume():
            self.surface_level_widget.setEnabled(True)
            self.surface_level_widget.set_range(range=pl.surface_range, value=pl.surface_level)
        else:
            self.surface_level_widget.setEnabled(False)

        # Pixelsize
        self.pf_edit_ori.setText(str(pl.origin_pixelsize))
        self.pf_edit_tra.setText(str(pl.translation_pixelsize))

        # Path of display model
        if pl.has_display_model():
            dpm = pl.display_model.get(0)
            if dpm.data.path is None:
                self.browse_edit.setText('')
            else:
                self.current_surface_label.setText('Current Surface: #{} - {}'.format(dpm.id_string, dpm.name))
                self.browse_edit.setText(dpm.data.path)
        else:
            self.browse_edit.setText('')

    def _partlist_changed(self, name, model):
        artia = self.session.ArtiaX
        opl = artia.partlists.get(artia.options_partlist)

        if model is opl:
            self._update_partlist_ui()



# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Motl Group Functions +++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _radius_changed(self, value, log=False):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        pl.radius = value

        if log:
            from chimerax.core.commands import log_equivalent_command
            log_equivalent_command(self.session, "artiax particles #{} radius {}".format(pl.id_string, value))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _surface_level_changed(self, value, log=False):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        pl.surface_level = value

        if log:
            from chimerax.core.commands import log_equivalent_command
            log_equivalent_command(self.session, "artiax particles #{} surfaceLevel {}".format(pl.id_string, value))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _axes_size_changed(self, value, log=False):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        pl.axes_size = value

        if log:
            from chimerax.core.commands import log_equivalent_command
            log_equivalent_command(self.session, "artiax particles #{} axesSize {}".format(pl.id_string, value))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _origin_pixelsize_changed(self):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)

        if not is_float(self.pf_edit_ori.text()):
            self.pf_edit_ori.setText(str(pl.origin_pixelsize))
            raise UserError('Please enter a valid number for the pixelsize.')

        value = float(self.pf_edit_ori.text())
        pl.origin_pixelsize = value

        from chimerax.core.commands import log_equivalent_command
        log_equivalent_command(self.session, "artiax particles #{} originScaleFactor {}".format(pl.id_string, value))
        run(self.session, "artiax view xy")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _trans_pixelsize_changed(self):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)

        if not is_float(self.pf_edit_tra.text()):
            self.pf_edit_tra.setText(str(pl.translation_pixelsize))
            raise UserError('Please enter a valid number for the pixelsize.')

        value = float(self.pf_edit_tra.text())
        pl.translation_pixelsize = value

        from chimerax.core.commands import log_equivalent_command
        log_equivalent_command(self.session, "artiax particles #{} transScaleFactor {}".format(pl.id_string, value))
        run(self.session, "artiax view xy")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _delete_selected(self):
        from numpy import any

        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        mask = pl.selected_particles

        if any(mask):
            ids = pl.particle_ids[mask]
            pl.delete_data(ids)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _reset_selected(self):
        from numpy import any
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        mask = pl.selected_particles

        if any(mask):
            ids = pl.particle_ids[mask]
            pl.reset_particles(ids)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _reset_all(self):
        print("reset all is executed")
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        pl.reset_all_particles()
        self._update_partlist_ui()

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _remove_duplicates(self, radius):
        #print("remove duplicates is executed")

        # Ensure the radius is a valid float
        try:
            rad = float(radius.text())
        except ValueError:
            print("Invalid radius value provided")
            return  # Exit the function if the input is invalid

        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        model=pl.id_string
        #print(f"model{model}")
        models=[model]
        from .particle.ParticleList import delete_duplicates

        delete_duplicates(self.session, models, rad)

        self._update_partlist_ui()

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _attach_display_model(self, file):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)

        from chimerax.core.commands import log_equivalent_command

        #TODO: ChimeraX bug? Doesn't log this.
        log_equivalent_command(self.session, 'open {}'.format(file))

        vol = open_map(self.session, file)[0][0]
        self.session.models.add([vol])
        temp_id = vol.id_string

        log_equivalent_command(self.session, 'artiax attach #{} toParticleList #{}'.format(temp_id, pl.id_string))
        pl.attach_display_model(vol)

        # Make sure the surfaces are visible
        run(self.session, 'artiax show #{} surfaces'.format(pl.id_string))

        # Make sure we are on top
        self._update_partlist_ui()
        run(self.session, 'ui tool show "ArtiaX Options"', log=False)

    def _enter_display_volume(self):
        file = self.browse_edit.text()

        if len(file) == 0:
            return

        try:
            file = self.browse_edit.text()
            self._attach_display_model(file)
        except Exception:
            self.browse_edit.setText('')

    def _browse_display_volume(self):

        file = self._choose_volume()

        if file is not None and len(file):
            self.browse_edit.setText(file[0])
            self._attach_display_model(file[0])

    def _choose_volume(self):
        if self.volume_open_dialog.exec():
            return self.volume_open_dialog.selectedFiles()

    def _add_display_volume(self, model):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)

        run(self.session, 'artiax attach #{} toParticleList #{}'.format(model.id_string, pl.id_string))

    def _lock_translation(self, state):
        artia = self.session.ArtiaX
        opl = artia.options_partlist
        pl = artia.partlists.get(opl)

        if state:
            run(self.session, 'artiax lock #{} translation'.format(pl.id_string))
        else:
            run(self.session, 'artiax unlock #{} translation'.format(pl.id_string))

    def _lock_rotation(self, state):
        artia = self.session.ArtiaX
        opl = artia.options_partlist
        pl = artia.partlists.get(opl)

        if state:
            run(self.session, 'artiax lock #{} rotation'.format(pl.id_string))
        else:
            run(self.session, 'artiax unlock #{} rotation'.format(pl.id_string))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Wrappers for ArtiaX  +++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# # Connect selector
# ow.partlist_selection.displayChanged.connect(artia.show_particles)
# ow.partlist_selection.selectionChanged.connect(artia.select_particles)
#
# # Connect colors
# ow.color_selection.colorChanged.connect(artia.color_particles)
# ow.color_selection.colormapChanged.connect(artia.color_particles_byattribute)
#
# ow.color_selection.colorChangeFinished.connect(partial(artia.color_particles, log=True))
# ow.color_selection.colormapChangeFinished.connect(partial(artia.color_particles_byattribute, log=True))

    def _show_particles(self, *args, **kwargs):
        self.session.ArtiaX.show_particles(*args, **kwargs)

    def _select_particles(self, *args, **kwargs):
        self.session.ArtiaX.select_particles(*args, **kwargs)

    def _color_particles(self, *args, **kwargs):
        self.session.ArtiaX.color_particles(*args, **kwargs)

    def _color_particles_byattribute(self, *args, **kwargs):
        self.session.ArtiaX.color_particles_byattribute(*args, **kwargs)

    def _color_geomodel(self, *args, **kwargs):
        self.session.ArtiaX.color_geomodel(*args, **kwargs)

    def _generate_in_surface(self):
        artia = self.session.ArtiaX
        gm = artia.geomodels.get(artia.options_geomodel)

        from .util.generate_points import generate_points_in_surface
        generate_points_in_surface(self.session, gm, gm.generate_in_surface_radius, gm.generate_in_surface_num_pts, gm.generate_in_surface_method)

        from chimerax.core.commands import log_equivalent_command
        if gm.generate_in_surface_method.lower() == 'poisson':
            log_equivalent_command(self.session, "artiax gen in surface #{} poisson radius {}".format(gm.id_string, gm.generate_in_surface_radius))
        elif gm.generate_in_surface_method.lower() == 'uniform':
            log_equivalent_command(self.session, "artiax gen in surface #{} uniform numPts {} exactNum False".format(gm.id_string,
                                                                                                     gm.generate_in_surface_num_pts))
        else:
            log_equivalent_command(self.session, "artiax gen in surface #{} regular numPts {}".format(gm.id_string,
                                                                                                     gm.generate_in_surface_num_pts))

    def _generate_in_surface_options_changed(self):
        artia = self.session.ArtiaX
        gm = artia.geomodels.get(artia.options_geomodel)

        gm.generate_in_surface_radius = self.generate_in_surface_widget.radius
        gm.generate_in_surface_method = self.generate_in_surface_widget.method
        gm.generate_in_surface_num_pts = self.generate_in_surface_widget.num_pts

    def _generate_on_surface(self):
        artia = self.session.ArtiaX
        gm = artia.geomodels.get(artia.options_geomodel)

        from .util.generate_points import generate_points_on_surface
        generate_points_on_surface(self.session, gm, gm.generate_on_surface_num_pts, gm.generate_on_surface_radius, gm.generate_on_surface_method, exact_num=True)

        from chimerax.core.commands import log_equivalent_command
        if gm.generate_on_surface_method.lower() == 'poisson':
            log_equivalent_command(self.session, "artiax gen on surface #{} poisson {} radius {} exactNum true".format(gm.id_string, gm.generate_on_surface_num_pts,
                                                                                                     gm.generate_on_surface_radius))
        else:
            log_equivalent_command(self.session, "artiax gen on surface #{} uniform {}".format(gm.id_string,
                                                                                                gm.generate_on_surface_num_pts))

    def _generate_on_surface_options_changed(self):
        artia = self.session.ArtiaX
        gm = artia.geomodels.get(artia.options_geomodel)

        gm.generate_on_surface_radius = self.generate_on_surface_widget.radius
        gm.generate_on_surface_method = self.generate_on_surface_widget.method
        gm.generate_on_surface_num_pts = self.generate_on_surface_widget.num_pts

    def take_snapshot(self, session, flags):
        return
        {
            'version': 1,
            'current text': self.line_edit.text()
        }

    @classmethod
    def restore_snapshot(class_obj, session, data):
        # Instead of using a fixed string when calling the constructor below,
        # we could have save the tool name during take_snapshot()
        # (from self.tool_name, inherited from ToolInstance) and used that saved
        # tool name. There are pros and cons to both approaches.
        inst = class_obj(session, "Tomo Bundle")
        inst.line_edit.setText(data['current text'])
        return inst

    def _reorient_from_order(self):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        from chimerax.geometry import z_align
        from numpy import asarray
        last_part = None
        rot = None
        for curr_id in pl.particle_ids:
            curr_part = pl.get_particle(curr_id)
            if last_part is not None:
                curr_pos = asarray(curr_part.coord)
                last_pos = asarray(last_part.coord)
                rot = z_align(last_pos, curr_pos).zero_translation().inverse()
                last_part.rotation = rot
            last_part = curr_part
        if rot is not None:
            last_part.rotation = rot
        pl.update_places()

    def _reorder_from_links(self):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        from chimerax.markers.markers import selected_markers
        import numpy as np

        atom_pairs = np.asarray(selected_markers(self.session).bonds.unique().atoms)
        nr_atoms = len(atom_pairs[0]) + 1
        if nr_atoms > 0:
            # Find start and check that chain ok
            starting_atom_index = np.zeros((0, 1), dtype=np.int32)
            cycle = False
            for i, atom in enumerate(atom_pairs[0]):
                if len(np.where(atom_pairs[0] == atom)[0]) != 1:
                    cycle = True
                if atom not in atom_pairs[1]:
                    starting_atom_index = np.append(starting_atom_index, i)
            if len(starting_atom_index) == 0 or cycle:
                self.session.logger.warning("Select at least one chain of particles with a start.")
                return

            # Add particles to new list
            artia.create_partlist(name="reordered " + pl.name)
            new_pl = artia.partlists.child_models()[-1]
            for start in starting_atom_index:
                atom_index = start
                start_atoms = atom_pairs[0]
                end_atoms = atom_pairs[1]
                # First one manually
                start_part = pl.get_particle(start_atoms[atom_index].particle_id)
                new_pl.new_particle(start_part.origin, start_part.translation, start_part.rotation)
                while True:
                    second_atom = end_atoms[atom_index]
                    second_part = pl.get_particle(end_atoms[atom_index].particle_id)
                    new_pl.new_particle(second_part.origin, second_part.translation, second_part.rotation)
                    start_atoms = np.delete(start_atoms, atom_index)
                    end_atoms = np.delete(end_atoms, atom_index)
                    if len(np.where(start_atoms == second_atom)[0]) > 0:
                        atom_index = np.where(start_atoms == second_atom)[0][0]
                    else:
                        break

    def _reorder_to_closest(self):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        if len(pl.particle_ids[pl.selected_particles]) != 1:
            self.session.logger.warning("Select exactly one particle as a starting point.")
            return

        artia.create_partlist(name="reordered " + pl.name)
        new_pl = artia.partlists.child_models()[-1]
        start_part = pl.get_particle(pl.particle_ids[pl.selected_particles][0])
        new_pl.new_particle(start_part.origin, start_part.translation, start_part.rotation)

        import numpy as np
        part_index = np.where(pl.selected_particles)[0][0]
        particles = [None]*len(pl.particle_ids)
        for i, p_id in enumerate(pl.particle_ids):
            particles[i] = pl.get_particle(p_id)
        while len(particles) > 1:
            curr_pos = np.asarray(particles[part_index].coord)
            particles = np.delete(particles, part_index)
            distances = np.zeros((len(particles), 1))
            for i, part in enumerate(particles):
                distances[i] = np.linalg.norm(np.asarray(part.coord) - curr_pos)
            closest_index = np.argmin(distances)
            closest_part = particles[closest_index]
            new_pl.new_particle(closest_part.origin, closest_part.translation, closest_part.rotation)
            part_index = closest_index

    # ==============================================================================
    # Options Menu for Geometric Models ============================================
    # ==============================================================================

    def _build_geomodel_widget(self):
        self.geomodel_area = QScrollArea()
        self.geomodel_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.geomodel_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.geomodel_area.setWidgetResizable(True)
        # Define the overall layout
        geomodel_layout = QVBoxLayout()
        geomodel_layout.setAlignment(Qt.AlignTop)

        # Display current geomodel name
        group_current_geomodel = QGroupBox("Current Geometric Model")
        group_current_geomodel.setSizePolicy(QSizePolicy(QSizePolicy.Maximum,
                                                         QSizePolicy.Maximum))
        group_current_geomodel.setFont(self.font)
        current_geomodel_layout = QHBoxLayout()
        self.current_geomodel_label = QLabel("")
        self.current_geomodel_label.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
                                                              QSizePolicy.Minimum))
        current_geomodel_layout.addWidget(self.current_geomodel_label)
        group_current_geomodel.setLayout(current_geomodel_layout)

        # Define a group for the visualization sliders
        color_select = QGroupBox("Color Options:")
        color_select.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
                                               QSizePolicy.Maximum))
        color_select.setFont(self.font)
        color_select.setCheckable(True)

        # Define the color settings
        group_color_layout = QVBoxLayout()

        self.geomodel_color_selection = ColorGeomodelWidget(self.session)
        self.geomodel_color_selection.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
                                                                QSizePolicy.Maximum))
        group_color_layout.addWidget(self.geomodel_color_selection)
        group_color_layout.addStretch()

        color_select.setLayout(group_color_layout)

        # Generating points options
        from .widgets import GenerateInSurfaceOptions, GenerateOnSurfaceOptions
        generate_points = QGroupBox("Generate Points:")
        generate_points.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
                                               QSizePolicy.Maximum))
        generate_points.setFont(self.font)
        generate_points.setCheckable(True)
        generate_points_layout = QVBoxLayout()
        self.generate_in_surface_widget = GenerateInSurfaceOptions()
        self.generate_on_surface_widget = GenerateOnSurfaceOptions()

        generate_points_layout.addWidget(self.generate_in_surface_widget)
        generate_points_layout.addWidget(self.generate_on_surface_widget)
        generate_points.setLayout(generate_points_layout)


        # Define the model specific options
        self.models = {"Sphere": 0, "CurvedLine": 1, "Surface": 2, "TriangulationSurface": 3, "Boundary": 4,
                       "ArbitraryModel": 5}
        self.model_options = QStackedWidget()

        self.sphere_options = SphereOptions(self.session)
        self.curved_options = CurvedLineOptions(self.session)
        self.plane_options = PlaneOptions(self.session)
        self.tri_surface_options = TriangulateOptions(self.session)
        self.boundary_options = BoundaryOptions(self.session)
        self.arbitrary_model_options = ArbitraryModelOptions(self.session)

        self.model_options.addWidget(self.sphere_options)
        self.model_options.addWidget(self.curved_options)
        self.model_options.addWidget(self.plane_options)
        self.model_options.addWidget(self.tri_surface_options)
        self.model_options.addWidget(self.boundary_options)
        self.model_options.addWidget(self.arbitrary_model_options)

        geomodel_layout.addWidget(group_current_geomodel)
        geomodel_layout.addWidget(color_select)
        geomodel_layout.addWidget(generate_points)
        geomodel_layout.addWidget(self.model_options)

        # And finally set the layout of the widget
        geomodel_widget = QWidget()
        geomodel_widget.setContentsMargins(0, 0, 0, 0)
        geomodel_widget.setLayout(geomodel_layout)
        self.geomodel_area.setWidget(geomodel_widget)

    def _update_geomodel_ui(self):
        artia = self.session.ArtiaX
        geomodel = artia.geomodels.get(artia.options_geomodel)

        # Set new model
        self.geomodel_color_selection.set_geomodel(geomodel)
        self.generate_in_surface_widget.blockSignals(True)
        self.generate_in_surface_widget.method = geomodel.generate_in_surface_method
        self.generate_in_surface_widget.num_pts = geomodel.generate_in_surface_num_pts
        self.generate_in_surface_widget.radius = geomodel.generate_in_surface_radius
        self.generate_in_surface_widget.blockSignals(False)
        self.generate_on_surface_widget.blockSignals(True)
        self.generate_on_surface_widget.method = geomodel.generate_on_surface_method
        self.generate_on_surface_widget.num_pts = geomodel.generate_on_surface_num_pts
        self.generate_on_surface_widget.radius = geomodel.generate_on_surface_radius
        self.generate_on_surface_widget.blockSignals(False)
        if type(geomodel).__name__ == "Sphere":
            self.sphere_options.set_sphere(geomodel)
        elif type(geomodel).__name__ == "CurvedLine":
            self.curved_options.set_line(geomodel)
        elif type(geomodel).__name__ == "Surface":
            self.plane_options.set_plane(geomodel)
        elif type(geomodel).__name__ == "TriangulationSurface":
            self.tri_surface_options.set_tri_surface(geomodel)
        elif type(geomodel).__name__ == "Boundary":
            self.boundary_options.set_boundary(geomodel)
        elif type(geomodel).__name__ == "ArbitraryModel":
            self.arbitrary_model_options.set_arbitrary_model(geomodel)

        self.model_options.setCurrentIndex(self.models[self.curr_model])

    def _geomodel_changed(self, name, model):
        artia = self.session.ArtiaX
        opgm = artia.geomodels.get(artia.options_geomodel)

        if model is opgm:
            self._update_geomodel_ui()

    def delete(self):
        self.session.triggers.remove_handler(self.add_from_session.handler_add)
        self.session.triggers.remove_handler(self.add_from_session.handler_del)

        ToolInstance.delete(self)
