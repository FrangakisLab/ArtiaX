from functools import partial
from chimerax.core.commands import run, Command
from chimerax.core.tools import ToolInstance
from chimerax.map.volume import volume_from_grid_data
from chimerax.map_data import ArrayGridData
from chimerax.map import Volume
from chimerax.core.models import Surface

# from chimerax.atomic.molobject import Atom
import os as os
import math as ma
import mrcfile
import numpy as np
from .emwrite import emwrite
from .emread import emread
from .euler_rotation import detRotMat, detInvRotMat, mulMatMat, mulVecMat, getEulerAngles, updateCoordinateSystem, rotateArray
from .object_settings import TomoInstance, MotlInstance
#from .start_tomo_dialogue import ArtiaXDialog

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPalette
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
    QWidget
)

class OptionsWindow(ToolInstance):
    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = True         # We do save/restore in sessions
    help = "help:user/tools/tutorial.html"
                            # Let ChimeraX know about our help page

# ==============================================================================
# Instance Initialization ======================================================
# ==============================================================================


    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)

        self.display_name = "Options Menu"

        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self)

        # Set the font
        self.font = QFont("Arial", 7)

        # We will be adding an item to the tool's context menu, so override
        # the default MainToolWindow fill context menu method
        self.tool_window.fill_context_menu = self.fill_context_menu

        # Set local variables
        self.set_variables()

        # Build the user interfaces
        self.build_default_ui()
        self.build_tomo_ui(session)
        self.build_motl_ui(session)
        # Build the final gui
        self.build_gui()
        # By default show the default window
        self.change_gui(session, "default")

        # Show the selected GUI
        # Set the layout
        self.tool_window.ui_area.setLayout(self.stacked_layout)

        # Show the window on the user-preferred side of the
        # ChimeraX main window
        self.tool_window.manage("left")


# ==============================================================================
# Set some variables ===========================================================
# ==============================================================================


    def set_variables(self):
        self.instance = None

        self.name = None

        # A switch that indicates if the function shall be executed
        # Switch is true if a motivelist is selected
        # When no motivelist is selected and when one is closed,
        # The switch is set to False
        self.execute = True

        # A switch that indicates what the variable slider should do
        self.variable_switch = True     # True indicates radius
                                        # False indicates surface


# ==============================================================================
# Show selected GUI ============================================================
# ==============================================================================


    def build_gui(self):
        # Define a stacked layout and only show the selected layout
        self.stacked_layout = QStackedLayout()
        # Add the widgets to the stacked layout
        self.stacked_layout.addWidget(self.default_widget)
        self.stacked_layout.addWidget(self.tomo_widget)
        self.stacked_layout.addWidget(self.motl_widget)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def change_gui(self, session, option, instance=None):
        if option == "default":
            self.tool_window.title = "Options Menu"
            self.stacked_layout.setCurrentIndex(0)
        elif option == "tomo":
            self.tool_window.title = "Options Menu: " + instance.name
            self.stacked_layout.setCurrentIndex(1)
            self.instance = instance    # Set the tomo instance
            # Now build the tomo sliders
            self.build_tomo_sliders(session, instance)
        elif option == "motl":
            self.tool_window.title = "Options Menu: " + instance.name
            self.stacked_layout.setCurrentIndex(2)
            self.instance = instance    # Set the motl instance
            # Now build the motl sliders
            self.build_motl_sliders(session, instance)
        else:
            print("Guess you have a spelling error somewhere where calling the options window.")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def build_default_ui(self):
        self.default_widget = QWidget()
        self.default_layout = QVBoxLayout()
        self.default_group = QGroupBox("Nothing selected")
        self.default_group.setFont(self.font)
        self.default_layout.addWidget(self.default_group)
        self.default_widget.setLayout(self.default_layout)


