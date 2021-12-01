# vim: set expandtab shiftwidth=4 softtabstop=4:

# === UCSF ChimeraX Copyright ===
# Copyright 2016 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  For details see:
# http://www.rbvi.ucsf.edu/chimerax/docs/licensing.html
# This notice must be embedded in or attached to all copies,
# including partial copies, of the software or any revisions
# or derivations thereof.
# === UCSF ChimeraX Copyright ===

from functools import partial
from chimerax.core.commands import run, Command
from chimerax.core.tools import ToolInstance
from chimerax.map.volume import volume_from_grid_data
from chimerax.map_data import ArrayGridData
from chimerax.map import Volume
from chimerax import atomic
from chimerax.markers import MarkerSet, selected_markers
import os as os
import math as ma
import mrcfile
import time
# from cp import cp_motive
# from convert import convert
import numpy as np
from .emwrite import emwrite
from .emread import emread
from .euler_rotation import detRotMat, detInvRotMat, mulMatMat, mulVecMat, getEulerAngles, updateCoordinateSystem, rotateArray

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QKeySequence
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
    QShortcut,
    QTableWidget,
    QTableWidgetItem,
    QTableView,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget
)

# Get current working directory
cwd = os.getcwd()

class Tomo_Dialogue(ToolInstance):

    # Inheriting from ToolInstance makes us known to the ChimeraX tool manager,
    # so we can be notified and take appropiate action when sessions are closed,
    # save, or restored, and we will be listed among running tools and so on.

    # If cleaning up is needed on finish, override the 'delete' method
    # but be sure to call 'delete' from the superclass at the end

    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = True         # We do save/restore in sessions
    help = "help:user/tools/tutorial.html"
                                # Let ChimeraX know about our help page

# ==============================================================================
# Instance Initialization ======================================================
# ==============================================================================


    def __init__(self, session, tool_name):
        # 'session'     - chimerax.core.session.Session instance
        # 'tool_name'   - string

        # Initialize base class
        super().__init__(session, tool_name)

        # Set name displayed on title bar (defaults to tool_name)
        # Must be after the superclass init, which would override it.
        self.display_name = "GUI Tomo Bundle"

        # Set the font
        self.font = QFont("Arial", 7)

        # Create the main window for our tool. The window object will have
        # a 'ui_area' where we place the widgets composing our interface.
        # The window isn't shown until we call its 'manage' method.

        # Note that by default, tool windows are only hidden rather than
        # destroyed when the user clicks the window's close button. To change
        # this behaviou, specify 'close_destroy=True' in the MainToolWindow
        # constructor
        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self)

        # We will be adding an item to the tool's context menu, so override
        # the default MainToolWindow fill context menu method
        self.tool_window.fill_context_menu = self.fill_context_menu

        # Our user interface is simple enough that we could probably inline
        # the code right here, but for any kind of even moderately complex
        # interface, it is probablt better to put the code in a method so
        # that this __init__ method remains readable.
        self._build_ui(session)

        # Also show the other windows
        from .tomo_dialog_visualization import Visualization
        self.visualization = Visualization(session, tool_name)
        from .tomo_dialog_manipulation import Manipulation
        self.manipulation = Manipulation(session, tool_name)

        # Connect functions to those windows
        self._connect_visualization(session)
        self._connect_manipulation(session)


# ==============================================================================
# Interface construction =======================================================
# ==============================================================================

    def _build_ui(self, session):

        # Create a file dialog to browse through in order to open tomogram/motl
        self.file_dialog_open = QFileDialog()
        self.file_dialog_open.setFileMode(QFileDialog.AnyFile)
        self.file_dialog_open.setNameFilters(["EM Files (*.em)", "MRC Files (*.mrc)"])
        self.file_dialog_save = QFileDialog()
        self.file_dialog_save.setFileMode(QFileDialog.AnyFile)
        self.file_dialog_save.setNameFilters(["EM Files (*.em)"])
        self.file_dialog_save.setAcceptMode(QFileDialog.AcceptSave)

        # Set up some local variables
        self.set_variables()

        # Prepare some widgets that are used later
        self.prepare_tables(session)

        # Build the menu bar
        self.build_menubar(session)

        # Prepare main window widgets
        self.build_main_ui(session)

        # Define some shortcuts
        self.define_shortcuts(session)

        # Add the menu bar
        self.layout_row_1 = QHBoxLayout()
        self.layout_row_1.addWidget(self.menuBar)
        # Merge all box layouts
        layout = QVBoxLayout()
        layout.addLayout(self.layout_row_1)
        layout.addLayout(self.layout_row_2)
        layout.addLayout(self.layout_row_3)

        # Set the layout
        self.tool_window.ui_area.setLayout(layout)

        # Show the window on the user-preferred side of the
        # ChimeraX main window
        self.tool_window.manage("left")

