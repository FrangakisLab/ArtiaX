from functools import partial
from chimerax.core.commands import run, Command
from chimerax.core.tools import ToolInstance
from chimerax.map.volume import volume_from_grid_data
from chimerax.map_data import ArrayGridData
from chimerax.map import Volume
import os as os
import math as ma
import mrcfile
import numpy as np
from .emwrite import emwrite
from .emread import emread
from .euler_rotation import detRotMat, detInvRotMat, mulMatMat, mulVecMat, getEulerAngles, updateCoordinateSystem, rotateArray

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
    QTableWidget,
    QTableWidgetItem,
    QTableView,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget
)

# ==============================================================================
# Visualization Window =========================================================
# ==============================================================================

class Visualization(ToolInstance):
    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = True         # We do save/restore in sessions
    help = "help:user/tools/tutorial.html"
                            # Let ChimeraX know about our help page

# ==============================================================================
# Instance Initialization ======================================================
# ==============================================================================


    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)

        self.display_name = "Visualization options of selected motivelist"

        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self)

        # Set the font
        self.font = QFont("Arial", 7)

        # We will be adding an item to the tool's context menu, so override
        # the default MainToolWindow fill context menu method
        self.tool_window.fill_context_menu = self.fill_context_menu

        # Our user interface is simple enough that we could probably inline
        # the code right here, but for any kind of even moderately complex
        # interface, it is probably better to put the code in a method so
        # that this __init__ method remains readable.
        self._build_ui(session)

        # Set local variables
        self.set_variables()

        # A switch thtat indicates if the function shall be executed
        # Switch is true if a motivelist is selected
        # When no motivelist is selected and when one is closed,
        # The switch is set to False
        self.execute = True

        # A switch that indicates what the variable slider should do
        self.variable_switch = True     # True indicates radius
                                        # False indicates surface