# ==============================================================================
# Options Menu for Tomograms ===================================================
# ==============================================================================

    def build_tomo_ui(self, session):
        # This window is a widget of the stacked layout
        self.tomo_widget = QWidget()
        # Define the overall layout
        self.tomo_layout = QVBoxLayout()
        # Set the layout of the Pixel Size LineEdit
        self.group_pixel = QGroupBox("Physical Position")
        self.group_pixel.setFont(self.font)
        self.group_pixel_layout = QGridLayout()

        self.group_pixel_size_label = QLabel("Pixel Size:")
        self.group_pixel_size_label.setFont(self.font)
        self.group_pixel_size_pixlabel = QLineEdit("")
        self.group_pixelSize_button = QPushButton("Apply")
        self.group_physPos_button = QPushButton("Position (xyz):")
        self.group_pixel_size_labelx = QLabel("")
        self.group_pixel_size_labelx.setFont(self.font)
        self.group_pixel_size_labely = QLabel("")
        self.group_pixel_size_labely.setFont(self.font)
        self.group_pixel_size_labelz = QLabel("")
        self.group_pixel_size_labelz.setFont(self.font)

        self.group_pixel_layout.addWidget(self.group_pixel_size_label, 0, 0, 1, 1)
        self.group_pixel_layout.addWidget(self.group_pixel_size_pixlabel, 0, 1, 1, 1)
        self.group_pixel_layout.addWidget(self.group_pixelSize_button, 0, 2, 1, 1)
        self.group_pixel_layout.addWidget(self.group_physPos_button, 1, 0, 1, 1)
        self.group_pixel_layout.addWidget(self.group_pixel_size_labelx, 1, 1, 1, 1)
        self.group_pixel_layout.addWidget(self.group_pixel_size_labely, 1, 2, 1, 1)
        self.group_pixel_layout.addWidget(self.group_pixel_size_labelz, 1, 3, 1, 1)
        # Add grid to group
        self.group_pixel.setLayout(self.group_pixel_layout)

        # Define a group for the contrast sliders
        self.group_contrast = QGroupBox("Contrast Settings")
        self.group_contrast.setFont(self.font)
        # Set the layout of the group
        self.group_contrast_layout = QGridLayout()
        # Define two sliders that control the contrast
        # Center Sliders
        self.group_contrast_center_label = QLabel("Center:")
        self.group_contrast_center_label.setFont(self.font)
        self.group_contrast_center_edit = QLineEdit("")
        self.group_contrast_center_edit.setFont(self.font)
        self.group_contrast_center_slider = QSlider(Qt.Horizontal)
        # Width Slider
        self.group_contrast_width_label = QLabel("Width:")
        self.group_contrast_width_label.setFont(self.font)
        self.group_contrast_width_edit = QLineEdit("")
        self.group_contrast_width_edit.setFont(self.font)
        self.group_contrast_width_slider = QSlider(Qt.Horizontal)
        # Add to the grid layout
        self.group_contrast_layout.addWidget(self.group_contrast_center_label, 0, 0)
        self.group_contrast_layout.addWidget(self.group_contrast_center_edit, 0, 1)
        self.group_contrast_layout.addWidget(self.group_contrast_center_slider, 0, 2)
        self.group_contrast_layout.addWidget(self.group_contrast_width_label, 1, 0)
        self.group_contrast_layout.addWidget(self.group_contrast_width_edit, 1, 1)
        self.group_contrast_layout.addWidget(self.group_contrast_width_slider, 1, 2)
        # Add grid to group
        self.group_contrast.setLayout(self.group_contrast_layout)

        # Define a group for different orthoplanes of a tomogram
        self.group_orthoplanes = QGroupBox("Orthoplanes")
        self.group_orthoplanes.setFont(self.font)
        # Set the layout of the group
        self.group_orthoplanes_layout = QGridLayout()
        # Define different buttons to press for the different orthoslices 
        self.group_orthoplanes_buttonxy = QPushButton("xy")
        self.group_orthoplanes_buttonxz = QPushButton("xz")
        self.group_orthoplanes_buttonyz = QPushButton("yz")
        self.group_orthoplanes_buttonxyz = QPushButton("xyz")
        # Add to the grid layout
        self.group_orthoplanes_layout.addWidget(self.group_orthoplanes_buttonxy, 0, 0)
        self.group_orthoplanes_layout.addWidget(self.group_orthoplanes_buttonxz, 0, 1)
        self.group_orthoplanes_layout.addWidget(self.group_orthoplanes_buttonyz, 0, 2)
        self.group_orthoplanes_layout.addWidget(self.group_orthoplanes_buttonxyz, 0, 3)
        # Add grid to group
        self.group_orthoplanes.setLayout(self.group_orthoplanes_layout)

        # Define a group for the fourier transform of a volume
        self.group_fourier_transform = QGroupBox("Fourier transformation")
        self.group_fourier_transform.setFont(self.font)
        # Set the layout of the group
        self.group_fourier_transform_layout = QGridLayout()
        # Define Button to press for execute the transformation
        self.group_fourier_transform_execute_label = QLabel("FT current volume:")
        self.group_fourier_transform_execute_label.setFont(self.font)
        self.group_fourier_transform_execute_button = QPushButton("FT Execute")
        # Add to the grid layout
        self.group_fourier_transform_layout.addWidget(self.group_fourier_transform_execute_label, 0, 0)
        self.group_fourier_transform_layout.addWidget(self.group_fourier_transform_execute_button, 0, 1)
        # Add grid to group
        self.group_fourier_transform.setLayout(self.group_fourier_transform_layout)

        # Define a group that jumps through the slices
        self.group_slices = QGroupBox("Jump Through Slices")
        self.group_slices.setFont(self.font)
        # Set the layout for the group
        self.group_slices_layout = QGridLayout()
        # Define a Slider and four jump buttons
        self.group_slices_label = QLabel("Slice:")
        self.group_slices_label.setFont(self.font)
        self.group_slices_first_row = QHBoxLayout()
        self.group_slices_edit = QLineEdit("")
        self.group_slices_edit.setFont(self.font)
        self.group_slices_slider = QSlider(Qt.Horizontal)
        self.group_slices_first_row.addWidget(self.group_slices_edit)
        self.group_slices_first_row.addWidget(self.group_slices_slider)
        self.group_slices_second_row = QHBoxLayout()
        self.group_slices_previous_10 = QPushButton("<<")
        self.group_slices_previous_10.setFont(self.font)
        self.group_slices_previous_1 = QPushButton("<")
        self.group_slices_previous_1.setFont(self.font)
        self.group_slices_next_1 = QPushButton(">")
        self.group_slices_next_1.setFont(self.font)
        self.group_slices_next_10 = QPushButton(">>")
        self.group_slices_next_10.setFont(self.font)
        self.group_slices_second_row.addWidget(self.group_slices_previous_10)
        self.group_slices_second_row.addWidget(self.group_slices_previous_1)
        self.group_slices_second_row.addWidget(self.group_slices_next_10)
        self.group_slices_second_row.addWidget(self.group_slices_next_1)
        # Add to the grid layout
        self.group_slices_layout.addWidget(self.group_slices_label, 0, 0)
        self.group_slices_layout.addLayout(self.group_slices_first_row, 0, 1)
        self.group_slices_layout.addLayout(self.group_slices_second_row, 1, 1)
        # Add grid to group
        self.group_slices.setLayout(self.group_slices_layout)

        # Add groups to layout
        self.tomo_layout.addWidget(self.group_pixel)
        self.tomo_layout.addWidget(self.group_contrast)
        self.tomo_layout.addWidget(self.group_slices)
        self.tomo_layout.addWidget(self.group_orthoplanes)
        self.tomo_layout.addWidget(self.group_fourier_transform)

        # And finally set the layout of the widget
        self.tomo_widget.setLayout(self.tomo_layout)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Tomo Window Functions ++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def center_execute(self, session, value, tomo_instance):
        # Use value as the current center and the width property width from tomo_instance
        center = value
        width = tomo_instance.width_position
        position = 0.5  # Default value for center intensity
        # Make a linear interpolation for the center intensity
        if center + width/2 > tomo_instance.data_max:
            if center - width/2 < tomo_instance.data_min:
                position = (center - tomo_instance.data_min)/(tomo_instance.data_max - tomo_instance.data_min)
            else:
                position = width/(2*(tomo_instance.data_max - center + width/2))
        else:
            if center - width/2 < tomo_instance.data_min:
                position = (center - tomo_instance.data_min)/(center + width/2 - tomo_instance.data_min)
            else:
                position = 0.5
        # Run the corresponding command -> Set the three positions of the yellow markers
        # each by a level command
        command = "volume #{} ".format(tomo_instance.id_string)  # Insert ID
        command += "level {},{} ".format(center - width/2, 0)      # Position of first marker
        command += "level {},{} ".format(center, position)            # Position of second marker
        command += "level {},{}".format(center + width/2, 1)       # Position of third marker
        # Run the command
        run(session, command)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def width_execute(self, session, value, tomo_instance):
        # Use value as the current width and the center property width from tomo_instance
        center = tomo_instance.center_position
        width = value
        position = 0.5  # Default value for center intensity
        # Make a linear interpolation for the center intensity
        if center + width/2 > tomo_instance.data_max:
            if center - width/2 < tomo_instance.data_min:
                position = (center - tomo_instance.data_min)/(tomo_instance.data_max - tomo_instance.data_min)
            else:
                position = width/(2*(tomo_instance.data_max - center + width/2))
        else:
            if center - width/2 < tomo_instance.data_min:
                position = (center - tomo_instance.data_min)/(center + width/2 - tomo_instance.data_min)
            else:
                position = 0.5
        # Run the corresponding command -> Set the three positions of the yellow markers
        # each by a level command
        command = "volume #{} ".format(tomo_instance.id_string)      # Insert ID
        command += "level {},{} ".format(center - width/2, 0)        # Position of first marker
        command += "level {},{} ".format(center, position)           # Position of second marker
        command += "level {},{}".format(center + width/2, 1)         # Position of third marker
        # Run the command
        run(session, command)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def slice_execute(self, session, value, tomo_instance):
        # Execute the command that shows the wanted plane of the tomogram
        command = "volume #{} plane z,{}".format(tomo_instance.id_string, value)
        run(session, command)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def build_tomo_sliders(self, session, tomo_instance):
        # Center goes in 100 steps from the minimal value to the maximal value of the data grid
        self.group_contrast_center_slider.setMinimum(ma.ceil(10000*tomo_instance.data_min))
        self.group_contrast_center_slider.setMaximum(ma.floor(10000*tomo_instance.data_max))
        self.group_contrast_center_slider.setValue(ma.ceil(tomo_instance.center_position*10000))
        self.group_contrast_center_edit.setText(str(tomo_instance.center_position))
        # Width goes from negative distance between minimum and maximum to positive distance
        distance = ma.floor(10000*(tomo_instance.data_max - tomo_instance.data_min))
        self.group_contrast_width_slider.setMinimum(-distance)
        self.group_contrast_width_slider.setMaximum(distance)
        self.group_contrast_width_slider.setValue(ma.ceil(tomo_instance.width_position*10000))
        self.group_contrast_width_edit.setText(str(tomo_instance.width_position))
        # Slice goes along the z-dimension of the tomogram
        self.group_slices_slider.setMinimum(1)
        self.group_slices_slider.setMaximum(tomo_instance.z_dim)
        self.group_slices_slider.setValue(tomo_instance.slice_position)
        self.group_slices_edit.setText(str(tomo_instance.slice_position))
        