# ==============================================================================
# Functions to have a better overview of the GUI ===============================
# ==============================================================================

    def build_menubar(self, session):
        # A dropdown menu for the menu bar
        self.menu_bar = QToolButton()
        self.menu_bar.setPopupMode(QToolButton.MenuButtonPopup)
        # Define all the buttons and connect them to corresponding function
        self.menu_bar_open_tomogram = QAction("Open Tomogram")
        self.menu_bar_open_tomogram.triggered.connect(partial(self.open_tomogram_pressed, session))
        self.menu_bar_create_motl = QAction("Create Motivelist")
        self.menu_bar_create_motl.triggered.connect(partial(self.create_motl_pressed, session))
        self.menu_bar_load_motl = QAction("Load Motivelist")
        self.menu_bar_load_motl.triggered.connect(partial(self.load_motl_pressed, session))
        # self.menu_bar_load_motl_as_obj = QAction("Load Motl. as Obj.")
        # self.menu_bar_load_motl_as_obj.triggered.connect(partial(self.load_motl_as_obj_pressed, session))
        self.menu_bar_save_motl = QAction("Save Motivelist")
        self.menu_bar_save_motl.triggered.connect(partial(self.save_motl_menu_pressed, session))
        self.menu_bar_save_markers = QAction("Save Selected Markers")
        self.menu_bar_save_markers.triggered.connect(partial(self.save_marker_menu_pressed, session))
        self.menu_bar_save_session_log = QAction("Save Session Log")
        self.menu_bar_save_session_log.triggered.connect(partial(self.save_session_log_pressed, session))
        # Prepare the file menu
        self.menu = QMenu("&File")
        self.menu.addAction(self.menu_bar_open_tomogram)
        self.menu.addSeparator()
        self.menu.addAction(self.menu_bar_create_motl)
        self.menu.addAction(self.menu_bar_load_motl)
        # self.menu.addAction(self.menu_bar_load_motl_as_obj)
        self.menu.addSeparator()
        self.menu.addAction(self.menu_bar_save_motl)
        self.menu.addAction(self.menu_bar_save_markers)
        self.menu.addAction(self.menu_bar_save_session_log)
        # Add to the actual menu
        self.menuBar = QMenuBar()
        self.menuBar.addMenu(self.menu)


    def build_main_ui(self, session):
        # Design the main window
        # The plan is to have three layouts vertically
        # Consisting of a couple of widgets each

        # Row 1 is not condidered here as this is the menu bar
        # which is prepared in a different function

        # Prepare row 2
        self.layout_row_2_column_1 = QVBoxLayout()
        self.tomo_label = QLabel("Tomograms/Images")
        self.tomo_label.setFont(self.font)
        self.layout_row_2_column_1.addWidget(self.tomo_label)
        self.layout_row_2_column_1.addWidget(self.table_1)      # Table has already been prepared before
        self.close_tomogram = QPushButton("Close Tomogram")
        self.close_tomogram.setFont(self.font)
        self.close_tomogram.clicked.connect(partial(self.close_tomogram_pressed, session))
        self.layout_row_2_column_1.addWidget(self.close_tomogram)

        self.layout_row_2_column_2 = QVBoxLayout()
        self.tomo_show_hide = QPushButton("Show/Hide")
        self.tomo_show_hide.setFont(self.font)
        self.tomo_show_hide.clicked.connect(partial(self.tomo_show_hide_pressed, session))
        self.layout_row_2_column_2.addWidget(self.tomo_show_hide)
        self.process_tomograms = QPushButton("Process Tomograms")
        self.process_tomograms.setFont(self.font)
        self.process_tomograms.clicked.connect(partial(self.process_tomograms_pressed, session))
        # self.layout_row_2_column_2.addWidget(self.process_tomograms)
        self.tomo_reset = QPushButton("Tomo Reset")
        self.tomo_reset.setFont(self.font)
        self.tomo_reset.clicked.connect(partial(self.tomo_reset_pressed, session))
        self.layout_row_2_column_2.addWidget(self.tomo_reset)
        # Merge this row to one HBox Layout
        self.layout_row_2 = QHBoxLayout()
        self.layout_row_2.addLayout(self.layout_row_2_column_1)
        self.layout_row_2.addLayout(self.layout_row_2_column_2)

        # Prepare row 3
        self.layout_row_3_column_1 = QVBoxLayout()
        self.motivelist_label = QLabel("Motivelists")
        self.motivelist_label.setFont(self.font)
        self.layout_row_3_column_1.addWidget(self.motivelist_label)
        self.layout_row_3_column_1.addWidget(self.table_2)      # Table has already been prepared before
        self.close_motls = QPushButton("Close Motivelists")
        self.close_motls.setFont(self.font)
        self.close_motls.clicked.connect(partial(self.close_motls_pressed, session))
        self.layout_row_3_column_1.addWidget(self.close_motls)

        self.layout_row_3 = QHBoxLayout()
        self.layout_row_3.addLayout(self.layout_row_3_column_1)
        # self.layout_row_3.addLayout(self.layout_row_3_column_2)

    def prepare_tables(self, session):
        # Prepare some initial widgets
        # A display table for the tomograms
        self.table_1 = QTableWidget()
        self.table_1.setFont(self.font)
        # self.table_1.setSelectionBehavior(QTableView.SelectRows)
        self.table_1.setRowCount(0)
        self.table_1.setColumnCount(3)
        self.header_1 = self.table_1.horizontalHeader()
        self.header_1.setSectionResizeMode(0, QHeaderView.Stretch)
        self.header_1.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.header_1.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_1.setHorizontalHeaderLabels(["Name", "Show", "Select"])
        # What happens if click
        self.table_1.itemClicked.connect(partial(self.table_clicked, session, 1))
        # We also need a counter for this table
        self.counter_1 = 0

        # A display table for the motivelists
        self.table_2 = QTableWidget()
        self.table_2.setFont(self.font)
        # self.table_2.setSelectionBehavior(QTableView.SelectRows)
        self.table_2.setRowCount(0)
        self.table_2.setColumnCount(4)
        self.header_2 = self.table_2.horizontalHeader()
        self.header_2.setSectionResizeMode(0, QHeaderView.Stretch)
        self.header_2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.header_2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.header_2.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_2.setHorizontalHeaderLabels(["Name", "Object", "Show", "Select"])
        # What happens if click
        self.table_2.itemClicked.connect(partial(self.table_clicked, session, 2))
        # A counter for this table would be nice
        self.counter_2 = 0


    def define_shortcuts(self, session):
        # Define some labels
        self.jump_1_forwards_label = QLabel("")
        self.jump_10_forwards_label = QLabel("")
        self.jump_1_backwards_label = QLabel("")
        self.jump_10_backwards_label = QLabel("")
        # Define the shortcuts
        self.jump_1_forwards = QShortcut(QKeySequence(Qt.Key_F4), self.jump_1_forwards_label)
        self.jump_10_forwards = QShortcut(QKeySequence(Qt.Key_F8), self.jump_10_forwards_label)
        self.jump_1_backwards = QShortcut(QKeySequence(Qt.Key_F3), self.jump_1_backwards_label)
        self.jump_10_backwards = QShortcut(QKeySequence(Qt.Key_F7), self.jump_10_backwards_label)
        # Connect actions to functions
        self.jump_1_forwards.activated.connect(partial(self.jump_1_forwards_pressed, session))
        self.jump_10_forwards.activated.connect(partial(self.jump_10_forwards_pressed, session))
        self.jump_1_backwards.activated.connect(partial(self.jump_1_backwards_pressed, session))
        self.jump_10_backwards.activated.connect(partial(self.jump_10_backwards_pressed, session))


