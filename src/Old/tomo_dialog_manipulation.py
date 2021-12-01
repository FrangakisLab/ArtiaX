from functools import partial
from chimerax.core.commands import run, Command
from chimerax.core.tools import ToolInstance
from chimerax.map.volume import volume_from_grid_data
from chimerax.map_data import ArrayGridData
from chimerax.map import Volume
from chimerax import atomic
from chimerax.geometry.matrix import euler_angles
from chimerax.markers import MarkerSet, selected_markers
import os as os
import math as ma
import mrcfile
# from cp import cp_motive
# from convert import convert
import numpy as np
from .emwrite import emwrite
from .emread import emread
from .euler_rotation import detRotMat, detInvRotMat, mulMatMat, mulVecMat, getEulerAngles, updateCoordinateSystem, rotateArray

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette
# from PyQt5.QtGui import QAbstractItemView
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QComboBox,
    QDesktopWidget,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
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

class Manipulation(ToolInstance):
    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = True         # We do save/restore in sessions
    help = "help:user/tools/tutorial.html"
                            # Let ChimeraX know about our help page

# ==============================================================================
# Instance Initialization ======================================================
# ==============================================================================


    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)

        self.display_name = "Manipulation options of selected motivelist"

        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self)

        # We will be adding an item to the tool's context menu, so override
        # the default MainToolWindow fill context menu method
        self.tool_window.fill_context_menu = self.fill_context_menu

        # Set the font
        self.font = QFont("Arial", 7)

        # Our user interface is simple enough that we could probably inline
        # the code right here, but for any kind of even moderately complex
        # interface, it is probablt better to put the code in a method so
        # that this __init__ method remains readable.
        self._build_ui(session)

        # Initialize the motls_instance variable
        self.mots_instance = None


# ==============================================================================
# Build Main Menu ==============================================================
# ==============================================================================

    def _build_ui(self, session):
        # At first just implement some simple buttons
        self.update_button = QPushButton("Update Motivelist")
        self.update_button.setFont(self.font)
        self.marker_button = QPushButton("Add Markers to Motl.")
        self.marker_button.setFont(self.font)
        self.color_button = QPushButton("Print Motivelist to Log")#"Motivelist Color")
        self.color_button.setFont(self.font)
        self.delete_button = QPushButton("Delete selected Obj.")
        self.delete_button.setFont(self.font)
        self.obj_filename_label = QLabel("Filename of Motivelist:")
        self.obj_filename_label.setFont(self.font)
        self.obj_filename_edit = QLineEdit("")
        self.obj_filename_edit.setFont(self.font)
        self.obj_filename_button = QPushButton("Browse")
        self.obj_filename_button.setFont(self.font)
        # Connect buttons to functions -> The rest is connected to a function
        # In the main window class
        # self.marker_button.clicked.connect(partial(self.add_marker_button_pressed, session))
        # Add the buttons to the layout
        self.first_button_row = QHBoxLayout()
        self.first_button_row.addWidget(self.update_button)
        self.first_button_row.addWidget(self.marker_button)
        self.first_button_row.addWidget(self.color_button)
        self.first_button_row.addWidget(self.delete_button)

        self.second_row = QHBoxLayout()
        self.second_row.addWidget(self.obj_filename_label)
        self.second_row.addWidget(self.obj_filename_edit)
        self.second_row.addWidget(self.obj_filename_button)
        self.second_row.setStretch(0, 0.2)
        self.second_row.setStretch(1, 0.6)
        self.second_row.setStretch(2, 0.2)

        self.layout = QVBoxLayout()
        self.layout.addLayout(self.first_button_row)
        self.layout.addLayout(self.second_row)


        # Set the layout
        self.tool_window.ui_area.setLayout(self.layout)

        # Show the window on the user-preferred side of the
        # ChimeraX main window
        self.tool_window.manage("left")


