# vim: set expandtab shiftwidth=4 softtabstop=4:

from functools import partial

from chimerax.core.commands import run
from chimerax.core.errors import UserError
from chimerax.core.tools import ToolInstance
from chimerax.map import Volume, open_map
from chimerax.core.models import MODEL_DISPLAY_CHANGED


# from chimerax.atomic.molobject import Atom
import os as os
import math as ma
import numpy as np
from .Tomogram import Tomogram, orthoplane_cmd
from .widgets import LabelEditSlider

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QWheelEvent, QPaintEvent
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QComboBox,
    QDesktopWidget,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QScrollBar,
    QSlider,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QTableView,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QAbstractItemView,
    QRadioButton,
    QButtonGroup,
    QScrollArea,
    QSizePolicy
)

from superqt import QDoubleRangeSlider

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
    SESSION_SAVE = True         # We do save/restore in sessions
    help = "help:user/tools/tutorial.html"
                            # Let ChimeraX know about our help page

# ==============================================================================
# Instance Initialization ======================================================
# ==============================================================================

    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)

        self.display_name = "ArtiaX Options"

        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self)

        # Set the font
        self.font = QFont("Arial", 7)

        # We will be adding an item to the tool's context menu, so override
        # the default MainToolWindow fill context menu method
        self.tool_window.fill_context_menu = self.fill_context_menu

        # Build the user interfaces
        self._build_tomo_widget()
        self._build_particlelist_widget()
        # Build the final gui
        self._build_full_ui()
        self._connect_ui()
        # By default show the default window
        #self.change_gui("default")

        # Set the layout
        self.tool_window.ui_area.setLayout(self.main_layout)

        # Show the window on the right side of main window, dock everything else below for space
        self.tool_window.manage("right")

        from chimerax.log.tool import Log
        from chimerax.model_panel.tool import ModelPanel
        from chimerax.map.volume_viewer import VolumeViewer

        # Make sure volume viewer is there
        run(self.session, 'ui tool show "Volume Viewer"', log=False)

        if len(self.session.tools.find_by_class(Log)) > 0:
            log_window = self.session.tools.find_by_class(Log)[0].tool_window
            log_window.manage(self.tool_window)

        if len(self.session.tools.find_by_class(ModelPanel)) > 0:
            model_panel = self.session.tools.find_by_class(ModelPanel)[0].tool_window
            model_panel.manage(self.tool_window)

        if len(self.session.tools.find_by_class(VolumeViewer)) > 0:
            vol_viewer = self.session.tools.find_by_class(VolumeViewer)[0].tool_window
            vol_viewer.manage(self.tool_window)


# ==============================================================================
# Show selected GUI ============================================================
# ==============================================================================

    def _build_full_ui(self):
        # Define a stacked layout and only show the selected layout
        self.main_layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # Add the Tabs
        self.tabs.addTab(self.tomo_widget, 'Tomogram Tools')
        self.tabs.addTab(self.motl_widget, 'Particle List Tools')
        self.tabs.widget(0).setEnabled(False)
        self.tabs.widget(1).setEnabled(False)
        self.tabs.setCurrentIndex(0)
        self.main_layout.addWidget(self.tabs)

        # Volume open dialog
        caption = 'Choose a volume.'
        self.volume_open_dialog = QFileDialog(caption=caption)
        self.volume_open_dialog.setFileMode(QFileDialog.ExistingFiles)
        self.volume_open_dialog.setNameFilters(["Volume (*.em *.mrc *.mrcs *.rec *.map *.hdf)"])
        self.volume_open_dialog.setAcceptMode(QFileDialog.AcceptOpen)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _show_tab(self, type):
        artia = self.session.ArtiaX

        if type == "tomogram":
            ct = artia.tomograms.get(artia.options_tomogram)
            self.current_tomo_label.setText(ct.name)
            self.tabs.setCurrentIndex(0)
            self.tabs.widget(0).setEnabled(True)

            # Update the ui
            self._update_tomo_ui()

            from .VolumePlus import RENDERING_OPTIONS_CHANGED
            ct.triggers.add_handler(RENDERING_OPTIONS_CHANGED, self._models_changed)

            # Make sure we are on top
            run(self.session, 'ui tool show "ArtiaX Options"', log=False)

        elif type == "partlist":
            cpl = artia.partlists.get(artia.options_partlist)
            #self.current_tomo_label.setText(artia.partlists.get(artia.options_partlist).name)
            self.tabs.setCurrentIndex(1)
            self.tabs.widget(1).setEnabled(True)

            # Update the ui
            self._update_partlist_ui()

            from .ParticleList import PARTLIST_CHANGED
            cpl.triggers.add_handler(PARTLIST_CHANGED, self._partlist_changed)

            # Make sure we are on top
            run(self.session, 'ui tool show "ArtiaX Options"', log=False)