# ==============================================================================
# Menu Functions ===============================================================
# ==============================================================================

    def open_tomogram_pressed(self, session):
        # When this button is clicked we need an empty filename
        self.tomo_filename = None

        # Activate the selector
        self.select = self.file_dialog_open.exec()
        # Get the clicked directory
        if self.select:
            self.tomo_filename = self.file_dialog_open.selectedFiles()

        if self.tomo_filename == None:  # If selecting is cancelled
            print("No tomogram selected.")
        else:
            run(session, "open {}".format(self.tomo_filename[0]))

            # Unable the capFaces
            # Get the volume ID
            volumes = session.models.list()
            id_list = []
            for volume in volumes:
                try:
                    id_list.append(int(volume.id_string))
                    print(id_list)
                    volume_interest = volume
                except:
                    continue

            run(session, "volume #{} capFaces false".format(id_list[-1]))
            # Also get the dimensions
            volumes = [v for v in session.models.list() if isinstance(v, Volume)]
            dimensions = volumes[0].data.size


            # Get file name
            tomo_filename = os.path.basename(self.tomo_filename[0])

            row = self.table_1.rowCount()
            # Create a tomogram instance and add to the list of tomograms
            from .object_settings import TomoSettings
            tomo_instance = TomoSettings(tomo_filename, row)
            self.tomo_list.append(tomo_instance)
            self.tomo_list[-1].set_tomo_filepath(self.tomo_filename[0])

            # Set the dimensions of the tomogram
            tomo_instance.set_dimensions(dimensions)

            # Add ChimeraX tomogram to the tomo instance
            tomo_instance.add_tomo(session.models.list()[-2])
            tomo_instance.set_dimensions(x_dim, y_dim, z_dim)

            # Update Tomo table (table_1)
            self.update_table(1, tomo_instance, name=tomo_filename)

        # Reset tomo filename
        self.tomo_filename = None


    def create_motl_pressed(self, session):
        # Create a default name of the Motivelist dependent on how many
        # Motivelists are already open
        motl_name = "Marker_Set_{}".format(self.counter_2 + 1)

        row = self.table_2.rowCount()
        # Create a Motivelist instance and add to the list of Motivelists
        from .object_settings import MotlSettings
        motl_instance = MotlSettings(motl_name, row)
        self.motl_list.append(motl_instance)

        # Update Motl table (table_2)
        self.update_table(2, motl_instance, name=motl_name)


    def load_motl_pressed(self, session):
        # Open file dialog to open the motivelist (EM file)
        self.select = self.file_dialog_open.exec()

        if self.select:
            self.motl_filename = self.file_dialog_open.selectedFiles()

        motl_name = os.path.basename(self.motl_filename[0])
        motl_data = emread(self.motl_filename[0])
        motl_data = np.ndarray.tolist(motl_data[0])

        row = self.table_2.rowCount()
        # Create a Motivelist instance and add to the list of Motivelists
        from .object_settings import MotlSettings
        motl_instance = MotlSettings(motl_name, row)

        # Get an unused ID to assign the markers to
        id = self.get_unused_id(session)
        # Usually new markers will now get the same ID
        # A way around this is by adding 1 to id (here in the code)
        id += 1

        for i in range(len(motl_data)):
            # Get the coordinates and radius
            radius = motl_data[i][2]
            x_coord = motl_data[i][7]
            y_coord = motl_data[i][8]
            z_coord = motl_data[i][9]

            # Assign found id to markers and place them
            run(session, "marker #{} position {},{},{} color yellow radius {}".format(id, x_coord, y_coord, z_coord, 4))

        # Select all markers using the given ID
        run(session, "select #{}".format(id))
        # And color all in the default color
        run(session, "color #{} 0,0,100".format(id))

        # Add the marker instance to the motl instance
        markers = selected_markers(session)
        motl_instance.add_marker(markers, id)

        # Update the table
        self.update_table(2, motl_instance, name=motl_name)

        # Add motl instance to the motl list
        self.motl_list.append(motl_instance)


    def save_motl_menu_pressed(self, session):
        if self.motl_selected_instance == None:
            print("Error: No motivelist to save selected.")
        else:
            # Activate the selector
            self.select = self.file_dialog_save.exec()
            # Open file dialog to save motivelist
            if self.select:
                self.motl_filename =  self.file_dialog_save.selectedFiles()

            # Get filename
            motl_filename = os.path.basename(self.motl_filename[0])
            # Update the filename in motl instance and table
            self.motl_selected_instance.name = motl_filename
            self.table_2.setItem(self.motl_selected_instance.table_row, 0, QTableWidgetItem(motl_filename))

            # Store data in a numpy array
            em_data = np.asarray([s[:20] for s in self.motl_selected_instance.motivelist])

            # Save the data in the corresponding path
            emwrite(em_data, self.motl_filename[0])


    def save_marker_menu_pressed(self, session):
        # Pops up a file dialog which indicates where to save the marker

        # Activate the selector
        self.select = self.file_dialog_save.exec()
        # Open file dialog to save marker
        if self.select:
            self.motl_filename =  self.file_dialog_save.selectedFiles()

        # Create the motivelist from the marker positions
        markers = atomic.selected_atoms(session)    # Markers
        if len(markers) > 0:
            motl = [[0 for i in range(20)] for j in range(len(markers))]    # Motivelist with only zeros
            # Save the positions to the motivelist
            counter = 0
            for marker in markers:
                motl[counter][7] = marker.coord[0]  # X coord
                motl[counter][8] = marker.coord[1]  # Y coord
                motl[counter][9] = marker.coord[2]  # Z coord

                counter += 1

            # Save the motivelist as an EM File
            motl = np.asarray(motl)
            if ".em" in self.motl_filename[0]:
                emwrite(motl, self.motl_filename[0])
            else:
                self.motl_filename[0] += ".em"
                emwrite(motl, self.motl_filename[0])
        else:
            print("Error: Please select markers to save")


    def save_session_log_pressed(self, session):
        return print("You've just pressed 'Save Session Log'")

