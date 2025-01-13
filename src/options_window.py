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
        tooltip = 'Low pass filter the current tomogram. Use Gaussian or Cosine decay. If the unit is set to pixels and the ' \
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

        ### Coloring Tomogram ###

        # Create a group box to hold the coloring-related widgets
        self.color_tomogram_group = QGroupBox("Tomogram Arithmetics")
        self.color_tomogram_group.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum))

        # Create a layout for the group box
        coloring_layout = QVBoxLayout()

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

        # Add the "Select Tomogram" group to the coloring layout
        coloring_layout.addWidget(self.select_tomogram_group)





        # Add the checkboxes for operations (Addition, Subtraction, Multiplication)
        operations_layout = QHBoxLayout()  # Use a horizontal layout for checkboxes
        self.addition_checkbox = QCheckBox("Addition")
        self.subtraction_checkbox = QCheckBox("Subtraction")
        self.multiplication_checkbox = QCheckBox("Multiplication")

        # Add checkboxes to the operations layout
        operations_layout.addWidget(self.addition_checkbox)
        operations_layout.addWidget(self.subtraction_checkbox)
        operations_layout.addWidget(self.multiplication_checkbox)

        # Connect the checkbox state change to the update function
        self.addition_checkbox.stateChanged.connect(self.update_operation_info)
        self.subtraction_checkbox.stateChanged.connect(self.update_operation_info)
        self.multiplication_checkbox.stateChanged.connect(self.update_operation_info)

        # Add the operations layout to the coloring layout
        coloring_layout.addLayout(operations_layout)




        # Add a QLabel to show the current operation and selected tomograms
        self.operation_info_label = QLabel("Current operation: None")
        self.operation_info_label.setAlignment(Qt.AlignCenter)

        # Add the label to the layout (somewhere appropriate in your layout)
        coloring_layout.addWidget(self.operation_info_label)




        # Create the "Color Tomogram" button
        self.color_tomogram_button = QPushButton("Compute")
        self.color_tomogram_button.setToolTip("Color the tomogram according to segmentation")

        # Connect the button to the method
        self.color_tomogram_button.clicked.connect(self.tomo_arithmetics)

        # Add the button to the coloring layout (at the end)
        coloring_layout.addWidget(self.color_tomogram_button)

        # Set the layout for the coloring group box
        self.color_tomogram_group.setLayout(coloring_layout)

        # Add groups to layout
        tomo_layout.addWidget(group_current_tomo)
        tomo_layout.addWidget(group_pixelsize)
        tomo_layout.addWidget(self.color_tomogram_group)
        tomo_layout.addWidget(group_contrast)
        tomo_layout.addWidget(group_slices)
        tomo_layout.addWidget(group_orthoplanes)
        tomo_layout.addWidget(group_process)
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


    # def split_volume_by_connected_colors(self):
    #     """
    #     Create new volumes for each connected colored region in the surface.
    #
    #     Args:
    #         surface: The surface object containing triangle and vertex color data.
    #     Returns:
    #         A list of new volumes split by color.
    #     """
    #     artia = self.session.ArtiaX
    #     tomo = artia.tomograms.get(artia.options_tomogram)
    #     volume=tomo
    #     print("Split Tomogram button clicked!")
    #
    #     #surface=Volume.VolumeSurface
    #
    #     # Get the number of surfaces in the volume
    #     num_surfaces = len(volume.surfaces)
    #
    #     # Print the number of surfaces
    #     print(f"There are {num_surfaces} surfaces in the volume.")
    #
    #     surface = volume.surfaces[0]
    #
    #     if hasattr(surface, 'triangles'):
    #         triangles = surface.triangles
    #         print("Triangles:", triangles)
    #
    #     if hasattr(surface, 'vertex_colors'):
    #         vertex_colors = surface.vertex_colors
    #         print("Vertex Colors:", vertex_colors)
    #
    #     if hasattr(surface, 'vertices'):
    #         vertices = surface.vertices
    #         print("Vertices:", vertices)
    #
    #
    #     if surface == None:
    #         raise UserError("No surface found")
    #
    #     from chimerax.surface import connected_triangles
    #
    #     if surface.vertex_colors is None:
    #         raise ValueError("Surface does not have vertex colors assigned.")
    #
    #     # Step 1: Group triangles by colors
    #     color_to_triangles=self.group_triangles_by_color(surface)
    #
    #     # Step 2: Generate masked grid data for each color group
    #     grids = []
    #
    #     print(f"color to triangles{color_to_triangles}")
    #     num_surfaces = len(color_to_triangles)
    #
    #     # Print the number of surfaces
    #     print(f"There are {num_surfaces} entries in color_to_triangles.")
    #
    #     for color, triangle_indices in color_to_triangles.items():
    #         # Mask triangles not belonging to this color group
    #         masked_triangles = np.isin(np.arange(len(surface.triangles)), triangle_indices)
    #         grid = self._create_grid_for_masked_triangles(volume, masked_triangles)
    #         grid.zone_color = color  # Assign the color to the grid
    #         grids.append(grid)
    #
    #     # Step 3: Create new volumes from grids
    #
    #     print("grids are done")
    #     for i, grid in enumerate(grids):
    #         print(f"Grid {i}: Name={grid.name}, Dimensions={grid.size}")
    #
    #     from chimerax.map import volume_from_grid_data
    #
    #     new_volumes = [volume_from_grid_data(g, self.session, open_model=False) for g in grids]
    #     for v in new_volumes:
    #         v.copy_settings_from(volume, copy_region=False)
    #         rgba = tuple(c / 255 for c in v.data.zone_color)
    #         v.set_parameters(surface_colors=[rgba] * len(v.surfaces))
    #         v.display = True
    #
    #     # Step 4: Handle model hierarchy and visibility
    #     volume.display = False
    #     if len(new_volumes) == 1:
    #         self.session.models.add(new_volumes)
    #     else:
    #         self.session.models.add_group(new_volumes, name=f"{volume.name} split")
    #
    #     return new_volumes
    #
    # def group_triangles_by_color(self, surface):
    #     """
    #         Groups the triangles of a surface based on their vertex colors.
    #
    #         Parameters:
    #         ----------
    #         surface : Surface
    #             The surface object containing information about vertices, triangles,
    #             and their associated colors. The `surface` object should have:
    #             - `vertex_colors`: A numpy array of shape (N, 4) where N is the number
    #               of vertices. Each row represents the RGBA color of a vertex.
    #
    #         Returns:
    #         -------
    #         color_to_triangles : dict
    #             A dictionary where the keys are tuples representing unique RGBA colors
    #             (e.g., `(R, G, B, A)`), and the values are arrays of indices pointing
    #             to triangles that have vertices of the corresponding color.
    #
    #         Notes:
    #         -----
    #         - Triangles are grouped by the vertex color. If a vertex is shared by multiple
    #           triangles, all those triangles will be included in the corresponding group.
    #         """
    #     # Step 1: Identify unique colors from the surface's vertex colors
    #     unique_colors = np.unique(surface.vertex_colors, axis=0)
    #     color_to_triangles = {}
    #
    #     # Step 2: Group triangles by their vertex colors
    #     for color in unique_colors:
    #         # Find all indices where the vertex color matches this unique color
    #         color_indices = np.where((surface.vertex_colors == color).all(axis=1))[0]
    #         color_to_triangles[tuple(color)] = color_indices
    #
    #     return color_to_triangles
    #
    # def _create_grid_for_masked_triangles(self, volume, masked_triangles):
    #     # """
    #     #     Generate grid data for a subset of triangles in the volume.
    #     #
    #     #     Args:
    #     #         volume: The volume object.
    #     #         masked_triangles: A boolean mask for triangles to include in the grid.
    #     #     Returns:
    #     #         A grid object with only the specified triangles.
    #     #     """
    #     # ijk_min, ijk_max, ijk_step = volume.region
    #     # from chimerax.map_data import GridSubregion
    #     # sg = GridSubregion(volume.data, ijk_min, ijk_max)
    #     # print(f"Subregion dimensions (ijk_min to ijk_max): {ijk_min} to {ijk_max}, ijk_step={ijk_step}")
    #     # print(f"Grid shape (sg): {sg.size}")  # Assuming GridSubregion has a data attribute.
    #     # pixsize=sg.step[0]
    #     #
    #     #
    #     # # Ensure that surface vertices are passed as zone_points
    #     # from chimerax.map_data import zone_mask, masked_grid_data
    #     #
    #     # vertices = volume.surfaces[0].vertices
    #     # # Create a mask for the vertices corresponding to the selected triangles
    #     # vertex_mask = np.zeros(len(vertices), dtype=bool)
    #     #
    #     # # Use masked_triangles to set the mask for the corresponding vertices
    #     # for i, triangle_indices in enumerate(volume.surfaces[0].triangles):
    #     #     if masked_triangles[i]:  # If the triangle is selected
    #     #         vertex_mask[triangle_indices] = True  # Mark the corresponding vertices
    #     #
    #     # print(f"vertex_mask{vertex_mask}")
    #     # num_surfaces = len(vertex_mask)
    #     #
    #     # # Print the number of surfaces
    #     # print(f"There are {num_surfaces} entries in vertex_mask.")
    #     #
    #     # # Extract only the selected vertices
    #     # selected_vertices = vertices[vertex_mask]
    #     #
    #     # # Print diagnostic info
    #     # print(f"Selected vertices: {selected_vertices}")
    #     # print(f"Total vertices: {len(vertices)}")
    #     # print(f"Selected vertices: {len(selected_vertices)}")
    #     # print(f"Selected percentage: {len(selected_vertices) / len(vertices) * 100:.2f}%")
    #     #
    #     # print(f"pixsize: {pixsize}")
    #     # # Use only the selected vertices as zone_points
    #     # selected_vertices_scaled = selected_vertices / pixsize
    #     # print(f"Number of scaled selected vertices: {len(selected_vertices_scaled)}")
    #     # print(f"Scaled selected vertices: {selected_vertices_scaled}")
    #     # print(f"Scaled vertices min: {selected_vertices_scaled.min(axis=0)}")
    #     # print(f"Scaled vertices max: {selected_vertices_scaled.max(axis=0)}")
    #     # print(f"Grid size: {sg.size}")
    #     # grid_shape = np.array(sg.size)  # (1024, 1440, 800)
    #     # zone_radius=1000
    #     # voxel_radius = zone_radius / pixsize
    #     # print(f"Voxel_radius {voxel_radius}")
    #     # print(f"Scaled vertices within bounds: {np.all((selected_vertices_scaled >= 0) & (selected_vertices_scaled < grid_shape))}")
    #     # mask = self.custom_zone_mask(sg, selected_vertices_scaled, zone_radius=voxel_radius, invert_mask=False)
    #     # print(f"Zone mask shape: {mask.shape}")
    #     # #mask = np.transpose(mask, (2, 1, 0))
    #     # # Replace the mask with one that is fully True
    #     # #mask = np.ones(sg.size, dtype=bool)
    #     # print(f"Transposed mask shape: {mask.shape}")
    #     # print(np.unique(mask))
    #     # print(f"Mask filled with True: {np.sum(mask)} out of {mask.size}")
    #     # indices = np.argwhere(mask)
    #     # min_coords = indices.min(axis=0)
    #     # max_coords = indices.max(axis=0)
    #     # print(f"Bounding box: Min {min_coords}, Max {max_coords}")
    #     #
    #     #
    #     #
    #     #
    #     # # Pass the actual surface vertices as zone_points
    #     # #mask = zone_mask(sg, vertices, zone_radius=1, invert_mask=False, zone_point_mask_values=vertex_mask)
    #     #
    #     # # Create the masked grid
    #     # grid = masked_grid_data(sg, mask, 1)  # '1' is used to select the region
    #     # grid.name = f"{volume.data.name}_{np.sum(masked_triangles)}triangles"
    #     # #print(dir(grid))
    #     # #print(dir(grid.data))
    #     # print(f"Grid size: {grid.size}")
    #     # if hasattr(grid, 'array'):
    #     #     print(f"Grid array shape: {grid.array.shape}")
    #     # else:
    #     #     print("Grid does not have an array attribute.")
    #     # if hasattr(grid, 'matrix'):
    #     #     print(f"Grid matrix shape: {grid.matrix().shape}")  # Use method call if `matrix` is callable
    #     # elif hasattr(grid, 'full_matrix'):
    #     #     print(f"Grid full matrix shape: {grid.full_matrix().shape}")
    #     # else:
    #     #     print("Grid has no matrix or full_matrix attributes.")
    #     # if hasattr(grid, 'submatrix'):
    #     #     submat = grid.submatrix((0, 0, 0), (1, 1, 1))  # Try with a minimal slice
    #     #     print(f"Submatrix slice shape: {submat.shape}")
    #     # print(f"Origin: {grid.origin}")  # May provide grid origin
    #     # print(f"Step size: {grid.step}")  # Spacing between voxels
    #     # print(f"Masked grid data name: {grid.name}, Masked grid size: {grid.size}")
    #     # print(f"Mask shape: {mask.shape}, Expected shape: {grid.size}")
    #     #
    #     # return grid
    #
    #     """
    #         Generate grid data for a subset of triangles in the volume.
    #
    #         Args:
    #             volume: The volume object.
    #             masked_triangles: A boolean mask for triangles to include in the grid.
    #         Returns:
    #             A grid object with only the specified triangles.
    #         """
    #     ijk_min, ijk_max, ijk_step = volume.region
    #     from chimerax.map_data import GridSubregion
    #     sg = GridSubregion(volume.data, ijk_min, ijk_max)
    #     pixsize = sg.step[0]
    #
    #     # Ensure that surface vertices are passed as zone_points
    #     vertices = volume.surfaces[0].vertices
    #     vertex_mask = np.zeros(len(vertices), dtype=bool)
    #
    #     # Use masked_triangles to set the mask for the corresponding vertices
    #     for i, triangle_indices in enumerate(volume.surfaces[0].triangles):
    #         if masked_triangles[i]:
    #             vertex_mask[triangle_indices] = True  # Mark the corresponding vertices
    #
    #     # Extract only the selected vertices
    #     selected_vertices = vertices[vertex_mask]
    #
    #     # Scale selected vertices by the pixel size (voxel units)
    #     selected_vertices_scaled = selected_vertices / pixsize
    #
    #     # Initialize the mask array (e.g., with the same shape as the grid)
    #     grid_shape = np.array(sg.size)  # (1024, 1440, 800)
    #     mask = np.zeros(grid_shape, dtype=bool)
    #
    #     # Iterate through the selected vertices and mark the corresponding entries in the mask
    #     for vertex in selected_vertices_scaled:
    #         # Round the scaled vertex coordinates to nearest integers (voxel indices)
    #         voxel_coords = np.round(vertex).astype(int)
    #
    #         # Check if the voxel coordinates are within the bounds of the grid
    #         if np.all(voxel_coords >= 0) and np.all(voxel_coords < grid_shape):
    #             mask[tuple(voxel_coords)] = True
    #
    #     # Final mask status
    #     print(f"Mask shape: {mask.shape}")
    #     print(f"Mask filled with True: {np.sum(mask)} out of {mask.size}")
    #
    #     # Create the masked grid
    #     from chimerax.map_data import masked_grid_data
    #     grid = masked_grid_data(sg, mask, 1)
    #     grid.name = f"{volume.data.name}_{np.sum(masked_triangles)}triangles"
    #
    #     print(f"Grid size: {grid.size}")
    #     if hasattr(grid, 'array'):
    #         print(f"Grid array shape: {grid.array.shape}")
    #     else:
    #         print("Grid does not have an array attribute.")
    #     if hasattr(grid, 'matrix'):
    #         print(f"Grid matrix shape: {grid.matrix().shape}")
    #     elif hasattr(grid, 'full_matrix'):
    #         print(f"Grid full matrix shape: {grid.full_matrix().shape}")
    #     else:
    #         print("Grid has no matrix or full_matrix attributes.")
    #     if hasattr(grid, 'submatrix'):
    #         submat = grid.submatrix((0, 0, 0), (1, 1, 1))  # Try with a minimal slice
    #         print(f"Submatrix slice shape: {submat.shape}")
    #     print(f"Origin: {grid.origin}")  # May provide grid origin
    #     print(f"Step size: {grid.step}")  # Spacing between voxels
    #     print(f"Masked grid data name: {grid.name}, Masked grid size: {grid.size}")
    #
    #     return grid
    #
    #
    # def custom_zone_mask(self, grid_data, zone_points, zone_radius, invert_mask=False, zone_point_mask_values=None):
    #     """
    #     Custom version of the zone_mask function with debugging output.
    #     """
    #
    #     # Convert zone_points to a numpy array (ensure it's in float64)
    #     zone_points = np.array(zone_points, dtype=np.float64)
    #
    #     # Initialize mask
    #     shape = tuple(reversed(grid_data.size))
    #     mask_3d = np.zeros(shape, dtype=np.int8)
    #     mask_1d = mask_3d.ravel()
    #
    #     # Debugging: Show the initial mask state
    #     print("Initial mask state:", mask_3d.shape)
    #
    #     # If zone_point_mask_values are not provided, set the mask value
    #     if zone_point_mask_values is None:
    #         mask_value = 1 if not invert_mask else 0
    #     else:
    #         mask_value = 1
    #
    #     # Check for grid size limit and process the grid efficiently
    #     size_limit = 2 ** 22  # limit to avoid too large arrays
    #     if mask_3d.size > size_limit:
    #         xsize, ysize, zsize = grid_data.size
    #         grid_points = np.indices((xsize, ysize, 1), dtype=np.float64)  # Convert to float64
    #
    #         # Reshape grid_points to be a 2D array where each row is a (x, y, z) point
    #         grid_points = grid_points.reshape(3, -1).T  # Reshape to (n_points, 3)
    #
    #         grid_data.ijk_to_xyz_transform.transform_points(grid_points, in_place=True)
    #         zstep = [grid_data.ijk_to_xyz_transform.matrix[a][2] for a in range(3)]
    #
    #         for z in range(zsize):
    #             i1, i2, n1 = find_closest_points(grid_points, zone_points, zone_radius)
    #             print(f"i1:{i1}, i2:{i2}, n1:{n1}")
    #             offset = xsize * ysize * z
    #
    #             if zone_point_mask_values is None:
    #                 mask_1d[i1 + offset] = mask_value
    #             else:
    #                 mask_1d[i1 + offset] = zone_point_mask_values[n1]
    #
    #             # Debugging: Show how points are marked
    #             print(f"Layer {z}: Marked grid points within zone_radius")
    #             print(f"Marked grid points indices in this layer: {i1 + offset}")
    #
    #     else:
    #         grid_points = np.indices(grid_data.size, dtype=np.float64)  # Convert to float64
    #
    #         # Reshape grid_points to be a 2D array where each row is a (x, y, z) point
    #         grid_points = grid_points.reshape(3, -1).T  # Reshape to (n_points, 3)
    #
    #         grid_data.ijk_to_xyz_transform.transform_points(grid_points, in_place=True)
    #         i1, i2, n1 = find_closest_points(grid_points, zone_points, zone_radius)
    #
    #         # Debugging: Show which grid points are affected by each zone_point
    #         print(f"Processing zone_points: {len(zone_points)} points within {zone_radius} radius.")
    #         for idx, zone_point in enumerate(zone_points):
    #             print(f"Zone Point {idx}: {zone_point}")
    #
    #         # Show the indices of the grid points being marked
    #         print(f"Indices of grid points marked within radius: {i1}")
    #
    #         if zone_point_mask_values is None:
    #             mask_1d[i1] = mask_value
    #         else:
    #             mask_1d[i1] = zone_point_mask_values[n1]
    #
    #     # Final mask status
    #     print(f"Final mask has {np.sum(mask_1d)} marked points (True values) out of {mask_3d.size}.")
    #
    #     # Return the 3D mask
    #     return mask_3d

    def tomo_arithmetics(self):

        # Get current tomogram
        artia = self.session.ArtiaX
        self.tomo_math = artia.tomograms.get(artia.options_tomogram)
        matrix_1 = self.tomo_math.data.matrix()
        #volume = tomo
        print("Split Tomogram button clicked!")
        #surface = volume.surfaces[0]
        #matrix_1=surface.data.matrix()
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

        # Get surface of selected tomogram/segmentation
        #segm = selected_tomo.surfaces[0]

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

        if sum([addition, subtraction, multiplication]) > 1:
            raise UserError("More than one operation selected. Please select only one.")

        if sum([addition, subtraction, multiplication]) == 0:
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

            name1=self.tomo_math.name
            name2=self.selected_tomo_math.name
            # Remove file extensions from the tomogram names
            name1_base = os.path.splitext(name1)[0]
            name2_base = os.path.splitext(name2)[0]

            # Build the new tomogram name dynamically without file extensions
            name = f"{name1_base}_{name2_base}_{key}"

            self.tomo_math.create_tomo_from_array(array,name)

        # Sort triangles of segmentation by color
        # triangles_per_color = self.group_triangles_by_color(surface=segm)
        # print(f"triangles per color dict: {triangles_per_color}")
        #
        # # Prepare arguments for the color_zone function
        # points = []
        # point_colors = []
        #
        # for color, triangle_indices in triangles_per_color.items():
        #     print(f"Processing color: {color}, triangle indices: {triangle_indices}")
        #
        #     # Calculate centroids for all triangles of this color
        #     for tri_idx in triangle_indices:
        #         triangle = segm.vertices[segm.triangles[tri_idx]]  # Get the 3 vertices of the triangle
        #         print(f"Triangle vertices for index {tri_idx}: {triangle}")
        #
        #         # Compute centroid of the triangle
        #         centroid = triangle.mean(axis=0)
        #         print(f"Centroid of triangle {tri_idx}: {centroid}")
        #
        #         # Add this centroid and its associated color
        #         points.append(centroid)
        #         point_colors.append(color)

        # Convert lists to numpy arrays for compatibility
        # points = np.array(points)  # Shape (N, 3), where N is the total number of triangles
        # point_colors = np.array(point_colors, dtype=np.uint8)  # Shape (N, 4)
        # print(f"points shape: {points.shape}")
        # print(f"points: {points}")
        # print(f"point_colors shape: {point_colors.shape}")
        # print(f"point_colors: {point_colors}")
        #
        # # Define the radius for the color zone
        # radius = 20.0
        #
        # from chimerax.surface.colorzone import color_zone
        #
        # # Apply the color zoning to the surface
        # color_zone(surface=surface,points=points,point_colors=point_colors,distance=radius,sharp_edges=False,far_color=None,auto_update=True)

        # print("Surface coloring completed!")

        #self.color_image(triangles_per_color=triangles_per_color, segm=segm, volume=volume)

    import numpy as np

    # def color_image(self, segm, triangles_per_color, volume):
    #
    #
    #     # Create the 3D segmentation map
    #     segmentation_map = self.create_3d_segmentation_map(segm, triangles_per_color, volume)
    #
    #     # Get the shape of the array
    #     shape = segmentation_map.shape
    #
    #     # Print lengths in each dimension
    #     x_length, y_length, z_length = shape
    #     print(f"Length in X (rows): {x_length}")
    #     print(f"Length in Y (columns): {y_length}")
    #     print(f"Length in Z (depth): {z_length}")
    #
    #     # For completeness, show size and count of non-zeros as before
    #     total_size = segmentation_map.size
    #     non_zero_count = np.count_nonzero(segmentation_map)
    #
    #     print(f"Total size of the array: {total_size}")
    #     print(f"Number of non-zero entries: {non_zero_count}")
    #
    #     # Convert the 3D segmentation map to a ChimeraX-compatible format
    #     #segmentation = self.create_segmentation_from_map(segmentation_map)
    #
    #     # Use the segmentation_colors function for the volume display
    #     from chimerax.segment.segment import segmentation_colors
    #     segmentation_colors(session=self.session, segmentations=segmentation_map, color=None, map=volume)
    #
    # def create_3d_segmentation_map(self, segm, triangles_per_color, volume):
    #     """
    #     Create a 3D segmentation map where each voxel corresponds to a segment ID.
    #
    #     Parameters:
    #     segm: The segmentation surface model (contains vertices and triangles).
    #     triangles_per_color: Dictionary mapping colors to triangle indices of the segm.
    #     volume: tomogram volume which is supposed to be colored
    #
    #     Returns:
    #     segmentation_map: 3D numpy array representing the segmentation volume.
    #     """
    #     grid_size=volume.size
    #     # Initialize a 3D array for the segmentation map
    #     segmentation_map = np.zeros(grid_size, dtype=int)
    #
    #     # Map colors to segment IDs
    #     color_to_segment_id = {}
    #     segment_counter = 1
    #     for color in triangles_per_color.keys():
    #         color_to_segment_id[color] = segment_counter
    #         segment_counter += 1
    #
    #     #reduced version for debugging
    #     # Loop through colors and their associated triangle indices
    #     # for color, triangle_indices in triangles_per_color.items():
    #     #     segment_id = color_to_segment_id[color]
    #     #     print(f"Now processing color: {color}")
    #     #
    #     #     # Limit to the first 5 triangles (or less if fewer exist)
    #     #     limited_triangle_indices = triangle_indices[:5]
    #     #
    #     #     for tri_idx in limited_triangle_indices:
    #     #         # Get the triangle vertices
    #     #         vertices = segm.vertices[segm.triangles[tri_idx]]
    #     #         print(f"Triangle vertices: {vertices}")
    #     #
    #     #         # Calculate the bounding box of the triangle in the 3D grid
    #     #         min_coords = np.floor(vertices.min(axis=0)).astype(int)
    #     #         max_coords = np.ceil(vertices.max(axis=0)).astype(int)
    #     #         print(f"Bounding box - min_coords: {min_coords}, max_coords: {max_coords}")
    #     #
    #     #         # Iterate over voxels within the bounding box
    #     #         for x in range(min_coords[0], max_coords[0] + 1):
    #     #             for y in range(min_coords[1], max_coords[1] + 1):
    #     #                 for z in range(min_coords[2], max_coords[2] + 1):
    #     #                     # Check if the voxel lies within the triangle
    #     #                     voxel_center = np.array([x + 0.5, y + 0.5, z + 0.5])
    #     #                     print(f"Voxel center: {voxel_center}")
    #     #                     if self.is_point_in_triangle(voxel_center, vertices):
    #     #                         segmentation_map[x, y, z] = segment_id
    #     #                         print(f"Marked voxel ({x}, {y}, {z}) with segment ID {segment_id}")
    #
    #
    #     #Old version
    #     # Iterate through each color and its associated triangles
    #     for color, triangle_indices in triangles_per_color.items():
    #         segment_id = color_to_segment_id[color]
    #         print(f"now color:{color}")
    #
    #         for tri_idx in triangle_indices:
    #             # Get the triangle vertices
    #             vertices = segm.vertices[segm.triangles[tri_idx]]
    #             print(f"vertices: {vertices}")
    #
    #             # Calculate the bounding box of the triangle in the 3D grid
    #             min_coords = np.floor(vertices.min(axis=0)).astype(int)
    #             max_coords = np.ceil(vertices.max(axis=0)).astype(int)
    #             print(f"min_coords: {min_coords}, max_coords: {max_coords}")
    #
    #             # Iterate over voxels within the bounding box
    #             for x in range(min_coords[0], max_coords[0] + 1):
    #                 for y in range(min_coords[1], max_coords[1] + 1):
    #                     for z in range(min_coords[2], max_coords[2] + 1):
    #                         # Check if the voxel lies within the triangle
    #                         voxel_center = np.array([x + 0.5, y + 0.5, z + 0.5])
    #                         print(f"voxel_center: {voxel_center}")
    #                         if self.is_point_in_triangle(voxel_center, vertices):
    #                             segmentation_map[x, y, z] = segment_id
    #                             print(f"marked {x},{y},{z} with {segment_id}")
    #
    #     return segmentation_map
    #
    # def is_point_in_triangle(self, point, triangle_vertices):
    #     """
    #     Check if a point lies within a triangle in 3D space using barycentric coordinates.
    #
    #     Parameters:
    #     point: The 3D coordinates of the point.
    #     triangle_vertices: The 3 vertices of the triangle.
    #
    #     Returns:
    #     True if the point is inside the triangle; False otherwise.
    #     """
    #     # Unpack the triangle vertices
    #     v0, v1, v2 = triangle_vertices
    #
    #     # Calculate the vectors relative to the first vertex
    #     v0v1 = v1 - v0
    #     v0v2 = v2 - v0
    #     v0p = point - v0
    #
    #     # Compute dot products
    #     dot00 = np.dot(v0v2, v0v2)
    #     dot01 = np.dot(v0v2, v0v1)
    #     dot02 = np.dot(v0v2, v0p)
    #     dot11 = np.dot(v0v1, v0v1)
    #     dot12 = np.dot(v0v1, v0p)
    #
    #     # Compute barycentric coordinates
    #     denom = dot00 * dot11 - dot01 * dot01
    #     if denom == 0:
    #         print("Degenerate triangle")
    #         return False  # Degenerate triangle
    #
    #     u = (dot11 * dot02 - dot01 * dot12) / denom
    #     v = (dot00 * dot12 - dot01 * dot02) / denom
    #
    #     # Check if point is in triangle
    #     inside = (u >= 0) and (v >= 0) and (u + v <= 1)
    #     if inside:
    #         print("is in triangle")
    #     else:
    #         print("not in triangle")
    #     return inside
    #
    # def color_segm(self):
    #     # Retrieve the currently selected tomogram
    #     print("empty button")
    #     # artia = self.session.ArtiaX
    #     # tomo = artia.tomograms.get(artia.options_tomogram)
    #     # matrix = tomo.data.matrix()
    #     # print("Array Excerpt (first 5 elements):")
    #     # print(matrix.ravel()[:5])  # Flatten the array and print the first 5 elements
    #     #
    #     # print("\nBasic Information:")
    #     # print(f"Shape: {matrix.shape}")
    #     # print(f"Data type: {matrix.dtype}")
    #     # print(f"Size (number of elements): {matrix.size}")
    #     # print(f"Memory (bytes): {matrix.nbytes}")
    #     # print(f"Max value: {matrix.max()}")
    #     # print(f"Min value: {matrix.min()}")
    #     #
    #     # # Compute and print histogram (value distribution)
    #     # # print("\nExact Value Distribution:")
    #     # # unique, counts = np.unique(matrix, return_counts=True)
    #     # # for value, count in zip(unique, counts):
    #     # #     print(f"Value {value}: {count}")
    #     # print("\nValue Distribution (Histogram):")
    #     # hist, edges = np.histogram(matrix, bins=10)
    #     # for i in range(len(hist)):
    #     #     print(f"Range {edges[i]:.2f} - {edges[i + 1]:.2f}: {hist[i]}")
    #
    #     #vertex=tomo.surfaces[0].vertex_colors
    #     #print("First 5 entries:")
    #     #for i, (key, value) in enumerate(vertex.items()):
    #     #    print(f"{key}: {value}")
    #     #    if i == 4:  # Stop after the 5th entry
    #     #        break

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

            # Connect the item check state change to update the operation info
            #item.stateChanged.connect(self.update_operation_info)

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
        print(selected_tomograms)
        return selected_tomograms

    def _update_analysis(self):
        self.populate_tomogram_list()

    # Method to update the operation information
    def update_operation_info(self):
        # Get the names of the tomograms
        #name1 = self.tomo_math.name
        artia = self.session.ArtiaX
        tomo1 = artia.tomograms.get(artia.options_tomogram)
        name1=tomo1.name
        id_1=tomo1.id_string
        #name2 = self.selected_tomo_math.name
        #name2="selected tomogram"
        # Get the second selected tomogram name
        selected_tomograms = self.get_selected_tomograms()

        if selected_tomograms:
            name2=selected_tomograms[0]
        else:
            name2=""
        # If a tomogram is selected, fetch its name
        #name2 = selected_tomograms[0].name if selected_tomograms else "No tomogram selected"

        # Check the operation being performed
        operation_str = "None"
        if self.addition_checkbox.isChecked():
            operation_str = "+"
        elif self.subtraction_checkbox.isChecked():
            operation_str = "-"
        elif self.multiplication_checkbox.isChecked():
            operation_str = "*"

        if operation_str == "None":
            self.operation_info_label.setText(f"No operation selected")
        # Update the QLabel text to show the current operation
        self.operation_info_label.setText(
            f"#{id_1} - {name1} {operation_str} {name2}")


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

        self.group_manipulation.setLayout(self.manipulation_buttons_1)
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
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        pl.reset_all_particles()
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