# ==============================================================================
# Build Main Menu ==============================================================
# ==============================================================================

    def _build_ui(self, session):
        # At first set up the properties group
        self.group_motl_props = QGroupBox("Properties")
        self.group_motl_props.setFont(self.font)
        # Define the properties that should be displayed
        # Those actions are connected to functions outside of this class
        self.group_motl_props_name = QLabel("")
        self.group_motl_props_name.setFont(self.font)
        self.group_motl_props_obj_name = QLabel("")
        self.group_motl_props_obj_name.setFont(self.font)
        self.group_motl_props_number_particles = QLabel("")
        self.group_motl_props_number_particles.setFont(self.font)
        # Use a grid layout for this group
        self.group_motl_props_layout = QGridLayout()
        # Add all the widgets
        # First column
        self.group_motl_prop_number_particles = QLabel("Number of particles:")
        self.group_motl_prop_number_particles.setFont(self.font)
        self.group_motl_props_layout.addWidget(self.group_motl_prop_number_particles, 0, 0)
        # Second column
        self.group_motl_props_layout.addWidget(self.group_motl_props_number_particles, 0, 1)
        # Set the layout of the group
        self.group_motl_props.setLayout(self.group_motl_props_layout)

        # Set up the selection group
        self.group_motl_select = QGroupBox("Selection")
        self.group_motl_select.setFont(self.font)
        # Define the selection options that should be displayed
        self.group_motl_select_single = QLineEdit("")
        self.group_motl_select_single.setFont(self.font)
        self.group_motl_select_slider = QScrollBar(Qt.Horizontal)
        self.group_motl_select_row_val = QLineEdit("")
        self.group_motl_select_row_val.setFont(self.font)
        self.group_motl_select_row_slider = QScrollBar(Qt.Horizontal)
        self.group_motl_select_lower_val = QLineEdit("")
        self.group_motl_select_lower_val.setFont(self.font)
        self.group_motl_select_lower_slider = QSlider(Qt.Horizontal)
        self.group_motl_select_lower_name = QLabel("Lower Threshold")
        self.group_motl_select_lower_name.setFont(self.font)
        self.group_motl_select_upper_val = QLineEdit("")
        self.group_motl_select_upper_val.setFont(self.font)
        self.group_motl_select_upper_slider = QSlider(Qt.Horizontal)
        self.group_motl_select_upper_name = QLabel("Upper threshold")
        self.group_motl_select_upper_name.setFont(self.font)
        self.group_motl_select_colormap_name = QLabel("Colormap")
        self.group_motl_select_colormap_name.setFont(self.font)
        self.group_motl_select_colormap_lower = QLineEdit("")
        self.group_motl_select_colormap_lower.setFont(self.font)
        self.group_motl_select_colormap_upper = QLineEdit("")
        self.group_motl_select_colormap_upper.setFont(self.font)
        self.group_motl_select_colormap_map = QLineEdit("")     # This needs to be changed!
        self.group_motl_select_colormap = QHBoxLayout()         # This needs to be changed!
        self.group_motl_select_colormap.addWidget(self.group_motl_select_colormap_map)          # This needs to be changed!
        self.group_motl_select_colormap.addWidget(self.group_motl_select_colormap_upper)        # This needs to be changed!
        self.group_motl_select_colormap.setStretch(0, 1)
        self.group_motl_select_colormap.setStretch(1, 0.5)
        self.group_motl_select_variable_name = QLabel("Radius")
        self.group_motl_select_variable = QLineEdit("")
        self.group_motl_select_variable.setFont(self.font)
        self.group_motl_select_variable_slider = QSlider(Qt.Horizontal)
        # Connect widgets to functions
        self.group_motl_select_single.returnPressed.connect(partial(self.select_edit_signal, session))
        self.group_motl_select_slider.valueChanged.connect(partial(self.select_slider_signal, session))
        self.group_motl_select_row_val.returnPressed.connect(partial(self.row_slider_edit))
        self.group_motl_select_row_slider.valueChanged.connect(partial(self.row_slider_signal, session))
        self.group_motl_select_lower_val.returnPressed.connect(partial(self.show_property_edit, True))     # True indicates lower threshold
        self.group_motl_select_lower_slider.valueChanged.connect(partial(self.show_property, session, True))
        self.group_motl_select_upper_val.returnPressed.connect(partial(self.show_property_edit, False))    # False indicates upper threshold
        self.group_motl_select_upper_slider.valueChanged.connect(partial(self.show_property, session, False))
        self.group_motl_select_variable.returnPressed.connect(partial(self.variable_edit, session))
        self.group_motl_select_variable_slider.valueChanged.connect(partial(self.variable_slider, session))
        # Use a grid layout for this group
        self.group_motl_select_layout = QGridLayout()
        self.group_motl_select_layout.setColumnStretch(0, 0.33)
        self.group_motl_select_layout.setColumnStretch(1, 0.2)
        self.group_motl_select_layout.setColumnStretch(2, 1)
        # Add all the widgets
        # First column
        self.group_motl_select_label_select = QLabel("Selected:")
        self.group_motl_select_label_select.setFont(self.font)
        self.group_motl_select_layout.addWidget(self.group_motl_select_label_select, 0, 0)
        self.group_motl_select_label_row = QLabel("Row:")
        self.group_motl_select_label_row.setFont(self.font)
        self.group_motl_select_layout.addWidget(self.group_motl_select_label_row, 1, 0)
        self.group_motl_select_layout.addWidget(self.group_motl_select_lower_name, 2, 0)
        self.group_motl_select_layout.addWidget(self.group_motl_select_upper_name, 3, 0)
        self.group_motl_select_layout.addWidget(self.group_motl_select_colormap_name, 4, 0)
        self.group_motl_select_layout.addWidget(self.group_motl_select_variable_name, 5, 0)
        # Second column
        self.group_motl_select_layout.addWidget(self.group_motl_select_single, 0, 1)
        self.group_motl_select_layout.addWidget(self.group_motl_select_row_val, 1, 1)
        self.group_motl_select_layout.addWidget(self.group_motl_select_lower_val, 2, 1)
        self.group_motl_select_layout.addWidget(self.group_motl_select_upper_val, 3, 1)
        self.group_motl_select_layout.addWidget(self.group_motl_select_colormap_lower, 4, 1)
        self.group_motl_select_layout.addWidget(self.group_motl_select_variable, 5, 1)
        # Third column
        self.group_motl_select_layout.addWidget(self.group_motl_select_slider, 0, 2)
        self.group_motl_select_layout.addWidget(self.group_motl_select_row_slider, 1, 2)
        self.group_motl_select_layout.addWidget(self.group_motl_select_lower_slider, 2, 2)
        self.group_motl_select_layout.addWidget(self.group_motl_select_upper_slider, 3, 2)
        self.group_motl_select_layout.addLayout(self.group_motl_select_colormap, 4, 2)
        self.group_motl_select_layout.addWidget(self.group_motl_select_variable_slider, 5, 2)
        # Set the layout of the group
        self.group_motl_select.setLayout(self.group_motl_select_layout)

        # Add a row of buttons
        self.button_row_1 = QHBoxLayout()
        # Define the buttons
        self.show_button = QPushButton("Show/Hide all")
        self.show_button.setFont(self.font)
        self.close_button = QPushButton("Close Motivelist")
        self.close_button.setFont(self.font)
        self.reset_selected = QPushButton("Reset selected")
        self.reset_selected.setFont(self.font)
        self.reset_all = QPushButton("Reset all")
        self.reset_all.setFont(self.font)
        # Connect buttons to functions -> other buttons connected to functions
        # In main class
        self.reset_selected.clicked.connect(partial(self.reset_selected_pressed, session))
        self.reset_all.clicked.connect(partial(self.reset_all_pressed, session))
        # Add buttons to layout
        self.button_row_1.addWidget(self.show_button)
        self.button_row_1.addWidget(self.close_button)
        self.button_row_1.addWidget(self.reset_selected)
        self.button_row_1.addWidget(self.reset_all)

        # Combine the layouts
        self.layout = QVBoxLayout()
        # self.layout.addWidget(self.group_motl_props)
        self.layout.addWidget(self.group_motl_select)
        self.layout.addLayout(self.button_row_1)

        # Set the layout
        self.tool_window.ui_area.setLayout(self.layout)

        # Show the window on the user-preferred side of the
        # ChimeraX main window
        self.tool_window.manage("left")