# ==============================================================================
# Main Window Functions ========================================================
# ==============================================================================

    def close_tomogram_pressed(self, session):
        # This button only works if a tomo from the table is selected
        if self.tomo_selected_instance == None:
            print("Error: Please select a tomogram from the table")
        else:
            # Get the selected tomos
            raise_id_error = False
            volumes = [v for v in session.selection.models()]

            # Only proceed if all selected objects belong to tomogram instance
            volume_ids = []
            for v in volumes:
                try:
                    id = int(v.id_string)
                    volume_ids.append(id)
                except:
                    continue
            for id in volume_ids:
                if id in self.tomo_selected_instance.tomo_ids:
                    continue
                else:
                    raise_id_error = True
            if raise_id_error:
                print("Error: One or more selected object(s) do(es) not belong to selected Tomogram")
                return

            # Now finally close all selected objects and update the table
            command = "close "
            for i in volume_ids:
                command += "#{} ".format(i)
            run(session, command)

            # Update the row in all motl instances with larger row number
            for instance in self.tomo_list:
                if instance.table_row > self.tomo_selected_instance.table_row:
                    instance.table_row -= 1
            # The way the table widget works is that we have to delete the last row
            # And then update every other row
            rows = self.table_1.rowCount()
            self.table_1.removeRow(rows-1)
            for instance in self.motl_list:
                self.table_1.setItem(instance.table_row, 0, QTableWidgetItem(instance.table_name))
                self.table_1.setItem(instance.table_row, 1, QTableWidgetItem(instance.table_show))
                self.table_1.setItem(instance.table_row, 2, QTableWidgetItem(instance.table_select))

            # And finally remove the motl from the motl_list
            self.tomo_list.remove(self.tomo_selected_instance)


    def tomo_show_hide_pressed(self, session):
        # This button only works if a tomo from the table is selected
        if self.tomo_selected_instance == None:
            print("Error: Please select a tomogram from the table")
        else:
            # Get the selected tomos
            raise_id_error = False
            volumes = [v for v in session.selection.models()]

            # Only proceed if all selected objects belong to tomogram instance
            volume_ids = []
            for v in volumes:
                try:
                    id = int(v.id_string)
                    volume_ids.append(id)
                except:
                    continue
            for id in volume_ids:
                if id in self.tomo_selected_instance.tomo_ids:
                    continue
                else:
                    raise_id_error = True
            if raise_id_error:
                print("Error: One or more selected object(s) do(es) not belong to selected Tomogram")
                return

            # Show or hide the selected models depending on the table entry
            if self.tomo_selected_instance.table_select == u"":    # If this is unchecked
                self.tomo_selected_instance.table_select = u""     # Check this

                # Update table
                self.table_1.setItem(self.tomo_selected_instance.table_row, 1, QTableWidgetItem(u""))

                # And show all the selected volumes
                command = "show "
                for i in volume_ids:
                    command += "#{} ".format(i)

                run(session, command)

            elif self.tomo_selected_instance.table_select == u"":  # If this is checked
                self.tomo_selected_instance.table_select = u""     # Uncheck this

                # Update table
                self.table_1.setItem(self.tomo_selected_instance.table_row, 1, QTableWidgetItem(u""))

                # And hide all the selected volumes
                command = "hide "
                for i in volume_ids:
                    command += "#{} ".format(i)

                run(session, command)


    def process_tomograms_pressed(self, session):
        print("You've pressed the Process Tomograms button, congratz!")


    # Function that resets any rotation
    def tomo_reset_pressed(self, session):
        # Check which tomogram is selected
        ids = []
        for tomo in self.tomo_list:
            if tomo.table_select == u"":
                ids = tomo.tomo_ids

        # Rotate the selected tomogram(s) back to their initial rotation
        view_matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]
        for id in ids:
            command = "view matrix models #{}".format(id)
            for i in range(len(view_matrix)):
                command += ",{}".format(view_matrix[i])
            run(session, command)


    def close_motls_pressed(self, session):
        # This button only works if a motl from the table is selected
        if self.motl_selected_instance == None:
            print("Error: Please select a motivelist from the table")
        else:
            # Close the objects in the motivelist
            command = "close "
            for i in range(len(self.motl_selected_instance.motivelist)):
                id = self.motl_selected_instance.motivelist[i][21]
                if "#" in id:
                    command += "{} ".format(id)
                else:
                    command += "#{} ".format(id)
            # Only execute this command if the motivelist is non-empty
            if command == "close ":
                print("Nothing to close.")
            else:
                run(session, command)
            # Update the row in all motl instances with larger row number
            for instance in self.motl_list:
                if instance.table_row > self.motl_selected_instance.table_row:
                    instance.table_row -= 1
            # The way the table widget works is that we have to delete the last row
            # And then update every other row
            rows = self.table_2.rowCount()
            self.table_2.removeRow(rows-1)
            for instance in self.motl_list:
                self.table_2.setItem(instance.table_row, 0, QTableWidgetItem(instance.table_name))
                self.table_2.setItem(instance.table_row, 1, QTableWidgetItem(instance.table_object_name))
                self.table_2.setItem(instance.table_row, 2, QTableWidgetItem(instance.table_show))
                self.table_2.setItem(instance.table_row, 3, QTableWidgetItem(instance.table_select))

            # Also change the browse text where the object filepath might be
            self.manipulation.obj_filename_edit.setText("")

            # And finally remove the motl from the motl_list
            self.motl_list.remove(self.motl_selected_instance)
            self.motl_selected_instance = None