# ==============================================================================
# Options Menu for Motivelists =================================================
# ==============================================================================


    def build_motl_ui(self, session):

        # This window is a widget of the stacked layout
        self.motl_widget = QWidget()

        # Define the overall layout
        self.motl_layout = QVBoxLayout()

        # Define a group for the visualization sliders
        self.group_select = QGroupBox("Visualization Options:")
        self.group_select.setFont(self.font)
        self.group_select.setCheckable(True)

        # Set the layout of the group
        self.group_select_layout = QGridLayout()
        # Define the input of the GridLayout which includes some sliders and LineEdits
        # Selection Slider
        self.group_select_selection_label = QLabel("Selected:")
        self.group_select_selection_label.setFont(self.font)
        self.group_select_selection_edit = QLineEdit("")
        self.group_select_selection_edit.setFont(self.font)
        self.group_select_selection_NumObjLabel = QLabel()
        self.group_select_selection_NumObjLabel.setText("# obj.")
        self.group_select_selection_clampview = QPushButton("Clamp View")
        # Row Slider 1
        self.group_select_row1_label = QLabel("Row 1:")
        self.group_select_row1_label.setFont(self.font)
        self.group_select_row1_edit = QLineEdit("")
        self.group_select_row1_edit.setFont(self.font)
        self.group_select_row1_slider = QScrollBar(Qt.Horizontal)
        # Row Slider 2
        self.group_select_row2_label = QLabel("Row 2:")
        self.group_select_row2_label.setFont(self.font)
        self.group_select_row2_edit = QLineEdit("")
        self.group_select_row2_edit.setFont(self.font)
        self.group_select_row2_slider = QScrollBar(Qt.Horizontal)
        # Lower Threshold Slider
        self.group_select_lower_thresh_label = QLabel("Lower Threshold 1:")
        self.group_select_lower_thresh_label.setFont(self.font)
        self.group_select_lower_thresh_edit = QLineEdit("")
        self.group_select_lower_thresh_edit.setFont(self.font)
        self.group_select_lower_thresh_slider = QSlider(Qt.Horizontal)
        # Upper threshold Slider
        self.group_select_upper_thresh_label = QLabel("Upper Threshold 1:")
        self.group_select_upper_thresh_label.setFont(self.font)
        self.group_select_upper_thresh_edit = QLineEdit("")
        self.group_select_upper_thresh_edit.setFont(self.font)
        self.group_select_upper_thresh_slider = QSlider(Qt.Horizontal)
        # Lower Threshold Slider 2
        self.group_select_lower_thresh_label2 = QLabel("Lower Threshold 2:")
        self.group_select_lower_thresh_label2.setFont(self.font)
        self.group_select_lower_thresh_edit2 = QLineEdit("")
        self.group_select_lower_thresh_edit2.setFont(self.font)
        self.group_select_lower_thresh_slider2 = QSlider(Qt.Horizontal)
        # Upper threshold Slider 2
        self.group_select_upper_thresh_label2 = QLabel("Upper Threshold 2:")
        self.group_select_upper_thresh_label2.setFont(self.font)
        self.group_select_upper_thresh_edit2 = QLineEdit("")
        self.group_select_upper_thresh_edit2.setFont(self.font)
        self.group_select_upper_thresh_slider2 = QSlider(Qt.Horizontal)
        # Color Gradient
        self.group_select_color_label = QLabel("Colormap:")
        self.group_select_color_label.setFont(self.font)
        self.group_select_color_lower_edit = QLineEdit("")
        self.group_select_color_lower_edit.setFont(self.font)
        self.group_select_color = QLineEdit("")     # This is where the color gradient should be
        self.group_select_color_upper_edit = QLineEdit("")
        self.group_select_color_upper_edit.setFont(self.font)
        # Variable Slider -> Either radius of marker of surface level of objects
        self.group_select_variable_label = QLabel("Radius:")    # By default this is the radius slider
        self.group_select_variable_label.setFont(self.font)
        self.group_select_variable_edit = QLineEdit("")
        self.group_select_variable_edit.setFont(self.font)
        self.group_select_variable_slider = QSlider(Qt.Horizontal)
        # Add to the grid layout
        self.group_select_layout.addWidget(self.group_select_selection_label, 0, 0, 1, 1)
        self.group_select_layout.addWidget(self.group_select_selection_edit, 0, 1, 1, 1)
        self.group_select_layout.addWidget(self.group_select_selection_NumObjLabel, 0, 2, 1, 2)
        self.group_select_layout.addWidget(self.group_select_selection_clampview, 0, 3, 1, 2)
        self.group_select_layout.addWidget(self.group_select_row1_label, 1, 0, 1, 1)
        self.group_select_layout.addWidget(self.group_select_row1_edit, 1, 1, 1, 1)
        self.group_select_layout.addWidget(self.group_select_row1_slider, 1, 2, 1, 2)
        self.group_select_layout.addWidget(self.group_select_lower_thresh_label, 2, 0, 1, 1)
        self.group_select_layout.addWidget(self.group_select_lower_thresh_edit, 2, 1, 1, 1)
        self.group_select_layout.addWidget(self.group_select_lower_thresh_slider, 2, 2, 1, 2)
        self.group_select_layout.addWidget(self.group_select_upper_thresh_label, 3, 0, 1, 1)
        self.group_select_layout.addWidget(self.group_select_upper_thresh_edit, 3, 1, 1, 1)
        self.group_select_layout.addWidget(self.group_select_upper_thresh_slider, 3, 2, 1, 2)
        self.group_select_layout.addWidget(self.group_select_row2_label, 4, 0, 1, 1)
        self.group_select_layout.addWidget(self.group_select_row2_edit, 4, 1, 1, 1)
        self.group_select_layout.addWidget(self.group_select_row2_slider, 4, 2, 1, 2)
        self.group_select_layout.addWidget(self.group_select_lower_thresh_label2, 5, 0, 1, 1)
        self.group_select_layout.addWidget(self.group_select_lower_thresh_edit2, 5, 1, 1, 1)
        self.group_select_layout.addWidget(self.group_select_lower_thresh_slider2, 5, 2, 1, 2)
        self.group_select_layout.addWidget(self.group_select_upper_thresh_label2, 6, 0, 1, 1)
        self.group_select_layout.addWidget(self.group_select_upper_thresh_edit2, 6, 1, 1, 1)
        self.group_select_layout.addWidget(self.group_select_upper_thresh_slider2, 6, 2, 1, 2)
        self.group_select_layout.addWidget(self.group_select_color_label, 7, 0, 1, 1)
        self.group_select_layout.addWidget(self.group_select_color_lower_edit, 7, 1, 1, 1)
        self.group_select_layout.addWidget(self.group_select_color, 7, 2, 1, 1)
        self.group_select_layout.addWidget(self.group_select_color_upper_edit, 7, 3, 1, 1)
        self.group_select_layout.addWidget(self.group_select_variable_label, 8, 0, 1, 1)
        self.group_select_layout.addWidget(self.group_select_variable_edit, 8, 1, 1, 1)
        self.group_select_layout.addWidget(self.group_select_variable_slider, 8, 2, 1, 2)
        # Set layout of group
        self.group_select.setLayout(self.group_select_layout)

        # Define a group for the maniulation buttons
        self.group_manipulation = QGroupBox("Manipulation Options:")
        self.group_manipulation.setFont(self.font)
        self.group_manipulation.setCheckable(True)
        self.group_manipulation.setChecked(False)

        # Define layout of the group
        self.group_manipulation_layout = QVBoxLayout()
        # Add a row of buttons
        self.group_manipulation_buttons_1 = QHBoxLayout()
        self.group_manipulation_update_button = QPushButton("Update Motivelist")
        self.group_manipulation_update_button.setFont(self.font)
        self.group_manipulation_add_button = QPushButton("Add Marker to Motivelist")
        self.group_manipulation_add_button.setFont(self.font)
        self.group_manipulation_print_button = QPushButton("Print Motivelist to Log")
        self.group_manipulation_print_button.setFont(self.font)
        self.group_manipulation_buttons_1.addWidget(self.group_manipulation_update_button)
        self.group_manipulation_buttons_1.addWidget(self.group_manipulation_add_button)
        self.group_manipulation_buttons_1.addWidget(self.group_manipulation_print_button)
        # Add another row of buttons
        self.group_manipulation_buttons_2 = QHBoxLayout()
        self.group_manipulation_delete_button = QPushButton("Delete selected")
        self.group_manipulation_delete_button.setFont(self.font)
        self.group_manipulation_reset_single_button = QPushButton("Reset selected")
        self.group_manipulation_reset_single_button.setFont(self.font)
        self.group_manipulation_reset_all_button = QPushButton("Reset all")
        self.group_manipulation_reset_all_button.setFont(self.font)
        self.group_manipulation_buttons_2.addWidget(self.group_manipulation_delete_button)
        self.group_manipulation_buttons_2.addWidget(self.group_manipulation_reset_single_button)
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
        self.group_manipulation_layout.addLayout(self.group_manipulation_buttons_1)
        self.group_manipulation_layout.addLayout(self.group_manipulation_buttons_2)
        self.group_manipulation_layout.addLayout(self.browse_layout)
        # Set layout of group
        self.group_manipulation.setLayout(self.group_manipulation_layout)

        # Add groups to layout
        self.motl_layout.addWidget(self.group_manipulation)
        self.motl_layout.addWidget(self.group_select)

        # And finally set the layout of the widget
        self.motl_widget.setLayout(self.motl_layout)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Motl Group Functions +++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #
    def ClampView_execute(self, session, value):

        if value == 0:      #Every thing is selected in the motivelist, zoom on them all

            run(session,"view sel clip true pad 0.5")

        else:               # Only show object/marker with index value-1

            run(session,"view sel clip false pad  0.7")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def row1_execute(self, session, value, motl_instance):
        # At first show all objects again
        for i in range(len(motl_instance.motivelist)):
            object = motl_instance.motivelist[i][20]
            if isinstance(object, Volume):
                object.show(show=True)
            else:
                object.hide = False
        # Build the sliders for the threshold
        self.build_other_motl_sliders(session, value, motl_instance)
        # Set the colors
        if value == 0:  # Default selected colors
            self.motl_color(session, True, 0, motl_instance)
        else:           # Build color gradient
            self.motl_colorgradient(session, value, motl_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def row2_execute(self, session, value, motl_instance):
        # At first show all objects again
        for i in range(len(motl_instance.motivelist)):
            object = motl_instance.motivelist[i][20]
            if isinstance(object, Volume):
                object.show(show=True)
            else:
                object.hide = False
        # Build the sliders for the threshold
        self.build_other_motl_sliders2(session, value, motl_instance)
        # Set the colors
        if value == 0:  # Default selected colors
            self.motl_color(session, True, 0, motl_instance)
        else:           # Build color gradient
            self.motl_colorgradient(session, value, motl_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def threshold_execute(self, session, lower_thresh1, upper_thresh1, lower_thresh2, upper_thresh2, motl_instance):
        # Row 1
        if motl_instance.row1_position != 0 and motl_instance.row2_position != 0:
            # Every object within the threshold boundaries is shown
            # Every object outside the boundaries is hidden
            row_list1 = [particle[motl_instance.row1_position - 1] for particle in motl_instance.motivelist]
            row_list2 = [particle[motl_instance.row2_position - 1] for particle in motl_instance.motivelist]
            object_list = [particle[20] for particle in motl_instance.motivelist]

            for i in range(len(object_list)):
                object = object_list[i]
                if (row_list1[i] >= lower_thresh1 and row_list1[i] <= upper_thresh1) and (row_list2[i] >= lower_thresh2 and row_list2[i] <= upper_thresh2): # Show the objects
                    if isinstance(object, Volume):
                        object.show(show=True)
                    else:
                        object.hide = False
                else:                                                           # Hide the objects
                    if isinstance(object, Volume):
                        object.show(show=False)
                    else:
                        object.hide = True
                        
        if motl_instance.row1_position != 0 and motl_instance.row2_position == 0 :
            # Every object within the threshold boundaries is shown
            # Every object outside the boundaries is hidden
            row_list1 = [particle[motl_instance.row1_position - 1] for particle in motl_instance.motivelist]
            object_list = [particle[20] for particle in motl_instance.motivelist]

            for i in range(len(object_list)):
                object = object_list[i]
                if (row_list1[i] >= lower_thresh1 and row_list1[i] <= upper_thresh1) : # Show the objects
                    if isinstance(object, Volume):
                        object.show(show=True)
                    else:
                        object.hide = False
                else:                                                           # Hide the objects
                    if isinstance(object, Volume):
                        object.show(show=False)
                    else:
                        object.hide = True
        # Row 2
        if motl_instance.row2_position != 0 and motl_instance.row1_position == 0 :
            # Every object within the threshold boundaries is shown
            # Every object outside the boundaries is hidden
            row_list2 = [particle[motl_instance.row2_position - 1] for particle in motl_instance.motivelist]
            object_list = [particle[20] for particle in motl_instance.motivelist]

            for i in range(len(object_list)):
                object = object_list[i]
                if (row_list2[i] >= lower_thresh2 and row_list2[i] <= upper_thresh2) : # Show the objects
                    if isinstance(object, Volume):
                        object.show(show=True)
                    else:
                        object.hide = False
                else:                                                           # Hide the objects
                    if isinstance(object, Volume):
                        object.show(show=False)
                    else:
                        object.hide = True

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def radius_execute(self, session, value, motl_instance):
        # Since the radius is selected all objects associated with this
        # Motivelist in fact are markers -> We don't need to make a difference
        # Between markers and volumes
        markers = [col[20] for col in motl_instance.motivelist]
        for marker in markers:
            marker.radius = value

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def surface_execute(self, session, value, motl_instance):
        # Since the surface is selected all objects associated with this
        # Motivelist in fact are volumes -> We don't need to make a difference
        # Between markers and volumes
        objects = [col[20] for col in motl_instance.motivelist]
        for object in objects:
            if isinstance(object, Volume):
                # Use the set_parameters function of the volume object
                # To set the level of the corresponding surface
                object.set_parameters(surface_levels=[value])

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def build_motl_sliders(self, session, motl_instance):
        # Selection Label
        self.group_select_selection_NumObjLabel.setText("# obj. "+str(len(motl_instance.motivelist)))
        #self.group_select_selection_slider.setMinimum(0)
        #self.group_select_selection_slider.setValue(motl_instance.selection_position)
        self.group_select_selection_edit.setText(str(motl_instance.selection_position))
        # Row 1 Slider
        self.group_select_row1_slider.setMinimum(0)
        self.group_select_row1_slider.setMaximum(20)
        self.group_select_row1_slider.setValue(motl_instance.row1_position)
        self.group_select_row1_edit.setText(str(motl_instance.row1_position))
        # Row 2 Slider
        self.group_select_row2_slider.setMinimum(0)
        self.group_select_row2_slider.setMaximum(20)
        self.group_select_row2_slider.setValue(motl_instance.row2_position)
        self.group_select_row2_edit.setText(str(motl_instance.row2_position))
        # Set default values for other sliders -> Are build when corresponding row is chosen
        # Lower Threshold
        self.group_select_lower_thresh_slider.setMinimum(0)
        self.group_select_lower_thresh_slider.setMaximum(0)
        self.group_select_lower_thresh_slider.setValue(0)
        self.group_select_lower_thresh_edit.setText("")
        # Upper Threshold
        self.group_select_upper_thresh_slider.setMinimum(0)
        self.group_select_upper_thresh_slider.setMaximum(0)
        self.group_select_upper_thresh_slider.setValue(0)
        self.group_select_upper_thresh_edit.setText("")
        # Finally radius/surface slider depends on whether an object has already
        # Been chosen for the motivelist
        if motl_instance.obj_name == None:  # Build radius slider
            self.group_select_variable_slider.setMinimum(1)
            self.group_select_variable_slider.setMaximum(1000)
            self.group_select_variable_slider.setValue(motl_instance.radius_position*10)
            self.group_select_variable_edit.setText(str(motl_instance.radius_position))
            # Just to make sure also change the label text here
            self.group_select_variable_label.setText("Radius:")
        else:                               # Build surface slider
            self.group_select_variable_slider.setMinimum(ma.ceil(100*motl_instance.surface_min))
            self.group_select_variable_slider.setMaximum(ma.floor(100*motl_instance.surface_max))
            self.group_select_variable_slider.setValue(motl_instance.surface_position*100)
            self.group_select_variable_edit.setText(str(motl_instance.surface_position))
            # Don't forget to change the corresponding label
            self.group_select_variable_label.setText("Surface Level:")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def build_other_motl_sliders(self, session, row, motl_instance):
        # If the 0th row is selected, threshold sliders are set back to default
        if row == 0:
            # Lower Threshold
            self.group_select_lower_thresh_slider.setMinimum(0)
            self.group_select_lower_thresh_slider.setMaximum(0)
            self.group_select_lower_thresh_slider.setValue(0)
            self.group_select_lower_thresh_edit.setText("")
            # Upper Threshold
            self.group_select_upper_thresh_slider.setMinimum(0)
            self.group_select_upper_thresh_slider.setMaximum(0)
            self.group_select_upper_thresh_slider.setValue(0)
            self.group_select_upper_thresh_edit.setText("")
            # Set Colorgradient LineEdits to default
            self.group_select_color_lower_edit.setText("")
            self.group_select_color_upper_edit.setText("")
        elif row == 1:  # Cross-correlation is a little special since the range is only between 0 and 1
            row_list = [particle[0] for particle in motl_instance.motivelist]
            # Lower Threshold
            self.group_select_lower_thresh_slider.setMinimum(ma.floor(min(row_list)*100))
            self.group_select_lower_thresh_slider.setMaximum(ma.ceil(max(row_list)*100))
            self.group_select_lower_thresh_slider.setValue(ma.floor(min(row_list)*100))
            self.group_select_lower_thresh_edit.setText(str(ma.floor(min(row_list))))
            # Upper Threshold
            self.group_select_upper_thresh_slider.setMinimum(ma.floor(min(row_list)*100))
            self.group_select_upper_thresh_slider.setMaximum(ma.ceil(max(row_list)*100))
            self.group_select_upper_thresh_slider.setValue(ma.ceil(max(row_list)*100))
            self.group_select_upper_thresh_edit.setText(str(ma.ceil(max(row_list))))
            # Set values on Colorgradient LineEdits
            self.group_select_color_lower_edit.setText(str(ma.floor(min(row_list))))
            self.group_select_color_upper_edit.setText(str(ma.ceil(max(row_list))))
        else:   # Set the range of the thresholds corresponding to the row of the motivelist
            row_list = [particle[row-1] for particle in motl_instance.motivelist]
            # Lower Threshold
            self.group_select_lower_thresh_slider.setMinimum(ma.floor(min(row_list)))
            self.group_select_lower_thresh_slider.setMaximum(ma.ceil(max(row_list)))
            self.group_select_lower_thresh_slider.setValue(ma.floor(min(row_list)))
            self.group_select_lower_thresh_edit.setText(str(ma.floor(min(row_list))))
            # Upper Threshold
            self.group_select_upper_thresh_slider.setMinimum(ma.floor(min(row_list)))
            self.group_select_upper_thresh_slider.setMaximum(ma.ceil(max(row_list)))
            self.group_select_upper_thresh_slider.setValue(ma.ceil(max(row_list)))
            self.group_select_upper_thresh_edit.setText(str(ma.ceil(max(row_list))))
            # Set values on Colorgradient LineEdits
            self.group_select_color_lower_edit.setText(str(ma.floor(min(row_list))))
            self.group_select_color_upper_edit.setText(str(ma.ceil(max(row_list))))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def build_other_motl_sliders2(self, session, row, motl_instance):
        # If the 0th row is selected, threshold sliders are set back to default
        if row == 0:
            # Lower Threshold
            self.group_select_lower_thresh_slider2.setMinimum(0)
            self.group_select_lower_thresh_slider2.setMaximum(0)
            self.group_select_lower_thresh_slider2.setValue(0)
            self.group_select_lower_thresh_edit2.setText("")
            # Upper Threshold
            self.group_select_upper_thresh_slider2.setMinimum(0)
            self.group_select_upper_thresh_slider2.setMaximum(0)
            self.group_select_upper_thresh_slider2.setValue(0)
            self.group_select_upper_thresh_edit2.setText("")
            # Set Colorgradient LineEdits to default
            self.group_select_color_lower_edit.setText("")
            self.group_select_color_upper_edit.setText("")
        elif row == 1:  # Cross-correlation is a little special since the range is only between 0 and 1
            row_list = [particle[0] for particle in motl_instance.motivelist]
            # Lower Threshold
            self.group_select_lower_thresh_slider2.setMinimum(ma.floor(min(row_list)*100))
            self.group_select_lower_thresh_slider2.setMaximum(ma.ceil(max(row_list)*100))
            self.group_select_lower_thresh_slider2.setValue(ma.floor(min(row_list)*100))
            self.group_select_lower_thresh_edit2.setText(str(ma.floor(min(row_list))))
            # Upper Threshold
            self.group_select_upper_thresh_slider2.setMinimum(ma.floor(min(row_list)*100))
            self.group_select_upper_thresh_slider2.setMaximum(ma.ceil(max(row_list)*100))
            self.group_select_upper_thresh_slider2.setValue(ma.ceil(max(row_list)*100))
            self.group_select_upper_thresh_edit2.setText(str(ma.ceil(max(row_list))))
            # Set values on Colorgradient LineEdits
            self.group_select_color_lower_edit.setText(str(ma.floor(min(row_list))))
            self.group_select_color_upper_edit.setText(str(ma.ceil(max(row_list))))
        else:   # Set the range of the thresholds corresponding to the row of the motivelist
            row_list = [particle[row-1] for particle in motl_instance.motivelist]
            # Lower Threshold
            self.group_select_lower_thresh_slider2.setMinimum(ma.floor(min(row_list)))
            self.group_select_lower_thresh_slider2.setMaximum(ma.ceil(max(row_list)))
            self.group_select_lower_thresh_slider2.setValue(ma.floor(min(row_list)))
            self.group_select_lower_thresh_edit2.setText(str(ma.floor(min(row_list))))
            # Upper Threshold
            self.group_select_upper_thresh_slider2.setMinimum(ma.floor(min(row_list)))
            self.group_select_upper_thresh_slider2.setMaximum(ma.ceil(max(row_list)))
            self.group_select_upper_thresh_slider2.setValue(ma.ceil(max(row_list)))
            self.group_select_upper_thresh_edit2.setText(str(ma.ceil(max(row_list))))
            # Set values on Colorgradient LineEdits
            self.group_select_color_lower_edit.setText(str(ma.floor(min(row_list))))
            self.group_select_color_upper_edit.setText(str(ma.ceil(max(row_list))))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Motl Other Functions +++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def motl_color(self, session, option, value, motl_instance):
        if option:              # Motl instance got selected -> lighter blue
            if value == 0:      # Color all
                for i in range(len(motl_instance.motivelist)):
                    object = motl_instance.motivelist[i][20]
                    if isinstance(object, Volume):      # Color the surface of volume
                        object.surfaces[0].rgba = [0, 1, 1, 1]
                    else:                               # Color the marker
                        object.color = [0, 255, 255, 255]
            else:               # Only color object/marker of index value-1
                object = motl_instance.motivelist[value-1][20]
                if ininstance(object, Volume):          # Color the surface of volume
                    object.surfaces[0].rgba = [0, 1, 1, 1]
                else:                                   # Color the marker
                    object.color = [0, 255, 255, 255]
        else:                   # Motl got unselected -> color default blue
            if value == 0:      # Color all
                for i in range(len(motl_instance.motivelist)):
                    object = motl_instance.motivelist[i][20]
                    if isinstance(object, Volume):      # Color the surface of volume
                        object.surfaces[0].rgba = [0, 0, 1, 1]
                    else:                               # Color the marker
                        object.color = [0, 0, 255, 255]
            else:               # Only color object/marker of index value-1
                object = motl_instance.motivelist[value-1][20]
                if ininstance(object, Volume):          # Color the surface of volume
                    object.surfaces[0].rgba = [0, 0, 1, 1]
                else:                                   # Color the marker
                    object.color = [0, 0, 255, 255]

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def motl_colorgradient(self, session, row, motl_instance):
        # Build list of values of corresponding row
        row_list = [particle[row-1] for particle in motl_instance.motivelist]
        object_list = [particle[20] for particle in motl_instance.motivelist]
        id_list = [particle[21] for particle in motl_instance.motivelist]
        min_val = min(row_list)
        max_val = max(row_list)
        center = 0.5*(min_val + max_val)

        # Now get an entry from the val_list and translate it to a color
        for i in range(len(row_list)):
            value = row_list[i]
            object = object_list[i]
            if value < center:
                relative_position = (value - min_val)/(center - min_val)
                if isinstance(object, Volume):          # Color the surface of volume
                    colors = [1, relative_position, 0, 1]
                    object.surfaces[0].rgba = colors
                else:                                   # Color the marker
                    colors = [255, relative_position*255, 0, 255]
                    object.color = colors
            elif value == center:
                if isinstance(object, Volume):
                    object.surfaces[0].rgba = [1, 1, 0, 1]
                else:
                    object.color = [255, 255, 0, 255]
            elif value > center:
                relative_position = (value - center)/(max_val - center)
                if isinstance(object, Volume):          # Color the surface of volume
                    colors = [1 - relative_position, 1 - relative_position*0.5, 0, 1]
                    object.surfaces[0].rgba = colors
                else:                                   # Color the marker
                    colors = [255 - relative_position*255, 255 - relative_position*255*0.5, 0, 255]
                    object.color = colors

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

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
        from Qt.QtQWidgets import QAction
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