# ==============================================================================
# Main Menu Functions ==========================================================
# ==============================================================================

    def update_button_pressed(self, session):
        # This button only works if a motl from the table is selected
        if self.motl_instance == None:
            print("Error: Please select a motivelist from the table")
        else:
            # Update the selected motivelist
            volumes = [v for v in session.models.list()]

            # Define the ID list
            id_list = [s[21] for s in self.motl_instance.motivelist]

            # Now finally update the motive list
            for v in volumes:
                print("This is the current ID:", v.id_string)
                try:
                    id = int(v.id_string)
                    # Get position in motivelist of the corresponding volume
                    index = id_list.index(str(id))

                    position_matrix = v.position.matrix

                    x_coord = position_matrix[0][3]
                    y_coord = position_matrix[1][3]
                    z_coord = position_matrix[2][3]
                    # Also get the angles
                    phi, theta, psi = getEulerAngles(position_matrix)

                    # And finally update the motivelist
                    self.motl_instance.motivelist[index][7] = x_coord
                    self.motl_instance.motivelist[index][8] = y_coord
                    self.motl_instance.motivelist[index][9] = z_coord
                    self.motl_instance.motivelist[index][16] = phi
                    self.motl_instance.motivelist[index][17] = psi
                    self.motl_instance.motivelist[index][18] = theta

                    print("Updated object with ID:", id)
                except:
                    # continue
                    print("Skipped object with ID:", id)

            print("Motivelist {} updated".format(self.motl_instance.name))


    def color_button_pressed(self, session):
        print("This is the motivelist:")
        for particle in self.motl_instance.motivelist:
            print(particle)
        print("There are", len(self.motl_instance.motivelist), "particles.")


    # Function that deletes the selected particle from the motivelist
    def delete_button_pressed(self, session):
        # Get the selected objects
        objs = session.selection.models()
        markers = selected_markers(session)

        # Define the ID list
        id_list = [s[21] for s in self.motl_instance.motivelist]
        volume_list = [s[20] for s in self.motl_instance.motivelist]

        # Markers are treated different from objects
        # So separate marker IDs from object IDs
        marker_ids = []
        marker_id = 0

        for marker in markers:
            print(marker)
            # Get the index in the motivelist
            index = volume_list.index(marker)

            # With the index get the marker id
            marker_id = self.motl_instance.motivelist[index][21][1]
            marker_ids.append(marker_id)

            # Close the marker
            run(session, "del {}".format(self.motl_instance.motivelist[index][21]))

            # Also remove it from the motivelist
            self.motl_instance.motivelist.remove(self.motl_instance.motivelist[index])
        for object in objs:
            try:
                # Get the ID
                id = int(object.id_string)

                if id not in marker_ids:
                    # And the corresponding index in the motivelist
                    index = id_list.index(id)

                    # Remove ID and corresponding column in motivelist
                    self.motl_instance.motivelist.remove(self.motl_instance.motivelist[index])

                    # Finally close the volume
                    print("Do we run?")
                    run(session, "close #{}".format(id))
            except:
                continue


# ==============================================================================
# Other Functions ==============================================================
# ==============================================================================

    # Function that sets the local motl_instance variable
    # Function is called when clicking on the corresponding row in the motl table
    def select_motl_instance(self, motl_instance):
        self.motl_instance = motl_instance


    # Function that sets the motls_instance variable to default
    # Function is called when clicking on the corresponding row in the motl table
    def unselect_motl_instance(self):
        self.motl_instance = None


    # This function returns the smallest unused ID
    def get_unused_id(self, session):
        # Load the list of open models
        obj_list = session.models.list()
        id_list = []    # List of all used IDs (int)

        for object in obj_list:
            try:
                current_id = int(object.id_string)
                id_list.append(current_id)
            except:
                continue

        # Find the lowest unused ID
        id_counter = 1
        while id_counter in id_list:
            id_counter += 1

        return id_counter



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