# ==============================================================================
# Other Functions ==============================================================
# ==============================================================================

    def set_variables(self):
        self.motl_list = []                 # Contains all motivelist instances
        self.tomo_list = []                 # Contains all tomogram instances
        self.motl_selected_instance = None  # Currently selected motivelist
        self.tomo_selected_instance = None  # Currently selected tomogram
        # Also define a static base of unit vectors
        self.unit_1 = [1, 0, 0]
        self.unit_2 = [0, 1, 0]
        self.unit_3 = [0, 0, 1]
        # Selector which file Dialog opens
        self.select = None
        # Initialize some default file paths
        self.tomo_filename = None
        self.motl_filename = None
        self.motl_name = None
        # initialize the selected motivelist
        self.motl_selected_instance = None


    # Function that determines what cell was clicked and executes corresponding actions
    def table_clicked(self, session, table):
        # Which table are we talking about?
        if table == 1:
            # Get the clicked cell
            select_cell = QTableWidgetItem()
            select_cell = self.table_1.selectedItems()[0]
            self.tomo_current_column = select_cell.column()
            self.tomo_current_row = select_cell.row()

            # Get the tomogram instance of the same name
            for tomo in self.tomo_list:
                if tomo.table_row == self.tomo_current_row:
                    self.tomo_selected_instance = tomo

            # If second column is selected show/hide tomograms
            if self.tomo_current_column == 1:
                if self.tomo_selected_instance.table_show == u"":    # If hidden
                    # Update the table
                    row = self.tomo_selected_instance.table_row
                    self.table_1.setItem(row, 1, QTableWidgetItem(u""))    # Shown
                    # Show the tomograms
                    self.show_hide_tomo(session, True)
                elif self.tomo_selected_instance.table_show == u"":  # If shown
                    # Update the table
                    row = self.tomo_selected_instance.table_row
                    self.table_1.setItem(row, 1, QTableWidgetItem(u""))    # Hidden
                    # Hide the tomograms
                    self.show_hide_tomo(session, False)

            # If third column is selected (un)select tomograms
            elif self.tomo_current_column == 2:
                if self.tomo_selected_instance.table_select == u"":    # If unselected
                    # Update the table
                    row = self.tomo_selected_instance.table_row
                    self.table_1.setItem(row, 2, QTableWidgetItem(u""))    # Selected
                    # Select the tomograms
                    self.select_unselect_tomo(session, True)
                    # Also if a hidden tomogram is selected show this tomogram
                    # Update table
                    self.table_1.setItem(row, 1, QTableWidgetItem(u""))    # Shown
                    # Show the tomograms
                    self.show_hide_tomo(session, True)
                elif self.tomo_selected_instance.table_select == u"":  # If selected
                    # Update table
                    row = self.tomo_selected_instance.table_row
                    self.table_1.setItem(row, 2, QTableWidgetItem(u""))    # Unselected
                    # Unselect tomograms
                    self.select_unselect_tomo(session, False)

        elif table == 2:
            # Get the clicked cell
            select_cell = QTableWidgetItem()
            select_cell = self.table_2.selectedItems()[0]
            self.motl_current_column = select_cell.column()
            self.motl_current_row = select_cell.row()

            # Get the motl instance of the same name
            for motl in self.motl_list:
                if motl.table_row == self.motl_current_row:
                    self.motl_selected_instance = motl

            # If third column is selected show/hide motivelist
            if self.motl_current_column == 2:
                if self.motl_selected_instance.table_show == u"":    # If hidden
                    # Update table
                    row = self.motl_selected_instance.table_row
                    self.table_2.setItem(row, 2, QTableWidgetItem(u""))    # Shown
                    # Show motivelist
                    self.show_hide_motl(session, True)
                elif self.motl_selected_instance.table_show == u"":  # If shown
                    # Update table
                    row = self.motl_selected_instance.table_row
                    self.table_2.setItem(row, 2, QTableWidgetItem(u""))    # Hidden
                    # Hide motivelist
                    self.show_hide_motl(session, False)

            # If fourth column is selected (un)select motivelist
            elif self.motl_current_column == 3:
                if self.motl_selected_instance.table_select == u"":    # If unselected
                    # At first unselect every motivelist in the table
                    for motl in self.motl_list:
                        motl.table_select = u""
                    for row in range(self.table_2.rowCount()):
                        self.table_2.setItem(row, 3, QTableWidgetItem(u""))
                    # Update table
                    row = self.motl_selected_instance.table_row
                    self.table_2.setItem(row, 3, QTableWidgetItem(u""))    # Selected
                    # Select motl
                    self.select_unselect_motl(session, True)

                    # Since selecting this motivelist results in the motivelist
                    # Being shown in the visualization and manipulation - which
                    # Comes along with also being displayed, triggering select
                    # Should also update the show status of the motivelist
                    self.motl_selected_instance.table_show = u""
                    self.table_2.setItem(row, 2, QTableWidgetItem(u""))

                    # Communication with visualization window
                    # ----------------------------------------------------------
                    # Set title name
                    self.visualization.group_motl_select.setTitle("Selection: {}".format(self.motl_selected_instance.name))
                    # Give over the selected motivelist instance to visualization
                    self.visualization.build_properties(self.motl_selected_instance)
                    # Lock all the sliders
                    self.visualization.execute = False
                    # Set minimum and maximum for slider
                    self.visualization.build_slider(session)
                    # Unlock sliders
                    self.visualization.execute = True
                    # Since this function (build_slider) resolves in only one objects being shown
                    # (Which is the first) we execute the command of showing all
                    # Objects in the motivelist instance
                    self.visualization.show = False
                    self.visualization.show_button_pressed(session)

                    # __________________________________________________________
                    # And also with manipulation window
                    # Give the motl instance to the manipulation window
                    self.manipulation.select_motl_instance(self.motl_selected_instance)
                    # Insert filepath to object in the corresponding QLineEdit
                    self.manipulation.obj_filename_edit.setText(self.motl_selected_instance.obj_filepath)

                    # ----------------------------------------------------------

                elif self.motl_selected_instance.table_select == u"":  # If selected
                    # Update table
                    row = self.motl_selected_instance.table_row
                    self.table_2.setItem(row, 3, QTableWidgetItem(u""))    # Unselected
                    # Unselect motivelist
                    self.select_unselect_motl(session, False)

                    # Communication with other windows
                    # --------------------------------------------------------------
                    # Lock all the sliders
                    self.visualization.execute = False
                    # Reset the visualization window
                    self.visualization.reset()

                    # ______________________________________________________________
                    # And also tohe manipulation options
                    self.manipulation.unselect_motl_instance()
                    # Reset the object filepath in the corresponding QLineEdit
                    self.manipulation.obj_filename_edit.setText("")

                    # --------------------------------------------------------------

                    # When the motivelist is not selected anymore the local variable vanishes
                    self.motl_selected_instance = None

        else:
            print("You don't have a table selected, how is this possible?")


    def show_hide_tomo(self, session, show):
        if show:
            # Show the tomograms
            command = "show "
            for id in self.tomo_selected_instance.tomo_ids:
                command += "#{} ".format(id)
            if command == "show ":
                print("Nothing to show.")
            else:
                run(session, command)
            # Update tomo instance
            self.tomo_selected_instance.table_show = u""     # Shown
        else:
            # Hide the tomograms
            command = "hide "
            for id in self.tomo_selected_instance.tomo_ids:
                command += "#{} ".format(id)
            if command == "hide ":
                print("Nothing to hide.")
            else:
                run(session, command)
            # Update tomo instance
            self.tomo_selected_instance.table_show = u""     # Hidden


    def select_unselect_tomo(self, session, select):
        if select:
            # Select the tomograms
            command = "select "
            for id in self.tomo_selected_instance.tomo_ids:
                command += "#{} ".format(id)
            # Only run the command if the motivelist is non-empty
            if command == "select ":
                print("Nothing to select.")
            else:
                run(session, command)
            # Update tomo instance
            self.tomo_selected_instance.table_select = u""     # Selected
        else:
            # Unselect everything
            run(session, "select clear")
            # Update tomo instance and table
            self.tomo_selected_instance.table_select = u""     # Unselected



    def show_hide_motl(self, session, show):
        if show:
            # Show the motivelist
            command = "show "
            for i in range(len(self.motl_selected_instance.motivelist)):
                id = self.motl_selected_instance.motivelist[i][21]
                if "#" in id:
                    command += "{} ".format(id)
                else:
                    command += "#{} ".format(id)
            # Only show if the motivelist is non-empty
            if command == "show ":
                print("No object to show.")
            else:
                run(session, command)
            # Update motl instance and table
            self.motl_selected_instance.table_show = u""     # Shown
        else:
            # Hide the motivelist
            command = "hide "
            for i in range(len(self.motl_selected_instance.motivelist)):
                id = self.motl_selected_instance.motivelist[i][21]
                if "#" in id:
                    command += "{} ".format(id)
                else:
                    command += "#{} ".format(id)
            # Only hide if the motivelist is non-empty
            if command == "hide ":
                print("No object to hide.")
            else:
                run(session, command)
            # Update motl instance and table
            self.motl_selected_instance.table_show = u""     # Hidden


    def select_unselect_motl(self, session, select):
        if select:
            # Select the motivelist
            command = "select "
            for i in range(len(self.motl_selected_instance.motivelist)):
                id = self.motl_selected_instance.motivelist[i][21]
                if "#" in id:
                    command += "{} ".format(id)
                else:
                    command += "#{} ".format(id)
            # Only select objects if motivelist contains any
            if command == "select ":
                print("Nothing to select.")
            else:
                run(session, command)
            # Update motl instance and table
            self.motl_selected_instance.table_select = u""     # Selected
            # Selected objects are colored in a darker blue
            for i in range(len(self.motl_selected_instance.motivelist)):
                id = self.motl_selected_instance.motivelist[i][21]
                if "#" in id:
                    run(session, "color {} 0,100,100".format(id))
                else:
                    run(session, "color #{} 0,100,100".format(id))
        else:
            # Unselect the motl
            run(session, "select clear")
            # Update motl instance and table
            self.motl_selected_instance.table_select = u""     # Unselected

            # Color all objects in the default color
            for i in range(len(self.motl_selected_instance.motivelist)):
                id = self.motl_selected_instance.motivelist[i][21]
                if "#" in id:
                    run(session, "color {} 0,0,100".format(id))
                else:
                    run(session, "color #{} 0,0,100".format(id))


    # Function the updates the table with the corresponding input
    def update_table(self, table, connect_instance, name = "", obj_name = "",
                selected = u"", show = u""):
        # Choose the right table
        if table == 1:
            # Get the number of rows and expand table by one row
            number_rows = self.table_1.rowCount()
            self.table_1.setRowCount(number_rows + 1)

            # Print the entries of the table
            self.table_1.setItem(number_rows, 0, QTableWidgetItem(name))
            self.table_1.setItem(number_rows, 1, QTableWidgetItem(show))
            self.table_1.setItem(number_rows, 2, QTableWidgetItem(selected))

            self.counter_1 += 1

        elif table == 2:
            # Get the number of rows and expand table by one row
            number_rows = self.table_2.rowCount()
            self.table_2.setRowCount(number_rows + 1)

            # Print the entries of the table
            self.table_2.setItem(number_rows, 0, QTableWidgetItem(name))
            self.table_2.setItem(number_rows, 1, QTableWidgetItem(obj_name))
            self.table_2.setItem(number_rows, 2, QTableWidgetItem(show))
            self.table_2.setItem(number_rows, 3, QTableWidgetItem(selected))

            self.counter_2 += 1

        else:
            print("You don't have a table selected, how is this possible?")

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


    def load_obj_to_motl(self, session, filepath):
        # Just a quick routine to get the surface level
        # It's a bad way around, but it works
        run(session, "open {}".format(filepath))
        volumes = session.models.list()
        surface = volumes[-1]
        surface_level = surface.level
        id = volumes[-2].id_string
        run(session, "close #{}".format(id))

        # Initialize variables
        current_volume = None

        # Get the name of the object
        obj_name = os.path.basename(filepath)
        motl_name = self.motl_selected_instance.name    # Check next lines

        # Since it has already been checked before that a motivelist instance
        # Is actually selected, we can simply add the object name here
        self.motl_selected_instance.obj_name = motl_name
        self.motl_selected_instance.obj_filepath = filepath

        # Make a list that contains the indices of all markers (no objects)
        index_list = []
        for i in range(len(self.motl_selected_instance.motivelist)):
            id = self.motl_selected_instance.motivelist[i][21]
            if "#" in id:
                index_list.append(i)

        # At first delete the markers
        for index in index_list:
            run(session, "close {}".format(self.motl_selected_instance.motivelist[i][21]))

        vol_data = 0

        if ".em" in filepath:
            # Get the shape of the data
            vol_data = emread(filepath)
            dimensions = np.asarray(vol_data.shape)
            voxel_size = [1, 1, 1]  # Which is default by EM file

            # Us the dimensions and the voxel size to determine the origin
            origin = [-ma.floor(dimensions[0]*voxel_size[0]/2)+1,-ma.floor(dimensions[1]*voxel_size[1]/2)+1,-ma.floor(dimensions[2]*voxel_size[2]/2)+1]

            # Change data to a ChimeraX GridData
            data_grid = ArrayGridData(vol_data, origin=origin, step=voxel_size, name=obj_name)

        elif ".mrc" in filepath:
            # Get the shape and the voxel size of the data and the data itself
            with mrcfile.open(filepath) as mrc:
                dimensions = np.asarray([mrc.header.nx, mrc.header.ny, mrc.header.nz])
                voxel_size = mrc.voxel_size.copy()
                vol_data = mrc.data
            # with the dimensions determine the origin, which is the center of the object
            origin = [-ma.floor(dimensions[0]*voxel_size.x/2)+1,-ma.floor(dimensions[1]*voxel_size.y/2)+1,-ma.floor(dimensions[2]*voxel_size.z/2)+1]
            step = np.asarray([voxel_size.x, voxel_size.y, voxel_size.z])

            # Change data to a ChimeraX GridData
            # mrc_grid = ArrayGridData(mrc_data, origin=origin, step=step, rotation=rot_mat, name=mrc_filename)
            data_grid = ArrayGridData(vol_data, origin=origin, step=step, name=obj_name)

        # For each object apply the corresponding shift and rotation
        for i in index_list:
            # Get position and rotation
            x_coord = self.motl_selected_instance.motivelist[i][7]
            y_coord = self.motl_selected_instance.motivelist[i][8]
            z_coord = self.motl_selected_instance.motivelist[i][9]
            phi = self.motl_selected_instance.motivelist[i][16]
            psi = self.motl_selected_instance.motivelist[i][17]
            theta = self.motl_selected_instance.motivelist[i][18]

            # Turn GridData to a ChimeraX volume which automatically is also
            # Added to the open models
            volume_from_grid_data(data_grid, session)

            # Add new volume to the object list in the motl instance
            current_volume = session.models.list()[-1]

            # Add volume and ID to motivelist
            self.motl_selected_instance.motivelist[i][20] = current_volume
            self.motl_selected_instance.motivelist[i][21] = current_volume.id_string

            # Use ChimeraX's view matrix method to rotate and translate
            # For this we need the rotation matrix appanded by the translation vector
            rot_mat = []
            rot_mat.extend(detRotMat(phi, psi, theta))
            # Append the translation vector
            rot_mat[0].append(x_coord)
            rot_mat[1].append(y_coord)
            rot_mat[2].append(z_coord)

            # Prepare the string for the command
            command = "view matrix models #{}".format(current_volume.id_string)
            for i in range(3):
                for j in range(4):
                    command += ",{}".format(rot_mat[i][j])

            run(session, command)

            # Also fix the problem EM files being displayed the wrong way
            run(session, "volume #{} capFaces false".format(current_volume.id_string))
            # # And give it the default color
            # run(session, "color #{} 0,0,100".format(current_volume.id_string))

        # Add the object to the motl instance
        self.motl_selected_instance.add_obj(obj_name, dimensions, voxel_size, False)

        # Set minimum, maximum and current surface level in motl instance
        self.motl_selected_instance.set_min_max(vol_data.min(), vol_data.max(), surface_level)#current_volume.surfaces[0].level)


        # Update the motl instance in visualization and manipulation
        self.visualization.motl_instance = self.motl_selected_instance
        self.manipulation.motl_instance = self.motl_selected_instance