# ==============================================================================
# Options Menu for Tomograms ===================================================
# ==============================================================================

    def _build_tomo_widget(self):
        # This window is a widget of the stacked layout
        self.tomo_widget = QScrollArea()
        # Define the overall layout
        tomo_layout = QVBoxLayout()

        # Display current tomogram name
        group_current_tomo = QGroupBox("Current Tomogram")
        group_current_tomo.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
                                                          QSizePolicy.Minimum))
        group_current_tomo.setFont(self.font)
        current_tomo_layout = QHBoxLayout()
        self.current_tomo_label = QLabel("")
        print(self.current_tomo_label.sizeHint())
        self.current_tomo_label.setSizePolicy(QSizePolicy(QSizePolicy.Minimum,
                                                          QSizePolicy.Minimum))
        current_tomo_layout.addWidget(self.current_tomo_label)
        group_current_tomo.setLayout(current_tomo_layout)

        # Set the layout of the Pixel Size LineEdit
        group_pixelsize = QGroupBox("Physical Position")
        group_pixelsize.setFont(self.font)
        group_pixelsize_layout = QGridLayout()

        group_pixelsize_label = QLabel("Pixel Size:")
        group_pixelsize_label.setFont(self.font)
        self.group_pixelsize_edit = QLineEdit("")
        self.group_pixelsize_button_apply = QPushButton("Apply")
        self.group_pixelsize_button_physpos = QPushButton("Position (xyz):")
        # self.group_pixel_size_labelx = QLabel("")
        # self.group_pixel_size_labelx.setFont(self.font)
        # self.group_pixel_size_labely = QLabel("")
        # self.group_pixel_size_labely.setFont(self.font)
        # self.group_pixel_size_labelz = QLabel("")
        # self.group_pixel_size_labelz.setFont(self.font)

        self.group_pixelsize_labelx = QLabel("")
        self.group_pixelsize_labelx.setFont(self.font)
        self.group_pixelsize_labely = QLabel("")
        self.group_pixelsize_labely.setFont(self.font)
        self.group_pixelsize_labelz = QLabel("")
        self.group_pixelsize_labelz.setFont(self.font)

        group_pixelsize_layout.addWidget(group_pixelsize_label, 0, 0, 1, 1)
        group_pixelsize_layout.addWidget(self.group_pixelsize_edit, 0, 1, 1, 1)
        group_pixelsize_layout.addWidget(self.group_pixelsize_button_apply, 0, 2, 1, 1)
        group_pixelsize_layout.addWidget(self.group_pixelsize_button_physpos, 1, 0, 1, 1)
        group_pixelsize_layout.addWidget(self.group_pixelsize_labelx, 1, 1, 1, 1)
        group_pixelsize_layout.addWidget(self.group_pixelsize_labely, 1, 2, 1, 1)
        group_pixelsize_layout.addWidget(self.group_pixelsize_labelz, 1, 3, 1, 1)
        # Add grid to group
        group_pixelsize.setLayout(group_pixelsize_layout)

        # Define a group for the contrast sliders
        group_contrast = QGroupBox("Contrast Settings")
        group_contrast.setFont(self.font)
        group_contrast_layout = QGridLayout()

        # Define two sliders that control the contrast
        # Center Sliders
        group_contrast_center_label = QLabel("Center:")
        group_contrast_center_label.setFont(self.font)
        self.group_contrast_center_edit = QLineEdit("")
        self.group_contrast_center_edit.setFont(self.font)
        self.group_contrast_center_slider = QSlider(Qt.Horizontal)

        # Width Slider
        group_contrast_width_label = QLabel("Width:")
        group_contrast_width_label.setFont(self.font)
        self.group_contrast_width_edit = QLineEdit("")
        self.group_contrast_width_edit.setFont(self.font)
        self.group_contrast_width_slider = QSlider(Qt.Horizontal)
        # Add to the grid layout
        group_contrast_layout.addWidget(group_contrast_center_label, 0, 0)
        group_contrast_layout.addWidget(self.group_contrast_center_edit, 0, 1)
        group_contrast_layout.addWidget(self.group_contrast_center_slider, 0, 2)
        group_contrast_layout.addWidget(group_contrast_width_label, 1, 0)
        group_contrast_layout.addWidget(self.group_contrast_width_edit, 1, 1)
        group_contrast_layout.addWidget(self.group_contrast_width_slider, 1, 2)
        # Add grid to group
        group_contrast.setLayout(group_contrast_layout)

        # Define a group for different orthoplanes of a tomogram
        group_orthoplanes = QGroupBox("Orthoplanes")
        group_orthoplanes.setFont(self.font)
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
        group_orthoplanes_layout.addWidget(self.group_orthoplanes_buttonxyz, 0, 3)
        # Add grid to group
        group_orthoplanes.setLayout(group_orthoplanes_layout)

        # Define a group for the fourier transform of a volume
        group_fourier_transform = QGroupBox("Fourier transformation")
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

        # Define a group that jumps through the slices
        group_slices = QGroupBox("Jump Through Slices")
        group_slices.setFont(self.font)
        # Set the layout for the group
        group_slices_layout = QGridLayout()
        # Define a Slider and four jump buttons
        group_slices_label = QLabel("Slice:")
        group_slices_label.setFont(self.font)

        group_slices_first_row = QHBoxLayout()
        self.group_slices_edit = QLineEdit("")
        self.group_slices_edit.setFont(self.font)
        self.group_slices_slider = QSlider(Qt.Horizontal)
        group_slices_first_row.addWidget(self.group_slices_edit)
        group_slices_first_row.addWidget(self.group_slices_slider)

        group_slices_second_row = QHBoxLayout()
        self.group_slices_previous_10 = QPushButton("<<")
        self.group_slices_previous_10.setFont(self.font)
        self.group_slices_previous_1 = QPushButton("<")
        self.group_slices_previous_1.setFont(self.font)
        self.group_slices_next_1 = QPushButton(">")
        self.group_slices_next_1.setFont(self.font)
        self.group_slices_next_10 = QPushButton(">>")
        self.group_slices_next_10.setFont(self.font)
        group_slices_second_row.addWidget(self.group_slices_previous_10)
        group_slices_second_row.addWidget(self.group_slices_previous_1)
        group_slices_second_row.addWidget(self.group_slices_next_1)
        group_slices_second_row.addWidget(self.group_slices_next_10)
        # Add to the grid layout
        group_slices_layout.addWidget(group_slices_label, 0, 0)
        group_slices_layout.addLayout(group_slices_first_row, 0, 1)
        group_slices_layout.addLayout(group_slices_second_row, 1, 1)
        # Add grid to group
        group_slices.setLayout(group_slices_layout)

        # Add groups to layout
        tomo_layout.addWidget(group_current_tomo)
        tomo_layout.addWidget(group_pixelsize)
        tomo_layout.addWidget(group_contrast)
        tomo_layout.addWidget(group_slices)
        tomo_layout.addWidget(group_orthoplanes)
        tomo_layout.addWidget(group_fourier_transform)

        # And finally set the layout of the widget
        self.tomo_widget.setLayout(tomo_layout)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Tomo Window Functions ++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _connect_ui(self):
        ow = self
        artia = self.session.ArtiaX

        ### Options window
        ## Tomo Tab
        # Pixel size
        ow.group_pixelsize_button_apply.clicked.connect(partial(ow._set_tomo_pixelsize))

        # Center
        ow.group_contrast_center_edit.editingFinished.connect(partial(ow._contrast_center_edited))
        ow.group_contrast_center_slider.valueChanged.connect(partial(ow._contrast_center_slider))

        # Width
        ow.group_contrast_width_edit.editingFinished.connect(partial(ow._contrast_width_edited))
        ow.group_contrast_width_slider.valueChanged.connect(partial(ow._contrast_width_slider))

        # Slice
        ow.group_slices_edit.editingFinished.connect(partial(ow._slice_edited))
        ow.group_slices_slider.valueChanged.connect(partial(ow._slice_slider))

        # Slices buttons
        ow.group_slices_previous_10.clicked.connect(partial(ow._skip_planes, -10))
        ow.group_slices_previous_1.clicked.connect(partial(ow._skip_planes, -1))
        ow.group_slices_next_1.clicked.connect(partial(ow._skip_planes, 1))
        ow.group_slices_next_10.clicked.connect(partial(ow._skip_planes, 10))

        # Orthoplanes
        ow.group_orthoplanes_buttonxy.clicked.connect(partial(ow._set_xy_orthoplanes))
        ow.group_orthoplanes_buttonxz.clicked.connect(partial(ow._set_xz_orthoplanes))
        ow.group_orthoplanes_buttonyz.clicked.connect(partial(ow._set_yz_orthoplanes))
        ow.group_orthoplanes_buttonxyz.clicked.connect(partial(ow.orthoplanes_buttonxyz_execute))

        # Fourier transform
        ow.group_fourier_transform_execute_button.clicked.connect(partial(ow._fourier_transform))

        ## Partlist Tab
        # Connect selector
        ow.partlist_selection.displayChanged.connect(artia.show_particles)
        ow.partlist_selection.selectionChanged.connect(artia.select_particles)

        # Connect colors
        ow.color_selection.colorChanged.connect(artia.color_particles)
        ow.color_selection.colormapChanged.connect(artia.color_particles_byattribute)

        # Connect sliders
        ow.radius_widget.valueChanged.connect(ow._radius_changed)
        ow.axes_size_widget.valueChanged.connect(ow._axes_size_changed)
        ow.surface_level_widget.valueChanged.connect(ow._surface_level_changed)

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

    def _update_tomo_ui(self):
        self._update_tomo_sliders()
        self._update_pixelsize_edit()

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

        self.group_contrast_center_slider.setMinimum(0)
        self.group_contrast_center_slider.setMaximum(10000)
        self.group_contrast_center_slider.setSingleStep(1)

        self.group_contrast_center_slider.setValue(value_to_slider(tomo.contrast_center, 10000, tomo.min, tomo.max))
        self.group_contrast_center_edit.setText(str(tomo.contrast_center))

        # Width goes from negative distance between minimum and maximum to positive distance
        self.group_contrast_width_slider.setMinimum(0)
        self.group_contrast_width_slider.setMaximum(10000)
        self.group_contrast_width_slider.setSingleStep(1)

        self.group_contrast_width_slider.setValue(value_to_slider(tomo.contrast_width, 10000, 0, tomo.range))
        self.group_contrast_width_edit.setText(str(tomo.contrast_width))

        self.group_slices_slider.setMinimum(0)
        self.group_slices_slider.setMaximum(tomo.slab_count-1)
        self.group_contrast_width_slider.setSingleStep(1)

        self.group_slices_slider.setValue(tomo.integer_slab_position)
        self.group_slices_edit.setText(str(tomo.integer_slab_position))

    def _update_pixelsize_edit(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        self.group_pixelsize_edit.setText(str(tomo.pixelsize[0]))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _set_tomo_pixelsize(self):
        ow = self
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        pixel_size = float(self.group_pixelsize_edit.text())

        if pixel_size <= 0:
            raise UserError("{} is not a valid pixel size".format(pixel_size))

        tomo.pixelsize = pixel_size

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _contrast_center_edited(self):
        try:
            artia = self.session.ArtiaX
            tomo = artia.tomograms.get(artia.options_tomogram)
            # Get text from edit
            value = float(self.group_contrast_center_edit.text())
            # Set value in slider
            self.group_contrast_center_slider.setValue(value_to_slider(value, 10000, tomo.min, tomo.max))
            # Execute the center function
            tomo.contrast_center = value
        except:
            print("Error: Please insert a number.")

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _contrast_center_slider(self, session):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        # Get the value from the slider
        value = slider_to_value(self.group_contrast_center_slider.value(), 10000, tomo.min, tomo.max)
        # Set value in edit
        self.group_contrast_center_edit.setText(str(value))
        # Execute the center function
        tomo.contrast_center = value

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _contrast_width_edited(self):
        try:
            artia = self.session.ArtiaX
            tomo = artia.tomograms.get(artia.options_tomogram)

            # Get text from edit
            value = float(self.group_contrast_width_edit.text())
            # Set value in slider
            self.group_contrast_width_slider.setValue(value_to_slider(value, 10000, 0, tomo.range))
            # Execute the width function
            tomo.contrast_width = value
        except:
            print("Error: Please insert a number")

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _contrast_width_slider(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        # Get the value from the slider
        value = slider_to_value(self.group_contrast_width_slider.value(), 10000, 0, tomo.range)
        # Set value in edit
        self.group_contrast_width_edit.setText(str(value))
        # Execute the width function
        tomo.contrast_width = value

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _slice_edited(self):
        try:
            artia = self.session.ArtiaX
            tomo = artia.tomograms.get(artia.options_tomogram)

            # Get text from edit
            value = float(self.group_slices_edit.text())
            # Set value in slider
            self.group_slices_slider.setValue(int(value))
            # Execute the slice function
            tomo.integer_slab_position = value
        except:
            print("Error: Please insert a number.")

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _slice_slider(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        # Get the value from the slider
        value = self.group_slices_slider.value()
        # Set value in edit
        self.group_slices_edit.setText(str(value))
        # Execute the slice function
        tomo.integer_slab_position = value

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _skip_planes(self, number):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        tomo_slice = tomo.integer_slab_position + number
        tomo_slice = max(0, tomo_slice)
        tomo_slice = min(tomo.slab_count, tomo_slice)
        tomo.integer_slab_position = tomo_slice
        self._update_tomo_sliders()

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _set_xy_orthoplanes(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        cmd = orthoplane_cmd(tomo, 'xy')
        run(self.session, cmd)
        run(self.session, 'artiax view xy')
        run(self.session, 'mousemode rightMode "move planes"')
        self._update_tomo_sliders()

    def _set_xz_orthoplanes(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        cmd = orthoplane_cmd(tomo, 'xz')
        run(self.session, cmd)
        run(self.session, 'artiax view xz')
        run(self.session, 'mousemode rightMode "move planes"')
        self._update_tomo_sliders()

    def _set_yz_orthoplanes(self):
        artia = self.session.ArtiaX
        tomo = artia.tomograms.get(artia.options_tomogram)

        cmd = orthoplane_cmd(tomo, 'yz')
        run(self.session, cmd)
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

# ==============================================================================
# Options Menu for Motivelists =================================================
# ==============================================================================


    def _build_particlelist_widget(self):
        # This widget is the particle lists tab
        self.motl_widget = QScrollArea()

        # Define the overall layout
        self.motl_layout = QVBoxLayout()

        # Define a group for the visualization sliders
        self.group_select = QGroupBox("Visualization Options:")
        self.group_select.setFont(self.font)
        self.group_select.setCheckable(True)

        # Set the layout of the group
        self.group_select_layout = QGridLayout()
        # Define the input of the GridLayout which includes some sliders and LineEdits
        self.partlist_selection = SelectionTableWidget()
        self.color_selection = ColorRangeWidget(self.session)
        self.radius_widget = LabelEditSlider((0.1, 200), 'Marker Radius')
        self.surface_level_widget = LabelEditSlider((0, 1), 'Surface Level')
        self.axes_size_widget = LabelEditSlider((0.1, 200), 'Axes Size')

        self.group_select_layout.addWidget(self.partlist_selection, 0, 0, 6, 6)
        self.group_select_layout.addWidget(self.color_selection, 6, 0, 3, 6)
        self.group_select_layout.addWidget(self.radius_widget, 9, 0, 1, 6)
        self.group_select_layout.addWidget(self.axes_size_widget, 10, 0, 1, 6)
        self.group_select_layout.addWidget(self.surface_level_widget, 11, 0, 1, 6)

        # Set layout of group
        self.group_select.setLayout(self.group_select_layout)

        # Define a group for the maniulation buttons
        self.group_manipulation = QGroupBox("Manipulation Options:")
        self.group_manipulation.setFont(self.font)
        self.group_manipulation.setCheckable(True)
        self.group_manipulation.setChecked(False)

        # Define layout of the group
        self.group_manipulation_layout = QVBoxLayout()
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

        # Add another row of buttons
        self.group_manipulation_buttons_2 = QHBoxLayout()
        self.group_manipulation_delete_button = QPushButton("Delete selected")
        self.group_manipulation_delete_button.setFont(self.font)
        self.group_manipulation_reset_selected_button = QPushButton("Reset selected")
        self.group_manipulation_reset_selected_button.setFont(self.font)
        self.group_manipulation_reset_all_button = QPushButton("Reset all")
        self.group_manipulation_reset_all_button.setFont(self.font)
        self.group_manipulation_buttons_2.addWidget(self.group_manipulation_delete_button)
        self.group_manipulation_buttons_2.addWidget(self.group_manipulation_reset_selected_button)
        self.group_manipulation_buttons_2.addWidget(self.group_manipulation_reset_all_button)

        # Add a browse row
        self.browse_layout = QHBoxLayout()
        self.browse_label = QLabel("Filepath of object:")
        self.browse_label.setFont(self.font)
        self.browse_edit = QLineEdit("")
        self.browse_edit.setFont(self.font)
        self.browse_button = QPushButton("Browse")
        self.browse_layout.addWidget(self.browse_label)
        self.browse_layout.addWidget(self.browse_edit)
        self.browse_layout.addWidget(self.browse_button)

        # Add to the grid layout
        self.group_manipulation_layout.addLayout(self.pixel_factor_layout)
        self.group_manipulation_layout.addLayout(self.group_manipulation_buttons_2)
        self.group_manipulation_layout.addLayout(self.browse_layout)

        # Set layout of group
        self.group_manipulation.setLayout(self.group_manipulation_layout)

        # Add groups to layout
        self.motl_layout.addWidget(self.group_manipulation)
        self.motl_layout.addWidget(self.group_select)

        # And finally set the layout of the widget
        self.motl_widget.setLayout(self.motl_layout)

    def _update_partlist_ui(self):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)

        # Set new list
        self.partlist_selection.clear(trigger_update=False)
        self.partlist_selection.set_partlist(pl)
        self.color_selection.set_partlist(pl)

        # Set sliders
        self.radius_widget.value = pl.radius
        self.axes_size_widget.value = pl.axes_size

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
    #

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _radius_changed(self, value):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        pl.radius = value

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _surface_level_changed(self, value):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        pl.surface_level = value

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _axes_size_changed(self, value):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)
        pl.axes_size = value

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _origin_pixelsize_changed(self):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)

        if not is_float(self.pf_edit_ori.text()):
            self.pf_edit_ori.setText(str(pl.origin_pixelsize))
            raise UserError('Please enter a valid number for the pixelsize.')

        value = float(self.pf_edit_ori.text())
        pl.origin_pixelsize = value

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _trans_pixelsize_changed(self):
        artia = self.session.ArtiaX
        pl = artia.partlists.get(artia.options_partlist)

        if not is_float(self.pf_edit_tra.text()):
            self.pf_edit_tra.setText(str(pl.translation_pixelsize))
            raise UserError('Please enter a valid number for the pixelsize.')

        value = float(self.pf_edit_tra.text())
        pl.translation_pixelsize = value

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

        vol = open_map(self.session, file)[0][0]
        self.session.models.add([vol])
        pl.attach_display_model(vol)
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


# ==============================================================================
# Context Menu =================================================================
# ==============================================================================

    def fill_context_menu(self, menu, x, y):
        # Add any tool-specific items to the given context menu (a QMenu
        # instance). The menu will then be automatically filled out with generic
        # tool-related actions (e.g. Hide Tool, Help, Dockable Tool, etc.)

        # The x, y args are the x() and y() values of QContextMenuEvent, in the
        # rare case where the items put in the menu depends on where in the
        # tool interface the menu was raised
        from Qt.QtWidgets import QAction
        clear_action = QAction("Clear",menu)
        clear_action.triggered.connect(lambda *args: self.line_edit.clear())
        menu.addAction(clear_action)

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


class SelectionTableWidget(QWidget):
    """
    A SelectionTableWidget allows selecting from or hiding parts of a ParticleList based on a combination attribute ranges.

    """
    DEBUG = True

    selectionChanged = pyqtSignal(tuple, list, list, list)
    displayChanged = pyqtSignal(tuple, list, list, list)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.partlist = None
        self.attributes = None
        self.minima = None
        self.maxima = None

        self._mode = "show"
        self._selectors = []

        # General layout
        self._layout = QVBoxLayout()

        # Radio buttons controlling task
        self._mode_layout = QHBoxLayout()
        self.sel_mode_switch = QRadioButton("Select")
        self.dis_mode_switch = QRadioButton("Show")
        self.mode_group = QButtonGroup()
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.sel_mode_switch)
        self.mode_group.addButton(self.dis_mode_switch)
        self.dis_mode_switch.setChecked(True)

        self._mode_layout.addWidget(self.sel_mode_switch, alignment=Qt.AlignCenter)
        self._mode_layout.addWidget(self.dis_mode_switch, alignment=Qt.AlignCenter)

        # Scroll area containing Selector widgets
        self.selector_area = QScrollArea()
        self.selectors = QWidget()
        self.selectors_vbox = QVBoxLayout()
        self.selectors.setLayout(self.selectors_vbox)

        self.selector_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.selector_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.selector_area.setWidgetResizable(True)
        self.selector_area.setWidget(self.selectors)

        # Clear button
        self._util_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Selector")
        self.clear_button = QPushButton("Clear All Selectors")
        self._util_layout.addWidget(self.add_button)
        self._util_layout.addWidget(self.clear_button)

        # Assemble
        self._layout.addLayout(self._mode_layout)
        self._layout.addWidget(self.selector_area)
        self._layout.addLayout(self._util_layout)
        self.setLayout(self._layout)

        # Connect functions
        self._connect()

    def set_partlist(self, partlist):
        """
        Set associated ParticleList instance, read available attributes and determine ranges for attributes. If
        ParticleList has attribute 'selection_settings' from a previous selection, then recreates the SelectorWidgets
        using the old settings.

        Parameters
        ----------
        partlist : ParticleList
            ParticleList instance to read from and select on.
        """
        self.partlist = partlist
        self.attributes = partlist.get_main_attributes()
        self.minima = partlist.get_attribute_min(self.attributes)
        self.maxima = partlist.get_attribute_max(self.attributes)
        self.attribute_constant = [False]*len(self.attributes)

        for idx, mini in enumerate(self.minima):
            if mini == self.maxima[idx]:
                self.attribute_constant[idx] = True

        if hasattr(self.partlist, 'selection_settings'):
            sel_mode = self.partlist.selection_settings['mode']
            sel_names = self.partlist.selection_settings['names']
            sel_minima = self.partlist.selection_settings['minima']
            sel_maxima = self.partlist.selection_settings['maxima']

            # Set mode
            prev = self.sel_mode_switch.blockSignals(True)
            prev1 = self.dis_mode_switch.blockSignals(True)
            if sel_mode == 'select':
                self.sel_mode_switch.setChecked(True)
            elif sel_mode == 'show':
                self.dis_mode_switch.setChecked(True)
            self.sel_mode_switch.blockSignals(prev)
            self.dis_mode_switch.blockSignals(prev1)

            # Create old selectors
            for name, mini, maxi in zip(sel_names, sel_minima, sel_maxima):
                idx = self.attributes.index(name)

                # Old selection could be out of date with respect to range (e.g. if particles were deleted/created)
                if mini < self.minima[idx]:
                    mini = self.minima[idx]

                if maxi > self.maxima[idx]:
                    maxi = self.maxima[idx]

                # New selector with previous range
                self._new_selector(idx, mini, maxi)

            # Trigger update
            self._selector_modified()

    def clear(self, trigger_update=True):
        """
        Remove all SelectorWidget instances (i.e. clear applied selection).

        Parameters
        ----------
        trigger_update : bool
            If True, update the selection after deleting.
        """
        for widget in self._selectors:
            self.selectors_vbox.removeWidget(widget)
            widget.deleteLater()

        self._selectors = []

        # Could be that no partlist was assigned yet
        if self.partlist is not None and trigger_update:
            self._selector_modified()

    @property
    def selector_count(self):
        """
        Return the number of SelectorWidgets currently owned by this instance.
        """
        return len(self._selectors)

    def _connect(self):
        """
        Connect the UI to respective callbacks.
        """
        # Radio buttons
        self.sel_mode_switch.clicked.connect(self._mode_switched)
        self.dis_mode_switch.clicked.connect(self._mode_switched)

        # Util buttons
        self.add_button.clicked.connect(partial(self._add_selector))
        self.clear_button.clicked.connect(partial(self.clear))

    def _add_selector(self):
        """
        Action upon clicking "Add Selector" button.
        """
        self._new_selector()
        self._selector_modified()

    def _new_selector(self, idx=0, mini=None, maxi=None):
        """
        Create a new SelectorWidget and add it to this instances _selectors-list.

        Parameters
        ----------
        idx : int
            Index of the attribute to pre-select in the new SelectorWidget upon creation.
        mini : float
            Value to pre-set as lower slider position on the newly created SelectorWidget
        maxi : float
            Value to pre-set as upper slider position on the newly created SelectorWidget
        """
        widget = SelectorWidget(self.attributes,
                                self.minima,
                                self.maxima,
                                self.attribute_constant,
                                idx=idx,
                                mini=mini,
                                maxi=maxi)

        self._selectors.append(widget)
        self.selectors_vbox.addWidget(widget)
        widget.selectionChanged.connect(self._selector_modified)
        widget.deleted.connect(self._selector_deleted)

    def _mode_switched(self):
        """
        Action upon switching between 'Show' and 'Select' radio buttons
        """
        # Reset the selection
        if self.selector_count > 0:
            self._selector_modified(get_selection=False)

        # Switch
        if self.sel_mode_switch.isChecked():
            self._mode = "select"
        elif self.dis_mode_switch.isChecked():
            self._mode = "show"

        # Apply the selection
        if self.selector_count > 0:
            self._selector_modified()

    def _selector_modified(self, get_selection=True):
        """
        Collect selection information from owned SelectorWidgets and emit appropriate signal depending on mode.

        Parameters
        ----------
        get_selection : bool
            If True, query the current values from the owned SelectorWidgets and emit them in the signal. If False, emit
            empty lists. The latter is useful for resetting the selection.
        """
        sel_names = []
        sel_minima = []
        sel_maxima = []

        if get_selection:
            if self.DEBUG:
                print(self._selectors)

            for selector in self._selectors:
                if self.DEBUG:
                    print(selector.active)
                if selector.active:
                    sel_name, sel_minimum, sel_maximum = selector.get_selection()
                    sel_names.append(sel_name)
                    sel_minima.append(sel_minimum)
                    sel_maxima.append(sel_maximum)

            if self.DEBUG:
                print("names: {} minima: {} maxima: {}".format(sel_names, sel_minima, sel_maxima))

            self.partlist.selection_settings = {'mode': self._mode,
                                                'names': sel_names,
                                                'minima': sel_minima,
                                                'maxima': sel_maxima}

        if self._mode == "select":
            self.selectionChanged.emit(self.partlist.id, sel_names, sel_minima, sel_maxima)
        elif self._mode == "show":
            self.displayChanged.emit(self.partlist.id, sel_names, sel_minima, sel_maxima)

    def _selector_deleted(self, selector):
        """
        Action upon deletion of a selector (usually triggered by SelectorWidget.deleted signal)

        Parameters
        ----------
        selector : SelectorWidget
            The Widget to remove.
        """
        self._selectors.remove(selector)
        self._selector_modified()


class SelectorWidget(QWidget):
    DEBUG = False

    selectionChanged = pyqtSignal()
    deleted = pyqtSignal(object)

    def __init__(self, attributes, minima, maxima, constant, idx=0, mini=None, maxi=None, parent=None):
        super().__init__(parent=parent)

        self.attributes = attributes
        self.minima = minima
        self.maxima = maxima
        self.attribute_constant = constant
        self._idx = idx
        self.active = True

        # The contents
        self._layout = QGridLayout()

        # Enable/Disable toggle
        self.toggle_switch = QCheckBox()
        self.toggle_switch.setCheckState(Qt.Checked)

        # Attributes
        self.attribute_box = IgnorantComboBox()
        self.attribute_box.setFocusPolicy(Qt.StrongFocus)
        for a in self.attributes:
            self.attribute_box.addItem(a)

        self.attribute_box.setCurrentIndex(self._idx)

        # Slider with edits and labels
        self._slider_layout = QVBoxLayout()

        # Slider values possibly preset
        if mini is not None:
            value_low = mini
        else:
            value_low = self.minimum

        if maxi is not None:
            value_high = maxi
        else:
            value_high = self.maximum

        # Slider Line 1
        self._slider_min_max_layout = QHBoxLayout()
        self.min_label = QLabel("{:.4f}".format(self.minimum))
        self.max_label = QLabel("{:.4f}".format(self.maximum))
        self._slider_min_max_layout.addWidget(self.min_label, alignment=Qt.AlignLeft)
        self._slider_min_max_layout.addWidget(self.max_label, alignment=Qt.AlignRight)

        # Slider Line 2
        self.slider = QDoubleRangeSlider()
        self.slider._singleStep = 0.001
        self.slider._pageStep = 0.01
        self.slider.setOrientation(Qt.Horizontal)

        # If current attribute is constant, disable slider
        if self.constant:
            self.slider.setMinimum(self.minimum)
            self.slider.setMaximum(self.maximum+1)
            self.slider.setValue((value_low, value_high+1))
            self.slider.setEnabled(False)
        else:
            self.slider.setMinimum(self.minimum)
            self.slider.setMaximum(self.maximum)
            self.slider.setValue((value_low, value_high))

        # Slider Line 3
        self._slider_edit_layout = QHBoxLayout()
        self.lower_edit = QLineEdit("{:.4f}".format(value_low))
        self.upper_edit = QLineEdit("{:.4f}".format(value_high))
        self._slider_edit_layout.addWidget(self.lower_edit, alignment=Qt.AlignCenter)
        self._slider_edit_layout.addWidget(self.upper_edit, alignment=Qt.AlignCenter)

        # If current attribute is constant, disable edits
        if self.constant:
            self.lower_edit.setEnabled(False)
            self.upper_edit.setEnabled(False)

        self._slider_layout.addLayout(self._slider_min_max_layout)
        self._slider_layout.addWidget(self.slider)
        self._slider_layout.addLayout(self._slider_edit_layout)

        # Destroy self button
        self.destroy_button = QPushButton()

        self._layout.addWidget(self.toggle_switch, 0, 0, 1, 1)
        self._layout.addWidget(self.attribute_box, 0, 1, 1, 5)
        self._layout.addLayout(self._slider_layout, 0, 6, 1, 13)
        self._layout.addWidget(self.destroy_button, 0, 19, 1, 1)

        self._connect()

        self.setLayout(self._layout)

        self._to_enable = [self.attribute_box,
                           self.slider,
                           self.lower_edit,
                           self.upper_edit]

    def _connect(self):
        # Turned on or off
        self.toggle_switch.stateChanged.connect(partial(self._toggled))

        # Destroy requested
        self.destroy_button.clicked.connect(partial(self._destroy))

        # Combo box
        self.attribute_box.currentIndexChanged.connect(partial(self._set_idx))

        # Slider
        self.slider.valueChanged.connect(partial(self._slider_changed))

        # Edits
        self.lower_edit.returnPressed.connect(partial(self._edit_changed))
        self.upper_edit.returnPressed.connect(partial(self._edit_changed))

    @property
    def minimum(self):
        return self.minima[self._idx]

    @property
    def maximum(self):
        return self.maxima[self._idx]

    @property
    def constant(self):
        return self.attribute_constant[self._idx]

    def get_selection(self):
        name = self.attribute_box.currentText()
        if self.DEBUG:
            print("Slider Value: {}".format(self.slider.value()))

        # If attribute is constant, ignore the slider.
        if self.constant:
            minimum = self.minimum
            maximum = self.maximum
        else:
            minimum = self.slider.value()[0]
            maximum = self.slider.value()[1]

        return name, minimum, maximum

    def _toggled(self, state):
        if state == Qt.Checked:
            self.active = True
        elif state == Qt.Unchecked:
            self.active = False

        self._enable_widgets()
        self._emit_selection_changed()

    def _set_idx(self, idx):
        self._idx = idx
        self._enable_widgets()
        self._set_min_max()
        self._emit_selection_changed()

    def _enable_widgets(self):
        if self.active:
            for w in self._to_enable:
                w.setEnabled(True)
            if self.constant:
                self.slider.setEnabled(False)
                self.upper_edit.setEnabled(False)
                self.lower_edit.setEnabled(False)
        else:
            for w in self._to_enable:
                w.setEnabled(False)

    def _set_min_max(self):

        prev = self.slider.blockSignals(True)
        if self.constant:
            self.slider.setMinimum(self.minimum)
            self.slider.setMaximum(self.maximum+1)
            self.slider.setValue((self.minimum, self.maximum+1))
        else:
            self.slider.setMinimum(self.minimum)
            self.slider.setMaximum(self.maximum)
            self.slider.setValue((self.minimum, self.maximum))
        self.slider.blockSignals(prev)

        self.min_label.setText("{:.4f}".format(self.minimum))
        self.max_label.setText("{:.4f}".format(self.maximum))

        prev = self.lower_edit.blockSignals(True)
        prev1 = self.upper_edit.blockSignals(True)
        self.lower_edit.setText("{:.4f}".format(self.minimum))
        self.upper_edit.setText("{:.4f}".format(self.maximum))
        self.lower_edit.blockSignals(prev)
        self.upper_edit.blockSignals(prev1)


    def _destroy(self):
        self.deleted.emit(self)
        self.deleteLater()

    def _slider_changed(self, value):
        prev = self.lower_edit.blockSignals(True)
        prev1 = self.upper_edit.blockSignals(True)
        self.lower_edit.setText("{:.4f}".format(value[0]))
        self.upper_edit.setText("{:.4f}".format(value[1]))
        self.lower_edit.blockSignals(prev)
        self.upper_edit.blockSignals(prev1)

        self._emit_selection_changed()

    def _edit_changed(self):
        lower = float(self.lower_edit.text())
        upper = float(self.upper_edit.text())

        if lower < self.minimum:
            prev = self.lower_edit.blockSignals(True)
            self.lower_edit.setText("{:.4f}".format(self.minimum))
            self.lower_edit.blockSignals(prev)
            lower = self.minimum

        if upper > self.maximum:
            prev = self.upper_edit.blockSignals(True)
            self.upper_edit.setText("{:.4f}".format(self.maximum))
            self.upper_edit.blockSignals(prev)
            upper = self.maximum

        prev = self.slider.blockSignals(True)
        self.slider.setValue((lower, upper))
        self.slider.blockSignals(prev)
        self._emit_selection_changed()

    def _emit_selection_changed(self):
        self.selectionChanged.emit()

class ColorRangeWidget(QWidget):

    # from P. Green-Armytage (2010): A Colour Alphabet and the Limits of Colour Coding. // Colour: Design & Creativity (5) (2010): 10, 1-23
    # https://eleanormaclure.files.wordpress.com/2011/03/colour-coding.pdf
    # skipped ebony, yellow
    green_armytage = [[(240, 163, 255, 255), (  0, 117, 220, 255), (153,  63,   0, 255)],
                      [( 76,   0,  92, 255), (  0,  92,  49, 255), ( 43, 206,  72, 255)],
                      [(255, 204, 153, 255), (128, 128, 128, 255), (148, 255, 181, 255)],
                      [(143, 124,   0, 255), (157, 204,   0, 255), (194,   0, 136, 255)],
                      [(  0,  51, 128, 255), (255, 164,   5, 255), (255, 168, 187, 255)],
                      [( 66, 102,   0, 255), (255,   0,  16, 255), ( 94, 241, 242, 255)],
                      [(  0, 153, 143, 255), (224, 255, 102, 255), (116,  10, 255, 255)],
                      [(153,   0,   0, 255), (255, 255, 128, 255), (255,  80,   5, 255)]]

    colorChanged = pyqtSignal(tuple, np.ndarray)
    colormapChanged = pyqtSignal(tuple, str, str, float, float)

    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.partlist = None
        self.attributes = None
        self._palettes = None
        self._att_idx = None
        self._pal_idx = 0
        self._color = None

        self._mode = "mono"

        # The contents
        self._layout = QHBoxLayout()

        # Mono/Gradient buttons
        _switch_layout = QVBoxLayout()
        self.mono_mode_switch = QRadioButton("Single\nColor")
        self.grad_mode_switch = QRadioButton("Colormap")
        self.mode_group = QButtonGroup()
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.mono_mode_switch)
        self.mode_group.addButton(self.grad_mode_switch)
        self.mono_mode_switch.setChecked(True)

        # Mono Toolbuttons
        self.mono_group = QWidget()
        _mono_layout = QHBoxLayout()
        _mono_button_layout = QGridLayout()
        self.col_cols = 8
        self.col_rows = 3
        self.mono_buttons = [[QToolButton() for i in range(self.col_rows)] for j in range(self.col_cols)]
        for col in range(self.col_cols):
            for row in range(self.col_rows):
                w = self.mono_buttons[col][row]
                color = self.green_armytage[col][row]
                w.setStyleSheet('background-color: rgba({},{},{},{});'.format(*color))
                _mono_button_layout.addWidget(w, row, col, 1, 1)

        _mono_display_layout = QVBoxLayout()
        self.pick_color_button = QPushButton("Pick Custom")

        self._mono_display_label = QLabel("Current Color")
        self.current_color_label = QLabel()
        self.current_color_label.setMinimumSize(50, 30)

        _mono_display_layout.addStretch()
        _mono_display_layout.addWidget(self._mono_display_label, alignment=Qt.AlignCenter)
        _mono_display_layout.addWidget(self.current_color_label, alignment=Qt.AlignCenter)
        _mono_display_layout.addWidget(self.pick_color_button, alignment=Qt.AlignCenter)
        _mono_display_layout.addStretch()

        _mono_layout.addLayout(_mono_button_layout)
        _mono_layout.addLayout(_mono_display_layout)
        self.mono_group.setLayout(_mono_layout)

        # Assemble switch
        _switch_layout.addWidget(self.mono_mode_switch)
        _switch_layout.addWidget(self.grad_mode_switch)

        # Attribute Selector
        _attribute_layout = QVBoxLayout()
        _attribute_label = QLabel("Attribute")
        self.attribute_box = IgnorantComboBox()
        self.attribute_box.setFocusPolicy(Qt.StrongFocus)
        _attribute_layout.addStretch()
        _attribute_layout.addWidget(_attribute_label, alignment=Qt.AlignCenter)
        _attribute_layout.addWidget(self.attribute_box)
        _attribute_layout.addStretch()

        # Palette Selector
        _palette_layout = QVBoxLayout()
        _palette_label = QLabel("Palette")
        self.palette_box = IgnorantComboBox()
        self.palette_box.setFocusPolicy(Qt.StrongFocus)
        _palette_layout.addStretch()
        _palette_layout.addWidget(_palette_label, alignment=Qt.AlignCenter)
        _palette_layout.addWidget(self.palette_box)
        _palette_layout.addStretch()

        # Slider with edits and labels
        _slider_layout = QVBoxLayout()

        # Slider Line 1
        _slider_min_max_layout = QHBoxLayout()
        self.min_label = QLabel("{:.4f}".format(0))
        self.max_label = QLabel("{:.4f}".format(1))
        _slider_min_max_layout.addWidget(self.min_label, alignment=Qt.AlignLeft)
        _slider_min_max_layout.addWidget(self.max_label, alignment=Qt.AlignRight)

        # Slider Line 2
        self.slider = GradientRangeSlider()
        self.slider._singleStep = 0.001
        self.slider._pageStep = 0.01
        self.slider.setOrientation(Qt.Horizontal)

        self.slider.setMinimum(0)
        self.slider.setMaximum(1)
        self.slider.setValue((0, 1))
        self.slider.setEnabled(False)

        # Slider Line 3
        _slider_edit_layout = QHBoxLayout()
        self.lower_edit = QLineEdit("{:.4f}".format(0))
        self.upper_edit = QLineEdit("{:.4f}".format(1))
        _slider_edit_layout.addWidget(self.lower_edit, alignment=Qt.AlignCenter)
        _slider_edit_layout.addWidget(self.upper_edit, alignment=Qt.AlignCenter)

        # Assemble slider
        _slider_layout.addLayout(_slider_min_max_layout)
        _slider_layout.addWidget(self.slider)
        _slider_layout.addLayout(_slider_edit_layout)

        self.cmap_group = QWidget()
        _cmap_group_layout = QHBoxLayout()
        _cmap_group_layout.addLayout(_attribute_layout)
        _cmap_group_layout.addLayout(_palette_layout)
        _cmap_group_layout.addLayout(_slider_layout)
        self.cmap_group.setLayout(_cmap_group_layout)

        # Color settings box
        self.color_group = QGroupBox("Color Settings")
        self._color_group_layout = QStackedLayout()
        self._color_group_layout.addWidget(self.mono_group)
        self._color_group_layout.addWidget(self.cmap_group)
        self.color_group.setLayout(self._color_group_layout)

        # Assemble self
        self._layout.addLayout(_switch_layout)
        self._layout.addWidget(self.color_group)

        self.setLayout(self._layout)

        # Populate palettes
        self._get_palettes()
        if self._palettes is not None:
            for p in self._palettes:
                self.palette_box.addItem(p)

            self.palette_box.setCurrentIndex(self._pal_idx)
            self._set_cmap()

        self._connect()

    def set_partlist(self, partlist):

        self._color = np.array(partlist.color, dtype=np.uint8)
        self._set_color()

        self.partlist = partlist
        self.attributes = partlist.get_main_attributes()
        self.minima = partlist.get_attribute_min(self.attributes)
        self.maxima = partlist.get_attribute_max(self.attributes)
        self.attribute_constant = [False] * len(self.attributes)

        for idx, mini in enumerate(self.minima):
            if mini == self.maxima[idx]:
                self.attribute_constant[idx] = True

        # Populate attributes
        prev = self.attribute_box.blockSignals(True)
        self.attribute_box.clear()
        for a in self.attributes:
            self.attribute_box.addItem(a)

        self._att_idx = 0
        self.attribute_box.setCurrentIndex(self._att_idx)
        self.attribute_box.blockSignals(prev)

        self._set_min_max()

        self._color_changed()

        # value_low = self.minimum
        # value_high = self.maximum
        #
        # if self.constant:
        #     self.slider.setMinimum(self.minimum)
        #     self.slider.setMaximum(self.maximum+1)
        #     self.slider.setValue((value_low, value_high+1))
        #     self.slider.setEnabled(False)
        # else:
        #     self.slider.setMinimum(self.minimum)
        #     self.slider.setMaximum(self.maximum)
        #     self.slider.setValue((value_low, value_high))

    @property
    def minimum(self):
        return self.minima[self._att_idx]

    @property
    def maximum(self):
        return self.maxima[self._att_idx]

    @property
    def constant(self):
        return self.attribute_constant[self._att_idx]

    @property
    def chimx_palette(self):
        return self._palettes[self._pal_idx]

    def _get_palettes(self):
        self._palettes = list(self.session.user_colormaps.keys())

        if len(self._palettes) > 0:
            self._pal_idx = 0

    def _connect(self):
        # Mode switch
        self.mono_mode_switch.clicked.connect(self._mode_switched)
        self.grad_mode_switch.clicked.connect(self._mode_switched)

        # Mono mode buttons
        for col in range(self.col_cols):
            for row in range(self.col_rows):
                self.mono_buttons[col][row].clicked.connect(partial(self._col_clicked, self.green_armytage[col][row]))
        self.pick_color_button.clicked.connect(self._pick_color)

        # Palette combo box
        self.palette_box.currentIndexChanged.connect(partial(self._set_pal_idx))
        self.attribute_box.currentIndexChanged.connect(partial(self._set_att_idx))

        # Slider
        self.slider.valueChanged.connect(partial(self._slider_changed))

        # Edits
        self.lower_edit.returnPressed.connect(partial(self._edit_changed))
        self.upper_edit.returnPressed.connect(partial(self._edit_changed))

    def _mode_switched(self):
        # Switch
        if self.mono_mode_switch.isChecked():
            self._mode = "mono"
        elif self.grad_mode_switch.isChecked():
            self._mode = "gradient"

        self._show_layout()

    def _show_layout(self):
        if self._mode == "mono":
            self._color_group_layout.setCurrentIndex(0)
        elif self._mode == "gradient":
            self._color_group_layout.setCurrentIndex(1)

    def _col_clicked(self, color):
        self._color = np.array(color, dtype=np.uint8)
        self._set_color()

        self._color_changed()

    def _set_color(self):
        self.current_color_label.setStyleSheet('background-color: rgba({},{},{},{});'.format(*tuple(self._color)))

    def _pick_color(self):
        from Qt.QtWidgets import QColorDialog
        cd = QColorDialog(self.window())
        cd.setOption(cd.NoButtons, True)
        cd.currentColorChanged.connect(self._picker_cb)
        cd.destroyed.connect(self._picker_destroyed_cb)
        cd.setOption(cd.ShowAlphaChannel, False)
        if self._color is not None:
            cd.setCurrentColor(QColor(*tuple(self._color)))
        cd.show()

    def _picker_cb(self, color: QColor):
        self._color = np.array([color.red(), color.green(), color.blue(), color.alpha()], dtype=np.uint8)
        self._set_color()

        self._color_changed()

    def _picker_destroyed_cb(self):
        pass

    def _set_pal_idx(self, idx):
        self._pal_idx = idx
        self._set_cmap()

    def _set_cmap(self):
        cmap = self.session.user_colormaps[self.chimx_palette]
        self.slider.set_gradient(cmap)

    def _set_att_idx(self, idx):
        self._att_idx = idx
        self._enable_widgets()
        self._set_min_max()
        self._color_changed()

    def _enable_widgets(self):
        if self.constant:
            self.slider.setEnabled(False)
            self.upper_edit.setEnabled(False)
            self.lower_edit.setEnabled(False)
        else:
            self.slider.setEnabled(True)
            self.upper_edit.setEnabled(True)
            self.lower_edit.setEnabled(True)

    def _set_min_max(self):
        prev = self.slider.blockSignals(True)
        if self.constant:
            self.slider.setMinimum(self.minimum)
            self.slider.setMaximum(self.maximum+1)
            self.slider.setValue((self.minimum, self.maximum+1))
        else:
            self.slider.setMinimum(self.minimum)
            self.slider.setMaximum(self.maximum)
            self.slider.setValue((self.minimum, self.maximum))
        self.slider.blockSignals(prev)

        self.min_label.setText("{:.4f}".format(self.minimum))
        self.max_label.setText("{:.4f}".format(self.maximum))

        prev = self.lower_edit.blockSignals(True)
        prev1 = self.upper_edit.blockSignals(True)
        self.lower_edit.setText("{:.4f}".format(self.minimum))
        self.upper_edit.setText("{:.4f}".format(self.maximum))
        self.lower_edit.blockSignals(prev)
        self.upper_edit.blockSignals(prev1)

    def _slider_changed(self, value):
        prev = self.lower_edit.blockSignals(True)
        prev1 = self.upper_edit.blockSignals(True)
        self.lower_edit.setText("{:.4f}".format(value[0]))
        self.upper_edit.setText("{:.4f}".format(value[1]))
        self.lower_edit.blockSignals(prev)
        self.upper_edit.blockSignals(prev1)

        self._color_changed()

    def _edit_changed(self):
        lower = float(self.lower_edit.text())
        upper = float(self.upper_edit.text())

        if lower < self.minimum:
            prev = self.lower_edit.blockSignals(True)
            self.lower_edit.setText("{:.4f}".format(self.minimum))
            self.lower_edit.blockSignals(prev)
            lower = self.minimum

        if upper > self.maximum:
            prev = self.upper_edit.blockSignals(True)
            self.upper_edit.setText("{:.4f}".format(self.maximum))
            self.upper_edit.blockSignals(prev)
            upper = self.maximum

        prev = self.slider.blockSignals(True)
        self.slider.setValue((lower, upper))
        self.slider.blockSignals(prev)

        self._color_changed()

    def _get_selection(self):
        palette = self.chimx_palette
        attribute = self.attribute_box.currentText()

        # If attribute is constant, ignore the slider.
        if self.constant:
            minimum = self.minimum
            maximum = self.maximum
        else:
            minimum = self.slider.value()[0]
            maximum = self.slider.value()[1]

        return palette, attribute, minimum, maximum

    def _color_changed(self):
        if self._mode == "mono":
            self.colorChanged.emit(self.partlist.id, self._color)
        elif self._mode == "gradient":
            palette, attribute, minimum, maximum = self._get_selection()
            self.colormapChanged.emit(self.partlist.id,
                                      palette,
                                      attribute,
                                      minimum,
                                      maximum)


class GradientRangeSlider(QDoubleRangeSlider):

    QSS = """
    GradientRangeSlider {{
        qproperty-barColor: qlineargradient(x1:0, y1:0, x2:1, y2:0, {});
    }}
    """

    def set_gradient(self, cmap):
        if cmap.value_range() != (0, 1):
            cmap = cmap.rescale_range(0, 1)

        values = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
        colors = cmap.interpolated_rgba8(values)

        stops = []
        for idx, v in enumerate(values):
            stops.append("stop:{} rgb({}, {}, {})".format(v, colors[idx, 0], colors[idx, 1], colors[idx, 2]))

        stopstring = ', '.join(stops)

        qss = self.QSS.format(stopstring)
        self.setStyleSheet(qss)


class IgnorantComboBox(QComboBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, e: QWheelEvent) -> None:
        if not self.hasFocus():
            e.ignore()
        else:
            super().wheelEvent(e)