# ==============================================================================
# Main Menu Functions ==========================================================
# ==============================================================================

#-------------------------------------------------------------------------------
# Staring with the sliders -----------------------------------------------------
# ------------------------------------------------------------------------------

    # Function that receives the signal from the slider
    def select_slider_signal(self, session):
        if self.execute:
            # Get the currently selected value
            value = self.group_motl_select_slider.value()
            # Set the value in the Line Edit to the left of the slider
            self.group_motl_select_single.setText(str(value))
            # Execute the selection function
            self.select_execute(session, value)


    def select_edit_signal(self, session):
        if self.execute:
            try:
                # Get the value from the text
                value = int(self.group_motl_select_single.text())
                # Set the value in the Slider to the right of the Line Edit
                self.group_motl_select_slider.setValue(value)
                # Execute the selection function
                self.select_execute(session, value)
            except:
                print("Error: Please insert an integer")


    def select_execute(self, session, value):
        if value != 0:  # Select a particle
            # Unselect all particles
            run(session, "select clear")
            # Hide all objects and only show the selected one
            command = "hide "
            for i in range(len(self.motl_instance.motivelist)):
                id = self.motl_instance.motivelist[i][21]
                if "#" in id:
                    command += "{} ".format(id)
                else:
                    command += "#{} ".format(id)
            # Only execute command if motivelist is non-empty
            if command == "hide ":
                print("Nothing to hide.")
            else:
                run(session, command)
            try:
                id  = self.motl_instance.motivelist[value-1][21]
                if "#" in id:
                    run(session, "show {}".format(id))
                    run(session, "select {}".format(id))
                else:
                    run(session, "show #{}".format(id))
                    run(session, "select #{}".format(id))
            except:
                print("No particles to select.")
        else:   # Select all particles
            command_show = "show "
            command_select = "select "
            for i in range(len(self.motl_instance.motivelist)):
                id = self.motl_instance.motivelist[i][21]
                if "#" in id:
                    command_show += "{} ".format(id)
                    command_select += "{}".format(id)
                else:
                    command_show += "#{} ".format(id)
                    command_select += "#{}".format(id)
            # Only execute commands if motivelist is non-empty
            if command_show == "show ":
                print("Nothing to show.")
                print("Nothing to select.")
            else:
                run(session, command_show)
                run(session, command_select)


    # Function that receives signal from the row slider
    def row_slider_signal(self, session):
        if self.execute:
            # Get the currently selected value
            value = int(self.group_motl_select_row_slider.value())
            # Set the value in the QLineEdit
            self.group_motl_select_row_val.setText(str(value))
            # Execute the row selection
            self.row_slider_execute(session, value)


    def row_slider_edit(self):
        if self.execute:
            try:
                # Get the inserted value of the QLinEdit
                value = int(self.group_motl_select_row_val.text())
                # Set the value in the QSlider
                self.group_motl_select_row_slider.setValue(value)
                # Execute the row selection
                self.row_slider_execute(session, value)
            except:
                print("Error: Please insert an integer")


    def row_slider_execute(self, session, row):
        if row != 0:  # Build the sliders for this row
            self.row_selected = row - 1

            # Build the other sliders
            self.slider_options(row)

            # Set the colors depending on the row value
            self.set_colors(session, row)

        else: # Reset all slider options and color are objects blue
            for i in range(len(self.motl_instance.motivelist)):
                id = self.motl_instance.motivelist[i][21]
                if "#" in id:
                    run(session, "color {} 0,100,100".format(id))
                else:
                    run(session, "color #{} 0,100,100".format(id))

            # Update the variable silders
            self.group_motl_select_lower_slider.setMinimum(0)
            self.group_motl_select_lower_slider.setMaximum(1)
            self.group_motl_select_lower_slider.setValue(0)
            self.group_motl_select_lower_val.setText("")
            self.group_motl_select_upper_slider.setMinimum(0)
            self.group_motl_select_upper_slider.setMaximum(1)
            self.group_motl_select_upper_slider.setValue(1)
            self.group_motl_select_upper_val.setText("")

            # Update the colormap
            self.group_motl_select_colormap_lower.setText("")
            self.group_motl_select_colormap_upper.setText("")


    # Show all objects that show values between the thresholds of the
    # corresponding row in the motive list
    # Receives signal from the sliders
    def show_property(self, session, threshold):
        if self.execute:
            # Get the values from the sliders
            min_val = float(self.group_motl_select_lower_slider.value())
            max_val = float(self.group_motl_select_upper_slider.value())

            # If the cross-correlation is selected divide the values by 100
            if self.row_selected == 0:
                min_val /= 100
                max_val /= 100

            # Send the value to the corresponding QLineEdit
            self.group_motl_select_lower_val.setText(str(min_val))
            self.group_motl_select_upper_val.setText(str(max_val))

            # Execute the show property
            self.show_property_execute(session, threshold, min_val, max_val)


    def show_property_edit(self, session, threshold):
        if self.execute:
            # Get the values from the QLineEdits
            min_val = float(self.group_motl_select_lower_val.text())
            max_val = float(self.group_motl_select_upper_val.text())

            # If the cross-correlation is selected divide the values by 100
            if self.row_selected == 0:
                min_val /= 100
                max_val /= 100

            # Pass the values to the sliders
            self.group_motl_select_lower_slider.setValue(min_val)
            self.group_motl_select_upper_slider.setValue(max_val)

            # Execute the show property
            self.show_property_execute(session, threshold, min_val, max_val)


    def show_property_execute(self, session, threshold, min_val, max_val):
        # Only show objects between the thresholds
        command_show = "show "
        command_hide = "hide "
        for i in range(len(self.motl_instance.motivelist)):
            value = self.motl_instance.motivelist[i][self.row_selected]
            id = self.motl_instance.motivelist[i][21]
            if value >= min_val and value <= max_val:
                if "#" in id:
                    command_show += "{} ".format(id)
                else:
                    command_show += "#{} ".format(id)
            else:
                if "#" in id:
                    command_hide += "{} ".format(id)
                else:
                    command_hide += "#{} ".format(id)

        if command_hide == "hide ":
            print("Nothing to hide.")
        else:
            run(session, command_hide)
        if command_show == "show ":
            print("Nothing to show.")
        else:
            run(session, command_show)


    def variable_slider(self, session):
        if self.execute:
            if self.variable_switch:    # Radius Slider
                # Get the value from the QSlider
                value = self.group_motl_select_variable_slider.value()
                # Set the value in the QLineEdit
                self.group_motl_select_variable.setText(str(value/10))

                print("We're in the radius slider now.")

                # Only execute if the motivelist is non-empt
                if len(self.motl_instance.motivelist) == 0:
                    print("No atoms to change radius. (Slider)")
                else:
                    command = "marker change "
                    for i in range(len(self.motl_instance.motivelist)):
                        id = self.motl_instance.motivelist[i][21]
                        command += "{} ".format(id)
                    command += "radius {}".format(value/10)
                    run(session, command)
            else:   # Surface slider
                # Get the value from the QSlider
                value = self.group_motl_select_variable_slider.value()
                # Set the value in the QLineEdit
                self.group_motl_select_variable.setText(str(value/100))

                # Change the surface level in all objects of the motl instance
                for i in range(len(self.motl_instance.motivelist)):
                    id = self.motl_instance.motivelist[i][21]
                    run(session, "volume #{} level {}".format(id, value/100))


    def variable_edit(self, session):
        if self.execute:
            if self.variable_switch:    # Radius Edit
                # Get the value from the QSlider
                try:
                    value = float(self.group_motl_select_variable.text())
                    # Set the value in the QLineEdit
                    self.group_motl_select_variable_slider.setValue(value*10)

                    print("We're in the radius edit now.")

                    # Only execute if the motivelist in non-empty
                    if len(self.motl_instance.motivelist) == 0:
                        print("No atoms to change radius. (Edit)")
                    else:
                        command = "marker change "
                        for i in range(len(self.motl_instance.motivelist)):
                            id = self.motl_instance.motivelist[i][21]
                            command += "{} ".format(id)
                        command += "radius {}".format(value)
                        run(session, command)
                except:
                    print("Please enter a float number as the radius.")
            else:   # Surface Edit
                # Get the value from the QLineEdit
                value = float(self.group_motl_select_variable.text())
                # Set the value in the slider
                self.group_motl_select_variable_slider.setValue(value*100)

                # Change the surface level in all objects of the motl instance
                for i in range(len(self.motl_instance.motivelist)):
                    id = self.motl_instance.motivelist[i][21]
                    run(session, "volume #{} level {}".format(id, value))