# ==============================================================================
# Set other window's buttons ===================================================
# ==============================================================================

    def _connect_visualization(self, session):
        self.visualization.show_button.clicked.connect(partial(self.vis_show_button_pressed, session))
        self.visualization.close_button.clicked.connect(partial(self.vis_close_button_pressed, session))


    def _connect_manipulation(self, session):
        self.manipulation.update_button.clicked.connect(partial(self.mani_update_motl_pressed, session))
        self.manipulation.color_button.clicked.connect(partial(self.mani_motl_color_pressed, session))
        self.manipulation.marker_button.clicked.connect(partial(self.mani_marker_button_pressed, session))
        self.manipulation.delete_button.clicked.connect(partial(self.mani_delete_button_pressed, session))
        self.manipulation.obj_filename_edit.returnPressed.connect(partial(self.mani_obj_filename_edit_enter, session))
        self.manipulation.obj_filename_button.clicked.connect(partial(self.mani_obj_filename_button_pressed, session))


# ==============================================================================
# Function to communicate with other windows ===================================
# ==============================================================================

# Communication with visualization
# ------------------------------------------------------------------------------

    def vis_show_button_pressed(self, session):
        # Update the motl instance and table with either shown or not hidden
        if self.visualization.show:     # Objects are shown
            # Hide objects in table and motl instance
            self.motl_selected_instance.table_show = u""
            row = self.motl_selected_instance.table_row
            self.table_2.setItem(row, 2, QTableWidgetItem(u""))

        else:                           # Objects are hidden
            # Show objects in table and motl instance
            self.motl_selected_instance.table_show = u""
            row = self.motl_selected_instance.table_row
            self.table_2.setItem(row, 2, QTableWidgetItem(u""))

        # Show/Hide all objects
        # Hide all objects
        self.visualization.show_button_pressed(session)


    # Update table (unselect/hide) and run function in visualization class
    def vis_close_button_pressed(self, session):
        # No information have been changed, so we don't have to get the
        # Latest version of the motl instance
        # Instead call the reset in the visualization class
        self.visualization.execute = False
        self.visualization.reset()

        # Now update the local motl instance and table
        self.motl_selected_instance.table_select = u"" # Not selected
        row = self.motl_selected_instance.table_row
        self.table_2.setItem(row, 3, QTableWidgetItem(u""))

        # Recolor all objects and unselect them
        for i in range(len(self.motl_selected_instance.motivelist)):
            id  = self.motl_selected_instance.motivelist[i][21]
            if "#" in id:
                run(session, "color {} 0,0,100".format(id))
            else:
                run(session, "color #{} 0,0,100".format(id))
        run(session, "select clear")

        # Change the QLineEdit with the filepath of the object
        self.manipulation.obj_filename_edit.setText("")

        # No motl instance is selected anymore
        self.motl_selected_instance = None