# ------------------------------------------------------------------------------
# And other functions ----------------------------------------------------------
# ------------------------------------------------------------------------------


    # Either show or hide all associated objects
    def show_button_pressed(self, session):
        if self.show:
            # Hide all objects
            command = "hide "
            for i in range(len(self.motl_instance.motivelist)):
                id = self.motl_instance.motivelist[i][21]
                if "#" in id:
                    command += "{} ".format(id)
                else:
                    command += "#{} ".format(id)
            # Only hide if the motivelist is non-empty
            if command == "hide ":
                print("Nothing to hide.")
            else:
                run(session, command)

            # Next time show all
            self.show = False
        else:
            # Show all objects
            command = "show "
            for i in range(len(self.motl_instance.motivelist)):
                id = self.motl_instance.motivelist[i][21]
                if "#" in id:
                    command += "{} ".format(id)
                else:
                    command += "#{} ".format(id)
            # Only show if the motivelist is non-empty
            if command == "show ":
                print("Nothing to show.")
            else:
                run(session, command)

            # Next time hide all
            self.show = True


    # The close button resets the groups and unselects all objects
    # Since the function is called from the main class, here we only
    # Reset the groups
    def close_button_pressed(self):
        # Reset might also be called from elsewhere
        # So I'll just stick with calling this function
        self.execute = False
        self.reset()


    def reset_selected_pressed(self, session):
        # In case more than one ID is selected get all IDs and check
        # If all belong to the motivelist
        ids = []
        for model in session.selection.models():
            try:
                id = int(model.id_string)
                # This is funny because in fact we need the id as a string
                ids.append(str(id))
            except:
                continue

        # For the sake of simplicity create a new list that only contains all IDs
        id_list = [i[21] for i in self.motl_instance.motivelist]

        for id in ids:
            if id in id_list:
                # Get corresponding index of id
                index = id_list.index(id)
                # Read angles and position from motivelist
                x_coord = self.motl_instance.motivelist[index][7]
                y_coord = self.motl_instance.motivelist[index][8]
                z_coord = self.motl_instance.motivelist[index][9]
                phi = self.motl_instance.motivelist[index][16]
                psi = self.motl_instance.motivelist[index][17]
                theta = self.motl_instance.motivelist[index][18]
                # Generate the rotation matrix
                rot_mat = detRotMat(phi, psi, theta)
                # Append position to rotation matrix
                rot_mat[0].append(x_coord)
                rot_mat[1].append(y_coord)
                rot_mat[2].append(z_coord)
                if "#" in id:
                    command = "marker change {} position {},{},{}".format(id, x_coord, y_coord, z_coord)
                    run(session, command)
                else:
                    # Reset position of object with current id
                    command = "view matrix models #{}".format(id)
                    for i in range(3):
                        for j in range(4):
                            command += ",{}".format(rot_mat[i][j])

                    run(session, command)
            else:
                print("Error: Selected ID", id, "is not part of the motivelist")


    def reset_all_pressed(self, session):
        # Only execute if the motivelist  is non-empty
        if len(self.motl_instance.motivelist) == 0:
            print("Nothing to reset.")
        else:
            # Reset all objects to initial location and rotation
            for k in range(len(self.motl_instance.motivelist)):
                # Read angles and position from motivelist
                x_coord = self.motl_instance.motivelist[k][7]
                y_coord = self.motl_instance.motivelist[k][8]
                z_coord = self.motl_instance.motivelist[k][9]
                phi = self.motl_instance.motivelist[k][16]
                psi = self.motl_instance.motivelist[k][17]
                theta = self.motl_instance.motivelist[k][18]
                id = self.motl_instance.motivelist[k][21]
                # Generate the rotation matrix
                rot_mat = detRotMat(phi, psi, theta)
                # Append position to rotation matrix
                rot_mat[0].append(x_coord)
                rot_mat[1].append(y_coord)
                rot_mat[2].append(z_coord)

                # Reset position of object with current id
                if "#" in id:
                    run(session, "marker change {} position {},{},{}".format(id, x_coord, y_coord, z_coord))
                else:
                    command = "view matrix models #{}".format(id)
                    for i in range(3):
                        for j in range(4):
                            command += ",{}".format(rot_mat[i][j])

                    run(session, command)


# ==============================================================================
# Other Fuctions ===============================================================
# ==============================================================================

    # Function that sets the local variables
    def set_variables(self):
        self.show = False
        self.row_selected = 1

    # Gets the motl instance as a variable and build the property group
    def build_properties(self, motl_instance):
        self.motl_instance = motl_instance

        # Update the motl props group
        # self.group_motl_props_name.setText(motl_instance.name)
        # self.group_motl_props_obj_name.setText(motl_instance.obj_name)
        self.group_motl_props_number_particles.setText(str(len(motl_instance.motivelist)))
        # Update the select group
        self.group_motl_select_single.setText("")
        self.group_motl_select_row_val.setText("")


    # The reset function resets all entries ni case a motivelist is closed
    def reset(self):
        # Update the motl props group
        self.group_motl_props_name.setText("")
        self.group_motl_props_obj_name.setText("")
        self.group_motl_props_number_particles.setText("")
        # Update the motl selection group
        self.group_motl_select_slider.setMaximum(1)
        self.group_motl_select_slider.setValue(1)
        self.group_motl_select_single.setText("")
        self.group_motl_select_row_slider.setMaximum(20)
        self.group_motl_select_row_val.setText("")

        # Update the variable silders
        self.group_motl_select_lower_slider.setMinimum(0)
        self.group_motl_select_lower_slider.setMaximum(1)
        self.group_motl_select_lower_slider.setValue(0)
        self.group_motl_select_lower_val.setText("")
        self.group_motl_select_upper_slider.setMinimum(0)
        self.group_motl_select_upper_slider.setMaximum(1)
        self.group_motl_select_upper_slider.setValue(1)
        self.group_motl_select_upper_val.setText("")

        # Update the colormap
        self.group_motl_select_colormap_lower.setText("")
        self.group_motl_select_colormap_upper.setText("")

        # Update the surface level
        self.group_motl_select_variable_slider.setMinimum(0)
        self.group_motl_select_variable_slider.setMaximum(1)
        self.group_motl_select_variable_slider.setValue(0)
        self.group_motl_select_variable.setText("")
        # self.group_motl_select_variable_name.setText("Surface Level")

        # Update the title of the group
        self.group_motl_select.setTitle("Selection")

        # Also 'delete' the selected motl instance
        self.motl_instance = None


    # Function that set minimum and maximum for slider
    def build_slider(self, session):
        # Select slider
        self.group_motl_select_slider.setMinimum(0) # Particle 0 means all particles are selected
        self.group_motl_select_slider.setMaximum(len(self.motl_instance.motivelist))
        self.group_motl_select_slider.setValue(0)
        self.group_motl_select_single.setText("0")

        # row slider
        self.group_motl_select_row_slider.setMinimum(0)         # Minimal row is always 0 -> Row 0 means no row selected
        self.group_motl_select_row_slider.setMaximum(20)        # Maximal row is always 20
        self.group_motl_select_row_slider.setValue(0)
        self.group_motl_select_row_val.setText("0")

        # If an object is loaded for the motivelist, add the surface slider
        # If no object is loaded, add the radius slider
        if self.motl_instance.obj_name == None:     # Add radius slider
            self.variable_switch = True     # Build the radius slider

            self.group_motl_select_variable_slider.setMinimum(1)
            self.group_motl_select_variable_slider.setMaximum(300)
            self.group_motl_select_variable_slider.setValue(40)     # The default radius is 4

            # Set the name of the label
            self.group_motl_select_variable_name.setText("Radius")
        else:                                       # Add the surface slider
            self.variable_switch = False    # Build the surface slider

            self.group_motl_select_variable_slider.setMinimum(ma.floor(100*self.motl_instance.surface_obj_min))
            self.group_motl_select_variable_slider.setMaximum(ma.ceil(100*self.motl_instance.surface_obj_max))
            self.group_motl_select_variable_slider.setValue(100*self.motl_instance.surface_obj_current)

            # Set the name of the label
            self.group_motl_select_variable_name.setText("Surface level")


    # Function that sets slider properties depended on selected row (of motivelist)
    def slider_options(self, row):
        # The variable row is the selected row of the motivelist
        # Define a list with all the elements from the selected row
        val_list = []
        for i in range(len(self.motl_instance.motivelist)):
            val_list = [s[row-1] for s in self.motl_instance.motivelist]
        # Get minimal, maximal value and the step width for a certain number of steps
        if row == 1:    # If cross-correlation multiply by 100
            min_val = 100*min(val_list)
            max_val = 100*max(val_list)
            number_steps = 100
            step_width = (max_val - min_val)/number_steps
        else:
            min_val = min(val_list)
            max_val = max(val_list)
            number_steps = 100
            step_width = (max_val - min_val)/number_steps

        # Set minimal, maximal and step width
        self.group_motl_select_lower_slider.setSingleStep(step_width)
        self.group_motl_select_lower_slider.setMinimum(ma.floor(min_val))
        self.group_motl_select_lower_slider.setMaximum(ma.ceil(max_val))
        self.group_motl_select_upper_slider.setSingleStep(step_width)
        self.group_motl_select_upper_slider.setMinimum(ma.floor(min_val))
        self.group_motl_select_upper_slider.setMaximum(ma.ceil(max_val))

        # Set the default positions of the sliders
        self.group_motl_select_lower_slider.setValue(ma.floor(min_val))
        self.group_motl_select_upper_slider.setValue(ma.ceil(max_val))

        # Also set maximal and minimal value to the colormap
        self.group_motl_select_colormap_lower.setText(str(ma.floor(min_val)))
        self.group_motl_select_colormap_upper.setText(str(ma.ceil(max_val)))


    def set_colors(self, session, row):
        # Get minimal and maximal value of the selected row
        val_list = []
        for i in range(len(self.motl_instance.motivelist)):
            val_list = [s[row-1] for s in self.motl_instance.motivelist]
        min_val = min(val_list)
        max_val = max(val_list)
        center = (max_val+min_val)/2
        command = ""    # Just for initialization

        # Now get an entry from the val_list and translate it to a color
        for i in range(len(val_list)):
            value = val_list[i]
            if value < center:
                relative_position = (value - min_val)/(center - min_val)
                colors = [100, relative_position*100, 0]
                id = self.motl_instance.motivelist[i][21]
                if "#" in id:
                    command = "color {} {},{},{}".format(id, colors[0], colors[1], colors[2])
                else:
                    command = "color #{} {},{},{}".format(id, colors[0], colors[1], colors[2])
            elif value == center:
                id = self.motl_instance.motivelist[i][21]
                if "#" in id:
                    command = "color {} 100,100,0".format(id)
                else:
                    command = "color #{} 100,100,0".format(id)
            elif value > center:
                relative_position = (value - center)/(max_val - center)
                colors = [100 - relative_position*100, 100 - relative_position*50, 0]
                id = self.motl_instance.motivelist[i][21]
                if "#" in id:
                    command = "color {} {},{},{}".format(id, colors[0], colors[1], colors[2])
                else:
                    command = "color #{} {},{},{}".format(id, colors[0], colors[1], colors[2])

            run(session, command)


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