# ______________________________________________________________________________
# Communicate with manipulation
# ______________________________________________________________________________

    def mani_update_motl_pressed(self, session):
        # Update the motivelist with all the new postitions anf angles
        self.manipulation.motl_instance = self.motl_selected_instance
        self.manipulation.update_button_pressed(session)

        # Call the new information to store it in this class' local variable
        self.motl_selected_instance = self.manipulation.motl_instance


    def mani_motl_color_pressed(self, session):
        self.manipulation.motl_instance = self.motl_selected_instance
        # Execute the associated manipulation function
        self.manipulation.color_button_pressed(session)

        self.motl_selected_instance = self.manipulation.motl_instance


    def mani_marker_button_pressed(self, session):
        if self.motl_selected_instance == None:
            print("Error: No motivelist selected")
        else:
            # Get the markers' ID befor closing them later
            marker_id = int(session.selection.models()[0].id_string)

            # Set some default values
            dimension = [0, 0, 0]
            voxel_size = [0, 0, 0]
            origin = [0, 0, 0]
            filename = None

            if self.motl_selected_instance.obj_filepath == None:
                # Add the marker instance to the motl instance
                markers = selected_markers(session)
                # Get the same ID as other markers if markers are already
                # Part of the motivelist
                if len(self.motl_selected_instance.motivelist) == 0:
                    # Get a new ID if the motivelist empty
                    id = session.selection.models()[0].id_string
                else:
                    # Get the already used ID for the markers
                    marker_id = self.motl_selected_instance.motivelist[0][21]
                    lower_index = marker_id.index("#") + 1
                    upper_index = marker_id.index("/")
                    id = marker_id[lower_index:upper_index]
                self.motl_selected_instance.add_marker(markers, id)
                # Also change the color of the markers
                for marker in markers:
                    marker.color = [0, 255, 255, 255]

                # Give the expanded motivelist to manipulation
                self.manipulation.motl_instance = self.motl_selected_instance
                # And build the silders again (so that the new markers are included)
                # Unlock all the sliders
                self.visualization.execute = True
                # Set minimum and maximum for slider
                self.visualization.build_slider(session)
            else:
                # Load the data of the object
                if ".em" in self.motl_selected_instance.obj_filepath:
                    filename = os.path.basename(self.motl_selected_instance.obj_filepath)
                    # Get the EM file
                    em_data = emread(self.motl_selected_instance.obj_filepath)
                    dimensions = np.asarray(em_data.shape)
                    voxel_size = [1, 1, 1]

                    # Us the dimensions and the voxel size to determine the origin
                    origin = [-ma.floor(dimensions[0]*voxel_size[0]/2)+1,-ma.floor(dimensions[1]*voxel_size[1]/2)+1,-ma.floor(dimensions[2]*voxel_size[2]/2)+1]

                    grid_data = ArrayGridData(em_data, origin=origin, step=voxel_size, name=filename)

                elif ".mrc" in self.motl_selected_instance.obj_filepath:
                    filename = os.path.basename(self.motl_selected_instance.obj_filepath)
                    # Get the shape and the voxel size of the data and the data itself
                    with mrcfile.open(self.motl_selected_instance.obj_filepath) as mrc:
                        dimensions = np.asarray([mrc.header.nx, mrc.header.ny, mrc.header.nz])
                        voxel_size = mrc.voxel_size.copy()
                        mrc_data = mrc.data
                    # with the dimensions determine the origin, which is the center of the object
                    origin = [-ma.floor(dimensions[0]*voxel_size.x/2)+1,-ma.floor(dimensions[1]*voxel_size.y/2)+1,-ma.floor(dimensions[2]*voxel_size.z/2)+1]
                    step = np.asarray([voxel_size.x, voxel_size.y, voxel_size.z])

                    # Change data to a ChimeraX GridData
                    # mrc_grid = ArrayGridData(mrc_data, origin=origin, step=step, rotation=rot_mat, name=mrc_filename)
                    grid_data = ArrayGridData(mrc_data, origin=origin, step=step, name=filename)

                # Get the selected markers
                atoms = atomic.selected_atoms(session)

                current_obj = len(self.motl_selected_instance.motivelist)
                for i in range(len(atoms)):
                    # self.motl_selected_instance.motivelist.append(self.motl_selected_instance.empty_row)
                    # Turn GridData to a ChimeraX volume which automatically is also
                    # Added to the open models
                    volume_from_grid_data(grid_data, session)

                    # Select the current volume
                    current_volume = session.models.list()[-1]
                    # Get the coordinates
                    coords = atoms[i].coord
                    x_coord = coords[0]
                    y_coord = coords[1]
                    z_coord = coords[2]

                    new_line = []
                    new_line.extend([0]*22)
                    new_line = [0]*22
                    new_line[7] = x_coord
                    new_line[8] = y_coord
                    new_line[9] = z_coord

                    new_line[20] = current_volume
                    new_line[21] = current_volume.id_string

                    # Add the new column (particle) to the motl
                    self.motl_selected_instance.motivelist.append(new_line)

                    # Use ChimeraX's view matrix method to rotate and translate
                    # For this we need the rotation matrix appanded by the translation vector
                    rot_mat = detRotMat(0, 0, 0)
                    # Append the translation vector
                    rot_mat[0].append(x_coord)
                    rot_mat[1].append(y_coord)
                    rot_mat[2].append(z_coord)

                    # Prepare the string for the command
                    command = "view matrix models #{}".format(current_volume.id_string)
                    for i in range(3):
                        for j in range(4):
                            command += ",{}".format(rot_mat[i][j])

                    run(session, command)

                    # Also fix the problem of EM files being displayed the wrong way
                    run(session, "volume #{} capFaces false".format(current_volume.id_string))

                # Finally close the markers
                run(session, "close #{}".format(marker_id))

                # Give the expanded motivelist to manipulation
                self.manipulation.motl_instance = self.motl_selected_instance
                # Add the object to the motl instance
                self.motl_selected_instance.add_obj(filename, dimensions, voxel_size, False)
                # And build the silders again (so that the new objects are included)
                # Unlock all the sliders
                self.visualization.execute = True
                # Set minimum and maximum for slider
                self.visualization.build_slider(session)
                # And give it the default color
                # Also run the volume level to build the surface which enables coloring
                # This is only needed for volumes, not for markers
                for i in range(len(self.motl_selected_instance.motivelist)):
                    id = self.motl_selected_instance.motivelist[i][21]
                    if "#" in id:   # Markers
                        run(session, "color {} 0,100,100".format(id))
                    else:   # Volumes
                        run(session, "volume #{} level {}".format(id, self.motl_selected_instance.surface_obj_current))
                        run(session, "color #{} 0,100,100".format(id))
                # run(session, "color #{} 0,0,100".format(current_volume.id_string))


    def mani_delete_button_pressed(self, session):
        # Deletes the selected object(s) from the motivelist
        # At first send the motl instance to the manipulation window
        self.manipulation.motl_instance = self.motl_selected_instance

        # Execute the function in the manipulation window
        self.manipulation.delete_button_pressed(session)

        # Receive the motivelist instance from manipulation again
        self.motl_selected_instance = self.manipulation.motl_instance


    def mani_obj_filename_button_pressed(self, session):
        # Make sure that a motl instance is selected
        if self.motl_selected_instance == None:
            print("Error: No motivelist selected.")
        else:
            # Open a filedialog to load the filepath of the object
            self.select = self.file_dialog_open.exec()

            if self.select:
                motl_filename = self.file_dialog_open.selectedFiles()[0]
            else:
                motl_filename = None
            # Set the filepath in the QLineEdit
            self.manipulation.obj_filename_edit.setText(motl_filename)
            # Execute the file loading
            self.mani_obj_filename_execute(session, motl_filename)


    def mani_obj_filename_edit_enter(self, session):
        # Make sure that a motl instance is selected
        if self.motl_selected_instance == None:
            print("Error: No motivelist selected.")
        else:
            # Get the entered filepath
            motl_filename = self.manipulation.obj_filename_edit.text()
            # Execute the file loading
            self.mani_obj_filename_execute(session, motl_filename)


    def mani_obj_filename_execute(self, session, filepath):
        if filepath == None:
            print("Error: Please enter a correct filepath")
        else:
            # Load the selected object to the positions of the motl
            self.load_obj_to_motl(session, filepath)

            # Change the radius slider into the surface slider
            self.visualization.group_motl_select_variable_name.setText("Surface level")

            self.visualization.variable_switch = False    # Build the surface slider

            # Since load_obj_to_motl is executed before, these variables
            # Should already be set in the motl instance
            self.visualization.group_motl_select_variable_slider.setMinimum(ma.floor(100*self.motl_selected_instance.surface_obj_min))
            self.visualization.group_motl_select_variable_slider.setMaximum(ma.ceil(100*self.motl_selected_instance.surface_obj_max))
            self.visualization.group_motl_select_variable_slider.setValue(100*self.motl_selected_instance.surface_obj_current)

            # The surface should be build by now, so now it's time to color
            for i in range(len(self.motl_selected_instance.motivelist)):
                id = self.motl_selected_instance.motivelist[i][21]
                if "#" in id:
                    run(session, "color {} 0,100,100".format(id))
                else:
                    run(session, "color #{} 0,100,100".format(id))


# ------------------------------------------------------------------------------


# ==============================================================================
# Shortcut Functions ===========================================================
# ==============================================================================

# The following 4 jump functions only work if a tomogram is selected
    def jump_1_forwards_pressed(self, session):
        print("Yes, the shortcut worked.")
        if self.tomo_selected_instance != None:
            for id in self.tomo_selected_instance.tomo_ids:
                print("This is the selected tomogram's ID:", self.tomo_selected_instance.tomo_ids)
        #volume #1 planes z,100


    def jump_10_forwards_pressed(self, session):
        if self.tomo_selected_instance != None:
            print("Nothing.")


    def jump_1_backwards_pressed(self, session):
        if self.tomo_selected_instance != None:
            print("Nothing.")


    def jump_10_backwards_pressed(self, session):
        if self.tomo_selected_instance != None:
            print("Nothing.")


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
