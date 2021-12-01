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
from chimerax.map_data import ArrayGridData, GridData
from chimerax.map import Volume
from chimerax.core.models import Surface
from chimerax.atomic.molobject import Atom
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
from .options_window import OptionsWindow
from .object_settings import TomoInstance
from chimerax.ui import MainToolWindow
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QKeySequence, QMouseEvent

# from PyQt5.QtGui import QAbstractItemView
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QComboBox,
    QDesktopWidget,
    QFileDialog,
    QGroupBox,
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
def event(self, e):
        if not isinstance(e, (
                QtCore.QEvent,
                QtCore.QChildEvent,
                QtCore.QDynamicPropertyChangeEvent,
                QtGui.QPaintEvent,
                QtGui.QHoverEvent,
                QtGui.QMoveEvent,
                QtGui.QEnterEvent,
                QtGui.QResizeEvent,
                QtGui.QShowEvent,
                QtGui.QPlatformSurfaceEvent,
                QtGui.QWindowStateChangeEvent,
                QtGui.QKeyEvent,
                QtGui.QWheelEvent,
                QtGui.QMouseEvent,
                QtGui.QFocusEvent,
                QtGui.QHelpEvent,
                QtGui.QHideEvent,
                QtGui.QCloseEvent,
                QtGui.QInputMethodQueryEvent,
                QtGui.QContextMenuEvent,
                )):
            log().warning("unknown event: %r %r", e.type(), e)
        return super().event(e)


# Define the tomo class which is a ChimeraX tool window
class TomoDialog(ToolInstance):

    # Inheriting from ToolInstance makes us known to the ChimeraX tool manager,
    # so we can be notified and take appropiate action when sessions are closed,
    # save, or restored, and we will be listed among running tools and so on.

    # If cleaning up is needed on finish, override the 'delete' method
    # but be sure to call 'delete' from the superclass at the end

    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = True         # We do save/restore in sessions
    help = "help:user/tools/tutorial.html"
                                # Let ChimeraX know about our help page
    #pixel_size_old = 1.0
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
        # this behaviour, specify 'close_destroy=True' in the MainToolWindow
        # constructor

        self.tool_window = MainToolWindow(self)

        # We will be adding an item to the tool's context menu, so override
        # the default MainToolWindow fill context menu method
        self.tool_window.fill_context_menu = self.fill_context_menu

        # Our user interface is simple enough that we could probably inline
        # the code right here, but for any kind of even moderately complex
        # interface, it is probably better to put the code in a method so
        # that this __init__ method remains readable.
        self._build_ui(session, tool_name)

        # Create the variable options window with default GUI
        self._build_options_window(session, tool_name)


        # Connect the option window functions
        self.connect_tomo_functions(session)
        self.connect_motl_functions(session)

        # Connect the shortcurts to functions in the options window
        self.define_shortcuts(session)


# ==============================================================================
# Interface construction =======================================================
# ==============================================================================

    def _build_ui(self, session, tool_name):

        # Create a file dialog to browse through in order to open tomogram/motl
        self.file_dialog_open = QFileDialog()
        self.file_dialog_open.setFileMode(QFileDialog.AnyFile)
        self.file_dialog_open.setNameFilters(["Volume (*.em *.mrc *.mrcs)"])
        self.file_dialog_open.setAcceptMode(QFileDialog.AcceptOpen)
        self.file_dialog_save = QFileDialog()
        self.file_dialog_save.setFileMode(QFileDialog.AnyFile)
        self.file_dialog_save.setNameFilters(["Motivelist (*.em)"])
        self.file_dialog_save.setAcceptMode(QFileDialog.AcceptSave)

        # Set up some local variables
        self.set_variables()

        # Build the menu bar
        self.build_menubar(session)

        # Prepare some widgets that are used later
        self.prepare_tables(session)

        # Prepare main window widgets
        self.build_main_ui(session)

        # Build the actual GUI
        layout = QVBoxLayout()
        layout.addLayout(self.menu_bar_widget)
        layout.addWidget(self.group_tomo)
        layout.addWidget(self.group_motl)

        # Set the layout
        self.tool_window.ui_area.setLayout(layout)

        # Show the window on the user-preferred side of the
        # ChimeraX main window
        self.tool_window.manage("left")


# ==============================================================================
# Set some variables and shortcuts =============================================
# ==============================================================================


    def set_variables(self):
        self.tomo_list = []                 # Contains all tomogram instances
        self.motl_list = []                 # Contains all motivelist instances
        self.tomo_selected_instance = None  # Currently selected tomogram
        self.motl_selected_instance = None  # Currently selected motivelist
        # Also define a static base of unit vectors
        self.unit_1 = [1, 0, 0]
        self.unit_2 = [0, 1, 0]
        self.unit_3 = [0, 0, 1]
        # Selector which file Dialog opens
        self.select = None
        # Initialize some default file paths and names
        self.tomo_filepath = None
        self.motl_filepath = None
        self.motl_name = None
        # initialize the selected motivelist
        self.motl_selected_instance = None
        # Define a switch that indicates if a function is executed
        self.execution_switch = True

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def define_shortcuts(self, session):
        # Define the shortcuts
        self.jump_1_forwards = QShortcut(QKeySequence(Qt.Key_F4), self.options_window.group_slices_next_1)
        self.jump_10_forwards = QShortcut(QKeySequence(Qt.Key_F8), self.options_window.group_slices_next_10)
        self.jump_1_backwards = QShortcut(QKeySequence(Qt.Key_F3), self.options_window.group_slices_previous_1)
        self.jump_10_backwards = QShortcut(QKeySequence(Qt.Key_F7), self.options_window.group_slices_previous_10)
        # Connect actions to functions
        self.jump_1_forwards.activated.connect(partial(self.skip_planes, session, 1))
        self.jump_10_forwards.activated.connect(partial(self.skip_planes, session, 10))
        self.jump_1_backwards.activated.connect(partial(self.skip_planes, session, -1))
        self.jump_10_backwards.activated.connect(partial(self.skip_planes, session, -10))


# ==============================================================================
# Prepare GUI functions ========================================================
# ==============================================================================


    def build_menubar(self, session):
        # Use a QHBoxLayout for the menu bar
        self.menu_bar_widget = QHBoxLayout()
        # A dropdown menu for the menu bar
        self.menu_bar = QToolButton()
        self.menu_bar.setPopupMode(QToolButton.MenuButtonPopup)
        # Define all the buttons and connect them to corresponding function
        self.menu_bar_open_tomogram = QAction("Open Tomogram")
        self.menu_bar_open_tomogram.triggered.connect(partial(self.open_tomogram_pressed, session))
        self.menu_bar_load_motl = QAction("Load Motivelist")
        self.menu_bar_load_motl.triggered.connect(partial(self.load_motl_pressed, session))
        self.menu_bar_save_motl = QAction("Save Motivelist")
        self.menu_bar_save_motl.triggered.connect(partial(self.save_motl_pressed, session))
        # Prepare the file menu
        self.menu = QMenu("&File")
        self.menu.addAction(self.menu_bar_open_tomogram)
        self.menu.addSeparator()
        self.menu.addAction(self.menu_bar_load_motl)
        self.menu.addAction(self.menu_bar_save_motl)
        # Add to the actual menu
        self.menuBar = QMenuBar()
        self.menuBar.addMenu(self.menu)
        # Add the menu bar to the widget
        self.menu_bar_widget.addWidget(self.menuBar)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def prepare_tables(self, session):
        # Prepare some initial widgets
        # A display table for the tomograms
        self.table_tomo = QTableWidget()
        self.table_tomo.setFont(self.font)
        self.table_tomo.setRowCount(0)
        self.table_tomo.setColumnCount(3)
        header_1 = self.table_tomo.horizontalHeader()
        header_1.setSectionResizeMode(0, QHeaderView.Stretch)
        header_1.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_1.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_tomo.setHorizontalHeaderLabels(["Name", "Show", "Options"])
        # Connect the table (and items) to a function
        self.table_tomo.itemChanged.connect(partial(self.table_cell_clicked, session, 1))

        # A display table for the motivelists
        self.table_motl = QTableWidget()
        self.table_motl.setFont(self.font)
        self.table_motl.setRowCount(0)
        self.table_motl.setColumnCount(3) #4
        header_2 = self.table_motl.horizontalHeader()
        header_2.setSectionResizeMode(0, QHeaderView.Stretch)
        #header_2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_motl.setHorizontalHeaderLabels(["Name", "Show", "Options"])
        # Connect the table (and items) to a function
        self.table_motl.itemChanged.connect(partial(self.table_cell_clicked, session, 2))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def build_main_ui(self, session):
        # Design the main window which consists of two groups - tomo instance
        # And motl instance - which each use a QVBoxLayout

        # Start with the tomo group
        self.group_tomo = QGroupBox("Tomogram")
        self.group_tomo.setFont(self.font)
        # Set the layout
        self.group_tomo_layout = QVBoxLayout()
        # Add table_tomo and a close button to the layout
        self.group_tomo_layout.addWidget(self.table_tomo)
        self.group_tomo_close_button = QPushButton("Close selected tomogram")
        self.group_tomo_close_button.clicked.connect(partial(self.tomo_close_button_pressed, session))
        self.group_tomo_layout.addWidget(self.group_tomo_close_button)
        # Add layout to the group
        self.group_tomo.setLayout(self.group_tomo_layout)

        # Now add the motl group
        self.group_motl = QGroupBox("Motivelist")
        self.group_motl.setFont(self.font)
        # Set the layout
        self.group_motl_layout = QVBoxLayout()
        # Add table_motl and a close button to the layout
        self.group_motl_layout.addWidget(self.table_motl)
        # Set a new layout to have two buttons next to each other
        self.group_motl_button_layout = QHBoxLayout()
        self.group_motl_create_button = QPushButton("Create new motivelist")
        self.group_motl_create_button.clicked.connect(partial(self.motl_create_button_pressed, session))
        self.group_motl_button_layout.addWidget(self.group_motl_create_button)
        self.group_motl_close_button = QPushButton("Close selected motivelist")
        self.group_motl_close_button.clicked.connect(partial(self.motl_close_button_pressed, session))
        self.group_motl_button_layout.addWidget(self.group_motl_close_button)
        # Add button layout to group layout
        self.group_motl_layout.addLayout(self.group_motl_button_layout)
        # Add layout to the group
        self.group_motl.setLayout(self.group_motl_layout)


# ==============================================================================
# Menu Bar Functions ===========================================================
# ==============================================================================

    def open_tomogram_pressed(self, session):
        # When this button is clicked we need an empty filepath
        self.tomo_filepath = None

        # Activate the selector
        self.select = self.file_dialog_open.exec()
        # Get the clicked directory
        if self.select:
            self.tomo_filepath = self.file_dialog_open.selectedFiles()

        if self.tomo_filepath == None:  # If selecting is cancelled
            print("No tomogram selected.")
        else:
            run(session, "open {}".format(self.tomo_filepath[0]))
        # else:
        #     tomo_name = os.path.basename(self.tomo_filepath[0])
        #     print('Hi there!')
        #     tomo_data = emread(self.tomo_filepath[0])
        #     tomo_data = np.ndarray.tolist(tomo_data[0])

            # Unable the capFaces
            # Get the volume ID
            volumes = [v for v in session.models.list() if isinstance(v, Volume)]
            run(session, "volume #{} capFaces false".format(volumes[-1].id_string))
            # Also get the dimensions
            current_volume = volumes[-1]
            dimensions = current_volume.data.size
            # And the minimal and maximal value of the raw data
            data_matrix = current_volume.data.matrix( ijk_size = dimensions)
            minimum = data_matrix.min()
            maximum = data_matrix.max()
            print(minimum, maximum, current_volume.data.step)
            # print(ijk_to_xyz(data_matrix))

            # Get file name
            tomo_filename = os.path.basename(self.tomo_filepath[0])
            # Get the index of the row (before adding new row so it is the index)
            row = self.table_tomo.rowCount()

            # Update Tomo table (table_tomo)
            self.table_add_row(session=session, table_number=1, name=tomo_filename)

            # Create a tomogram instance and add to the list of tomograms
            tomo_instance = TomoInstance(tomo_filename, row, len(self.tomo_list), current_volume.id_string)
            tomo_instance.set_filepath(self.tomo_filepath)
            # Set the dimensions of the tomogram
            tomo_instance.set_dimensions(dimensions)
            # Set minimum and maximum of data
            tomo_instance.set_min_max([minimum, maximum])
            # Add ChimeraX tomogram to the tomo instance
            tomo_instance.set_tomo(volumes[-1])
            # Set default slider positions
            center = np.median(data_matrix)    #current_volume.surfaces[0].level       # Use this as a default until I know a better value
            width = data_matrix.mean()+12.5*data_matrix.std()             # Randomly use 15% of total width
            slice = ma.ceil(0.5*(1+tomo_instance.z_dim))    # Select middle of the stack
            tomo_instance.set_default_positions([center, width, slice])

            self.tomo_list.append(tomo_instance)
            run(session, "set bgColor black")
            run(session, "volume #{} plane z style image".format(volumes[-1].id_string + " imageMode " + '"full region"'))

            self.options_window.group_pixel_size_pixlabel.setText(str(current_volume.data.step[0]))
        # Reset tomo filepath
        self.tomo_filepath = None

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def load_motl_pressed(self, session):
        self.motl_filename = None
        # Open file dialog to open the motivelist (EM file)
        self.select = self.file_dialog_open.exec()

        if self.select:
            self.motl_filename = self.file_dialog_open.selectedFiles()

        if self.motl_filename == None:
            print("No motivelist selected.")
        else:
            motl_name = os.path.basename(self.motl_filename[0])
            motl_data = emread(self.motl_filename[0])
            motl_data = np.ndarray.tolist(motl_data[0])

            row = self.table_motl.rowCount()
            # Create a Motivelist instance and add to the list of Motivelists
            from .object_settings import MotlInstance
            motl_instance = MotlInstance(motl_name, row, len(self.motl_list))

            # Get an unused ID to assign the markers to
            id = self.get_unused_id(session)
            pixel_size=float(self.options_window.group_pixel_size_pixlabel.text())
            for i in range(len(motl_data)):
                # Get the coordinates and radius
                radius = motl_data[i][2]
                x_coord = ((motl_data[i][7]+motl_data[i][10])*pixel_size)-1
                y_coord = ((motl_data[i][8]+motl_data[i][11])*pixel_size)-1
                z_coord = ((motl_data[i][9]+motl_data[i][12])*pixel_size)-1
                print(x_coord,y_coord,z_coord,pixel_size)
                # Assign found id to markers and place them
                run(session, "marker #{} position {},{},{} radius {}".format(id, x_coord, y_coord, z_coord, 4))

            # Select all markers using the given ID
            run(session, "select #{}".format(id))
            markers = [model for model in session.models.list() if model.id_string == str(id)]
            for marker in markers:
                # And color all in the default color
                marker.color = [0, 0, 255, 255]

            # Add the marker instance to the motl instance
            markers = selected_markers(session)
            motl_instance.add_marker(markers, id, motl_data)

            # Update the table
            self.table_add_row(session, 2, motl_name)

            # Add motl instance to the motl list
            self.motl_list.append(motl_instance)


        self.motl_filename = None

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def save_motl_pressed(self, session):
        if self.motl_selected_instance == None:
            print("Please select a motivelist to save.")
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
            self.table_motl.setItem(self.motl_selected_instance.table_row, 0, QTableWidgetItem(motl_filename))

            # Store data in a numpy array
            pixel_size = float(self.options_window.group_pixel_size_pixlabel.text())
            em_data = np.asarray([s[:20] for s in self.motl_selected_instance.motivelist])
            print(em_data.shape)
            for i in range(em_data.shape[0]):
                em_data[i][7]=(em_data[i][7]+1)/pixel_size
                em_data[i][8]=(em_data[i][8]+1)/pixel_size
                em_data[i][9]=(em_data[i][9]+1)/pixel_size
            # Save the data in the corresponding path
            emwrite(em_data, self.motl_filename[0])


# ==============================================================================
# Main Window Functions ========================================================
# ==============================================================================


    def tomo_close_button_pressed(self, session):
        # This button only works if a tomo from the table is selected
        if self.tomo_selected_instance == None:
            print("Error: Please select a tomogram from the table")
        else:
            # Close the tomogram
            self.tomo_selected_instance.volume.delete()

            # Update the row/index in all tomo instances with larger row/index number
            for instance in self.tomo_list:
                if instance.table_row > self.tomo_selected_instance.table_row:
                    instance.table_row -= 1
                if instance.list_index > self.tomo_selected_instance.list_index:
                    instance.list_index -= 1
            # Delete the row
            self.table_tomo.removeRow(self.tomo_selected_instance.table_row)
            # Reconnect all the QCheckBoxes with the right variables

            # Remove the motl from the motl_list
            self.tomo_list.remove(self.tomo_selected_instance)

            # It is also nice to have a message printed in the Log that
            # The tomogram got closed
            print("{} has been closed.".format(self.tomo_selected_instance.name))

            # Since this function is only executed when a tomo instance is selected
            # The options menu needs to be closed when the tomogram is closed
            self.options_window.change_gui(session, "default")

            # And finally set the selected tomo instance to default
            self.tomo_selected_instance = None
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def motl_create_button_pressed(self, session):

        # Create a new motl instance with a default name
        number_rows = self.table_motl.rowCount()
        name = "Motivelist {}".format(number_rows + 1)
        from .object_settings import MotlInstance
        motl_instance = MotlInstance(name, number_rows, len(self.motl_list))

        # Append motl instance in motl list
        self.motl_list.append(motl_instance)
        # Update motl table (table_motl)
        self.table_add_row(session=session, table_number=2, name=name)

        run(session,"mousemode leftMode "+'"mark plane"')
        run(session,"mousemode rightMode select")
        run(session,"mousemode middleMode " + '"delete markers"')

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def motl_close_button_pressed(self, session):
        # This button only works if a motl instance from the table is selected
        if self.motl_selected_instance == None:
            print("Error: Please select a motivelist from the table.")
        else:
            # Close all the objects in the motivelist
            for i in range(len(self.motl_selected_instance.motivelist)):
                object = self.motl_selected_instance.motivelist[i][20]
                object.delete()                          # Remove the object

            # Update the row/index in all motl instances with larger row/index number
            for instance in self.motl_list:
                if instance.table_row > self.motl_selected_instance.table_row:
                    instance.table_row -= 1
                if instance.list_index > self.motl_selected_instance.list_index:
                    instance.list_index -= 1
            # Delete the row
            self.table_motl.removeRow(self.motl_selected_instance.table_row)
            # Reconnect all the QCheckBoxes with the right variables


            # Remove the motl from the motl_list
            self.motl_list.remove(self.motl_selected_instance)

            # It is also nice to have a message printed in the Log that
            # The tomogram got closed
            print("{} has been closed.".format(self.motl_selected_instance.name))

            # Also update the options window
            self.options_window.change_gui(session, "default")
            self.options_window.group_pixel_size_pixlabel.setText("1.0")

            # And finally set the selected tomo instance to default
            self.motl_selected_instance = None


# ==============================================================================
# Table Functions ==============================================================
# ==============================================================================


    def table_add_row(self, session, table_number, name, obj_name=None):
        if table_number == 1:
            # Get the number of rows and expand table by one row
            number_rows = self.table_tomo.rowCount()
            self.table_tomo.setRowCount(number_rows + 1)

            # Define Checkboxes for show and options
            table_tomo_show_box = QCheckBox()
            table_tomo_options_box = QCheckBox()
            # Set the check stati
            table_tomo_show_box.setCheckState(Qt.Checked)
            table_tomo_options_box.setCheckState(Qt.Unchecked)
            # Connect the Items to a function
            table_tomo_show_box.stateChanged.connect(partial(self.table_box_clicked, session, 1, "show", number_rows))
            table_tomo_options_box.stateChanged.connect(partial(self.table_box_clicked, session, 1, "options", number_rows))

            # Print the entries of the table
            self.table_tomo.setItem(number_rows, 0, QTableWidgetItem(name))
            self.table_tomo.setCellWidget(number_rows, 1, table_tomo_show_box)
            self.table_tomo.setCellWidget(number_rows, 2, table_tomo_options_box)

        elif table_number == 2:
            # Get the number of rows and expand table by one row
            number_rows = self.table_motl.rowCount()
            self.table_motl.setRowCount(number_rows + 1)

            # Define Checkboxes for show and options
            table_motl_show_box = QCheckBox()
            table_motl_options_box = QCheckBox()

            # Set the check state
            table_motl_show_box.setCheckState(Qt.Checked)
            table_motl_options_box.setCheckState(Qt.Unchecked)

            # Connect the Items to a function
            table_motl_show_box.stateChanged.connect(partial(self.table_box_clicked, session, 2, "show", number_rows))
            table_motl_options_box.stateChanged.connect(partial(self.table_box_clicked, session, 2, "options", number_rows))

            # Print the entries of the table
            self.table_motl.setItem(number_rows, 0, QTableWidgetItem(name))
            #self.table_motl.setItem(number_rows, 1, QTableWidgetItem(obj_name))
            self.table_motl.setCellWidget(number_rows, 1, table_motl_show_box)
            self.table_motl.setCellWidget(number_rows, 2, table_motl_options_box)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def table_box_clicked(self, session, table_number, option, row):
        # Initialize the instance
        instance = None
        # This function needs a safety switch so that it is only executed when
        # The checkbox is changed manually -> Disabled when setCheckState is used
        if self.execution_switch:
            if table_number == 1:
                if option == "show":
                    # Select the right tomo instance
                    for i in range(len(self.tomo_list)):
                        if self.tomo_list[i].table_row == row:
                            instance = self.tomo_list[i]
                    item = self.table_tomo.cellWidget(row, 1)
                    # The function receives the updated state of the QCheckBox
                    if item.isChecked():    # Show
                        instance.shown = True
                        instance.volume.show(show=True)
                    else:                   # Hide
                        instance.shown = False
                        instance.volume.show(show=False)
                elif option == "options":
                    # Select the right tomo instance
                    for i in range(len(self.tomo_list)):
                        if self.tomo_list[i].table_row == row:
                            instance = self.tomo_list[i]

                    item = self.table_tomo.cellWidget(row, 2)
                    state = item.isChecked()    # Save the current check state
                    # The function receives the updated state of the QCheckBox
                    if state:   # Open options menu in other window
                        # Now uncheck every QCheckBox
                        for i in range(self.table_tomo.rowCount()):
                            options_item = self.table_tomo.cellWidget(i, 2)
                            # Switch execution switch
                            self.execution_switch = False
                            options_item.setCheckState(Qt.Unchecked)
                            self.execution_switch = True
                        # And uncheck the options state in the tomo instances
                        for i in range(len(self.tomo_list)):
                            self.tomo_list[i].options = False
                        # Check the originally selected Box again
                        self.execution_switch = False
                        item.setCheckState(Qt.Checked)
                        self.execution_switch = True
                        # Also update the corresponding tomo instance
                        instance.options = True
                        # Set the globally accessible tomo instance
                        self.tomo_selected_instance = instance
                        # Finally update the options window
                        self.options_window.change_gui(session, "tomo", self.tomo_selected_instance)
                    else:       # Set options window back to default
                        # Close the options menu and update the options state in the tomo instance
                        instance.options = False
                        # Free the globally accessible tomo instance
                        self.tomo_selected_instance = None
                        # Update the options window
                        self.options_window.change_gui(session, "default")

            elif table_number == 2:
                if option == "show":
                    # Select the right motl instance
                    for i in range(len(self.motl_list)):
                        if self.motl_list[i].table_row == row:
                            instance = self.motl_list[i]
                    item = self.table_motl.cellWidget(row, 1)
                    obj_list = [particle[20] for particle in instance.motivelist]
                    # The function receives the updated state of the QCheckBox
                    if item.isChecked():    # Show
                        instance.shown = True
                        for object in obj_list:
                            if isinstance(object, Volume):
                                object.show(show=True)
                            else:
                                object.hide = False
                    else:                   # Hide
                        instance.shown = False
                        for object in obj_list:
                            if isinstance(object, Volume):
                                object.show(show=False)
                            else:
                                object.hide = True
                elif option == "options":
                    # Select the right motl instance
                    for i in range(len(self.motl_list)):
                        if self.motl_list[i].table_row == row:
                            instance = self.motl_list[i]

                    # print(str(self.table_motl.row(self.table_motl.cellWidget(row, 2)).isChecked))
                    item = self.table_motl.cellWidget(row, 2)
                    state = item.isChecked()    # Save the current check state

                    # The function receives the updated state of the QCheckBox
                    if state:                   # Open options menu in other window
                        # Now uncheck every QCheckBox
                        for i in range(self.table_motl.rowCount()):
                            options_item = self.table_motl.cellWidget(i, 2)
                            self.execution_switch = False
                            options_item.setCheckState(Qt.Unchecked)
                            self.execution_switch = True
                        # And uncheck the view state in the tomo instances
                        for i in range(len(self.motl_list)):
                            self.motl_list[i].options = False
                        # Check the originally selected Box again
                        self.execution_switch = False
                        item.setCheckState(Qt.Checked)
                        self.execution_switch = True
                        # Also update the corresponding tomo instance
                        instance.options = True
                        # Set the globally accessible motl instance
                        self.motl_selected_instance = instance
                        # Finally update the options window and color the markers/objects
                        self.options_window.change_gui(session, "motl", self.motl_selected_instance)
                        self.options_window.motl_color(session, True, 0, self.motl_selected_instance)
                    else:
                        # Close the options menu and update the options state in the tomo instance
                        instance.options = False
                        # Update the options window to default settings
                        self.options_window.change_gui(session, "default")
                        # Color all objects/markers associated with this motivelist in default blue
                        self.options_window.motl_color(session, False, 0, self.motl_selected_instance)
                        # Free the globally accessible motl instance
                        self.motl_selected_instance = None
                        # Unselect everything
                        run(session, "select clear")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def table_cell_clicked(self, session, table_number):
        if table_number == 1:
            item = self.table_tomo.selectedItems()
            column = self.table_tomo.currentColumn()
            row = self.table_tomo.currentRow()
            tomo_instance = None
            # Depending on the row, find the corresponding tomo_instance
            for instance in self.tomo_list:
                if instance.table_row == row:
                    tomo_instance = instance
                    break

            if tomo_instance != None:
                if column == 0:     # Change the name
                    tomo_instance.name = self.table_tomo.item(row, column).text()

        elif table_number == 2:
            item = self.table_motl.selectedItems()
            column = self.table_motl.currentColumn()
            row = self.table_motl.currentRow()
            motl_instance = None
            # Depending on the row, find the corresponding motl instance
            for instance in self.motl_list:
                if instance.table_row == row:
                    motl_instance = instance
                    break

            if motl_instance != None:
                if column == 0:     # Change the name
                    motl_instance.name = self.table_motl.item(row, column).text()
                # elif column == 1:   # Change the object name
                #     motl_instance.obj_name = self.table_motl.item(row, column).text()


# ==============================================================================
# Other Functions ==============================================================
# ==============================================================================


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
# Shortcut Functions ===========================================================
# ==============================================================================

# The following 4 jump functions only work if a tomogram is selected
    def jump_1_forwards_pressed(self, session):
        print("Yes, the shortcut worked.")
        #volume #1 planes z,100


    def jump_10_forwards_pressed(self, session):
        print("Yes, the shortcut worked.")


    def jump_1_backwards_pressed(self, session):
        print("Yes, the shortcut worked.")


    def jump_10_backwards_pressed(self, session):
        print("Yes, the shortcut worked.")


# ==============================================================================
# Options Window ===============================================================
# ==============================================================================


    def _build_options_window(self, session, tool_name):
        # Creates an instance of the new window's class
        self.options_window = OptionsWindow(session, tool_name)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Tomo Functions +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def connect_tomo_functions(self, session):
        #Physical Position
        self.options_window.group_pixelSize_button.clicked.connect(partial(self.ApplypixSize_execute, session))
        self.options_window.group_physPos_button.clicked.connect(partial(self.physPosition_execute, session))
        # Center
        self.options_window.group_contrast_center_edit.returnPressed.connect(partial(self.center_edited, session))
        self.options_window.group_contrast_center_slider.valueChanged.connect(partial(self.center_slider, session))
        self.options_window.group_contrast_center_slider.sliderReleased.connect(partial(self.center_released))
        # Width
        self.options_window.group_contrast_width_edit.returnPressed.connect(partial(self.width_edited, session))
        self.options_window.group_contrast_width_slider.valueChanged.connect(partial(self.width_slider, session))
        self.options_window.group_contrast_width_slider.sliderReleased.connect(partial(self.width_released))
        # Slice
        self.options_window.group_slices_edit.returnPressed.connect(partial(self.slice_edited, session))
        self.options_window.group_slices_slider.valueChanged.connect(partial(self.slice_slider, session))
        self.options_window.group_slices_slider.sliderReleased.connect(partial(self.slice_released))
        # Slices buttons
        self.options_window.group_slices_previous_10.clicked.connect(partial(self.skip_planes, session, -10))
        self.options_window.group_slices_previous_1.clicked.connect(partial(self.skip_planes, session, -1))
        self.options_window.group_slices_next_1.clicked.connect(partial(self.skip_planes, session, 1))
        self.options_window.group_slices_next_10.clicked.connect(partial(self.skip_planes, session, 10))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def ApplypixSize_execute(self, session):

        try:
            pixel_size= float(self.options_window.group_pixel_size_pixlabel.text())
            for i in range(len(self.motl_selected_instance.motivelist)):
                object = self.motl_selected_instance.motivelist[i][20]
                if isinstance(object, Volume):
                    # Get the position matrix from the volume object
                    position_matrix = object.position.matrix
                    # Determine spatial coordinates and rotation angles
                    x_coord = position_matrix[0][3]
                    y_coord = position_matrix[1][3]
                    z_coord = position_matrix[2][3]
                    # Update the coordinates and angles in the motivelist
                    self.motl_selected_instance.motivelist[i][7] = ((x_coord+1)*pixel_size)-1
                    self.motl_selected_instance.motivelist[i][8] = ((y_coord+1)*pixel_size)-1
                    self.motl_selected_instance.motivelist[i][9] = ((z_coord+1)*pixel_size)-1
                else:
                    # From markers only get the positions
                    coords = object.coord
                    # Update the coordinates in the motivelist
                    self.motl_selected_instance.motivelist[i][7] = ((coords[0]+1)*pixel_size)-1
                    self.motl_selected_instance.motivelist[i][8] = ((coords[1]+1)*pixel_size)-1
                    self.motl_selected_instance.motivelist[i][9] = ((coords[2]+1)*pixel_size)-1

            # Update the tomo list with the updated selected tomo instance
            self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance

            obj_list = [particle[20] for particle in self.motl_selected_instance.motivelist]

            for i in range(len(obj_list)):
                object = obj_list[i]
                if isinstance(object, Volume):

                    position_matrix = object.position.matrix
                    # Determine the angles
                    psi, theta, phi = getEulerAngles(position_matrix)
                    # Get coordinates
                    x_coord = self.motl_selected_instance.motivelist[i][7]
                    y_coord = self.motl_selected_instance.motivelist[i][8]
                    z_coord = self.motl_selected_instance.motivelist[i][9]
                    # Set the corresponding rotation-translation matrix
                    matrix = detRotMat(phi, psi, theta)
                    matrix[0].append(x_coord)
                    matrix[1].append(y_coord)
                    matrix[2].append(z_coord)

                    # Prepare the command
                    id  = self.motl_selected_instance.motivelist[i][21]
                    command = "view matrix models #{}".format(id)
                    for i in range(3):
                        for j in range(4):
                            command += ",{}".format(matrix[i][j])
                    run(session, command)
                else:

                    # Get coordinates and angles
                    x_coord = self.motl_selected_instance.motivelist[i][7]
                    y_coord = self.motl_selected_instance.motivelist[i][8]
                    z_coord = self.motl_selected_instance.motivelist[i][9]
                    # Reset the marker position
                    object.coord = [x_coord, y_coord, z_coord]

            # Update the tomo list with the updated selected tomo instance
            self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance

        except:
            print("Error: Please insert a valid number.")


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def physPosition_execute(self, session):

        try:
            pixel_size= float(self.options_window.group_pixel_size_pixlabel.text())
            markers = selected_markers(session)
            for marker in markers:
                coords = marker.coord
                # show the physical position
                self.options_window.group_pixel_size_labelx.setText(str(round(((coords[0]+1)*pixel_size)/pixel_size, 3)))
                self.options_window.group_pixel_size_labely.setText(str(round(((coords[1]+1)*pixel_size)/pixel_size, 3)))
                self.options_window.group_pixel_size_labelz.setText(str(round(((coords[2]+1)*pixel_size)/pixel_size, 3)))


        except:
            print("Error: invalid object.")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def center_edited(self, session):
        try:
            # Get text from edit
            value = float(self.options_window.group_contrast_center_edit.text())
            # Set value in slider
            self.options_window.group_contrast_center_slider.setValue(int(10000*value))
            # Update the center position in the tomo instance
            self.tomo_selected_instance.center_position = value
            self.tomo_selected_instance.use_save_settings = True
            # Update the tomo list with the updated selected tomo instance
            self.tomo_list[self.tomo_selected_instance.list_index] = self.tomo_selected_instance
            # Execute the center function
            self.options_window.center_execute(session, value, self.tomo_selected_instance)
        except:
            print("Error: Please insert a number.")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def center_slider(self, session):
        # Get the value from the slider
        value = self.options_window.group_contrast_center_slider.value()
        # Set value in edit
        self.options_window.group_contrast_center_edit.setText(str(value/10000))
        # Execute the center function
        self.options_window.center_execute(session, value/10000, self.tomo_selected_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def center_released(self):
        # Get the value from the slider
        value = self.options_window.group_contrast_center_slider.value()
        # Update the center position in the tomo instance
        self.tomo_selected_instance.center_position = value/10000
        self.tomo_selected_instance.use_save_settings = True
        # Update the tomo list with the updated selected tomo instance
        self.tomo_list[self.tomo_selected_instance.list_index] = self.tomo_selected_instance

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def width_edited(self, session):
        try:
            # Get text from edit
            value = float(self.options_window.group_contrast_width_edit.text())
            # Set value in slider
            self.options_window.group_contrast_width_slider.setValue(int(10000*value))
            # Update the width position in the tomo instance
            self.tomo_selected_instance.width_position = value
            self.tomo_selected_instance.use_save_settings = True
            # Update the tomo list with the updated selected tomo instance
            self.tomo_list[self.tomo_selected_instance.list_index] = self.tomo_selected_instance
            # Execute the width function
            self.options_window.width_execute(session, value, self.tomo_selected_instance)
        except:
            print("Error: Please insert a number")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def width_slider(self, session):
        # Get the value from the slider
        value = self.options_window.group_contrast_width_slider.value()
        # Set value in edit
        self.options_window.group_contrast_width_edit.setText(str(value/10000))
        # Execute the width function
        self.options_window.width_execute(session, value/10000, self.tomo_selected_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def width_released(self):
        # Get the value from the slider
        value = self.options_window.group_contrast_width_slider.value()
        # Update the width position in the tomo instance
        self.tomo_selected_instance.width_position = value/10000
        self.tomo_selected_instance.use_save_settings = True
        # Update the tomo list with the updated selected tomo instance
        self.tomo_list[self.tomo_selected_instance.list_index] = self.tomo_selected_instance

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def slice_edited(self, session):
        try:
            # Get text from edit
            value = float(self.options_window.group_slices_edit.text())
            # Set value in slider
            self.options_window.group_slices_slider.setValue(int(value))
            # Update the slice position in the tomo instance
            self.tomo_selected_instance.slice_position = value
            self.tomo_selected_instance.use_save_settings = True
            # Update the tomo list with the updated selected tomo instance
            self.tomo_list[self.tomo_selected_instance.list_index] = self.tomo_selected_instance
            # Execute the slice function
            self.options_window.slice_execute(session, value, self.tomo_selected_instance)
        except:
            print("Error: Please insert a number.")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def slice_slider(self, session):
        # Get the value from the slider
        value = self.options_window.group_slices_slider.value()
        # Set value in edit
        self.options_window.group_slices_edit.setText(str(value))
        # Execute the slice function
        self.options_window.slice_execute(session, value, self.tomo_selected_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def slice_released(self):
        # Get the value from the slider
        value = self.options_window.group_slices_slider.value()
        # Update the slice position in the tomo instance
        self.tomo_selected_instance.slice_position = value
        self.tomo_selected_instance.use_save_settings = True
        # Update the tomo list with the updated selected tomo instance
        self.tomo_list[self.tomo_selected_instance.list_index] = self.tomo_selected_instance

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def skip_planes(self, session, number):
        # Update the slice position in the tomo instance
        if self.tomo_selected_instance.slice_position + number > self.tomo_selected_instance.z_dim:
            self.tomo_selected_instance.slice_position = self.tomo_selected_instance.z_dim
        elif self.tomo_selected_instance.slice_position + number < 1:
            self.tomo_selected_instance.slice_position = 1
        else:
            self.tomo_selected_instance.slice_position = self.tomo_selected_instance.slice_position + number
        # Update the slider and edit value
        self.options_window.group_slices_edit.setText(str(self.tomo_selected_instance.slice_position))
        self.options_window.group_slices_slider.setValue(self.tomo_selected_instance.slice_position)
        # Update the tomo list with the updated selected tomo instance
        self.tomo_list[self.tomo_selected_instance.list_index] = self.tomo_selected_instance
        # Execute the slice function
        self.options_window.slice_execute(session, self.tomo_selected_instance.slice_position, self.tomo_selected_instance)


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Motl Functions +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def connect_motl_functions(self, session):
        # Select slider
        self.options_window.group_select_selection_edit.returnPressed.connect(partial(self.selection_edit, session))
        #self.options_window.group_select_selection_slider.valueChanged.connect(partial(self.selection_slider, session))
        #self.options_window.group_select_selection_slider.sliderReleased.connect(partial(self.selection_released))
        # Row 1 Slider
        self.options_window.group_select_row1_edit.returnPressed.connect(partial(self.row1_edit, session))
        self.options_window.group_select_row1_slider.valueChanged.connect(partial(self.row1_slider, session))
        # Row 2 Slider
        self.options_window.group_select_row2_edit.returnPressed.connect(partial(self.row2_edit, session))
        self.options_window.group_select_row2_slider.valueChanged.connect(partial(self.row2_slider, session))
        # Variable Slider
        self.options_window.group_select_variable_edit.returnPressed.connect(partial(self.variable_edit, session))
        self.options_window.group_select_variable_slider.valueChanged.connect(partial(self.variable_slider, session))
        self.options_window.group_select_variable_slider.sliderReleased.connect(partial(self.variable_released))
        # Lower threshold 1
        self.options_window.group_select_lower_thresh_edit.returnPressed.connect(partial(self.lower_thresh_edit, session))
        self.options_window.group_select_lower_thresh_slider.valueChanged.connect(partial(self.lower_thresh_slider, session))
        # Upper threshold 1
        self.options_window.group_select_upper_thresh_edit.returnPressed.connect(partial(self.upper_thresh_edit, session))
        self.options_window.group_select_upper_thresh_slider.valueChanged.connect(partial(self.upper_thresh_slider, session))
        # Lower threshold 2
        self.options_window.group_select_lower_thresh_edit2.returnPressed.connect(partial(self.lower_thresh_edit2, session))
        self.options_window.group_select_lower_thresh_slider2.valueChanged.connect(partial(self.lower_thresh_slider2, session))
        # Upper threshold 2
        self.options_window.group_select_upper_thresh_edit2.returnPressed.connect(partial(self.upper_thresh_edit2, session))
        self.options_window.group_select_upper_thresh_slider2.valueChanged.connect(partial(self.upper_thresh_slider2, session))
        # Add all the buttons here
        self.options_window.group_manipulation_update_button.clicked.connect(partial(self.update_button_pressed, session))
        self.options_window.group_manipulation_add_button.clicked.connect(partial(self.add_button_pressed, session))
        self.options_window.group_manipulation_print_button.clicked.connect(partial(self.print_button_pressed, session))
        self.options_window.group_manipulation_delete_button.clicked.connect(partial(self.delete_button_pressed, session))
        self.options_window.group_manipulation_reset_single_button.clicked.connect(partial(self.reset_selected_pressed, session))
        self.options_window.group_manipulation_reset_all_button.clicked.connect(partial(self.reset_all_pressed, session))
        # Add the Browse options
        self.options_window.browse_edit.returnPressed.connect(partial(self.browse_edited, session))
        self.options_window.browse_button.clicked.connect(partial(self.browse_pushed, session))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def selection_edit(self, session):

        #run(session,"mousemode right select")
        # try:
        #     markers = selected_markers(session)
        #     for i in markers:
        #         i.id
        # except:
        #     print("Error: Please enter a number")

        # Get text from edit
        value = int(self.options_window.group_select_selection_edit.text())
        # Update the selection position in the tomo instance
        self.motl_selected_instance.selection_position = value
        # Update the tomo list with the updated selected tomo instance
        self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance


        # Execute the selection function
        if value == 0:
            self.options_window.select_execute(session, value, self.motl_selected_instance)

        elif value != 0 and (not value > len(self.motl_selected_instance.motivelist[:][20])):
            object = self.motl_selected_instance.motivelist[value-1][20]
            # print(object)
            # if (not isinstance(object, Volume)) and (isinstance(object, Atom)) :
            #     self.options_window.select_execute(session, value, self.motl_selected_instance)
            if (not isinstance(object, Volume)) and (not isinstance(object, Atom)):
                model = session.models[value-1]
                print(model)
                if isinstance(model, Surface):
                    self.options_window.select_surface_execute(session, value)

        elif value != 0 and ((value) <= len(session.models.list())) and (value > len(self.motl_selected_instance.motivelist[:][20])):
            model = session.models[value-1]
            print(model)
            if isinstance(model, Surface):
                self.options_window.select_surface_execute(session, value)

        else:
            print("Error: Please enter a valid number")


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # def selection_slider(self, session):
    #     run(session,"mousemode right select")
    #     # Get the value from the slider
    #     value = self.options_window.group_select_selection_slider.value()
    #     # Set value in edit
    #     self.options_window.group_select_selection_edit.setText(str(value))
    #     # Execute the slice function
    #     self.options_window.select_execute(session, value, self.motl_selected_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # def selection_released(self):
    #     run(session,"mousemode right select")
    #     # Get the value from the slider
    #     value = self.options_window.group_select_selection_slider.value()
    #     # Update the selection position in the tomo instance
    #     self.motl_selected_instance.selection_position = value
    #     # Update the tomo list with the updated selected tomo instance
    #     self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def row1_edit(self, session):
        try:
            # Get text from edit
            value = int(self.options_window.group_select_row1_edit.text())
            # Set value in slider
            self.options_window.group_select_row1_slider.setValue(int(value))
            # Update the selection position in the tomo instance
            self.motl_selected_instance.row1_position = value
            # Update the tomo list with the updated selected tomo instance
            self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance
            # Execute the slice function
            self.options_window.row1_execute(session, value, self.motl_selected_instance)
        except:
            print("Error: Please enter a number")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def row2_edit(self, session):
        try:
            # Get text from edit
            value = int(self.options_window.group_select_row2_edit.text())
            # Set value in slider
            self.options_window.group_select_row2_slider.setValue(int(value))
            # Update the selection position in the tomo instance
            self.motl_selected_instance.row2_position = value
            # Update the tomo list with the updated selected tomo instance
            self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance
            # Execute the slice function
            self.options_window.row2_execute(session, value, self.motl_selected_instance)
        except:
            print("Error: Please enter a number")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def row1_slider(self, session):
        # Get the value from the slider
        value = int(self.options_window.group_select_row1_slider.value())
        # Set value in edit
        self.options_window.group_select_row1_edit.setText(str(value))
        # The row property of the motl instance needs to be updated instantly
        # As this is needed for the threshold sliders
        self.motl_selected_instance.row1_position = value
        # Update the tomo list with the updated selected tomo instance
        self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance
        # Execute the slice function
        self.options_window.row1_execute(session, value, self.motl_selected_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def row2_slider(self, session):
        # Get the value from the slider
        value = int(self.options_window.group_select_row2_slider.value())
        # Set value in edit
        self.options_window.group_select_row2_edit.setText(str(value))
        # The row property of the motl instance needs to be updated instantly
        # As this is needed for the threshold sliders
        self.motl_selected_instance.row2_position = value
        # Update the tomo list with the updated selected tomo instance
        self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance
        # Execute the slice function
        self.options_window.row2_execute(session, value, self.motl_selected_instance)


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def lower_thresh_edit(self, session):
        try:
            # Get lower and upper threshold from the LineEdits
            lower_value1 = float(self.options_window.group_select_lower_thresh_edit.text())
            upper_value1 = float(self.options_window.group_select_upper_thresh_edit.text())
            lower_value2 = float(self.options_window.group_select_lower_thresh_edit2.text())
            upper_value2 = float(self.options_window.group_select_upper_thresh_edit2.text())
            if self.motl_selected_instance.row1_position == 1:
                # Set value in slider
                self.options_window.group_select_lower_thresh_slider.setValue(int(100*lower_value1))
                # Execute lower threshold function
                self.options_window.threshold_execute(session, 100*lower_value1, 100*upper_value1, lower_value2, upper_value2, self.motl_selected_instance)
            else:
                # Set value in slider
                self.options_window.group_select_lower_thresh_slider.setValue(int(lower_value))
                # Execute lower threshold function
                self.options_window.threshold_execute(session, lower_value1, upper_value1, lower_value2, upper_value2, self.motl_selected_instance)
        except:
            print("Error: Please enter a number")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def lower_thresh_slider(self, session):
        # Get lower and upper threshold from the slider
        lower_value1 = self.options_window.group_select_lower_thresh_slider.value()
        upper_value1 = self.options_window.group_select_upper_thresh_slider.value()
        lower_value2 = self.options_window.group_select_lower_thresh_slider2.value()
        upper_value2 = self.options_window.group_select_upper_thresh_slider2.value()
        if self.motl_selected_instance.row1_position == 1:
            # Set value in edit
            self.options_window.group_select_lower_thresh_edit.setText(str(lower_value1/100))
            # Execute the lower threshold function
            self.options_window.threshold_execute(session, lower_value1/100, upper_value1/100, lower_value2, upper_value2, self.motl_selected_instance)
        else:
            # Set value in edit
            self.options_window.group_select_lower_thresh_edit.setText(str(lower_value1))
            # Execute the lower threshold function
            self.options_window.threshold_execute(session, lower_value1, upper_value1, lower_value2, upper_value2, self.motl_selected_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def upper_thresh_edit(self, session):
        try:
            # Get lower and upper threshold from the LineEdits
            lower_value1 = float(self.options_window.group_select_lower_thresh_edit.text())
            upper_value1 = float(self.options_window.group_select_upper_thresh_edit.text())
            lower_value2 = float(self.options_window.group_select_lower_thresh_edit2.text())
            upper_value2 = float(self.options_window.group_select_upper_thresh_edit2.text())
            if self.motl_selected_instance.row1_position == 1:
                # Set value in slider
                self.options_window.group_select_upper_thresh_slider.setValue(int(100*upper_value1))
                # Execute upper thresh funtion
                self.options_window.threshold_execute(session, 100*lower_value1, 100*upper_value1, lower_value2, upper_value2, self.motl_selected_instance)
            else:
                # Set value in slider
                self.options_window.group_select_upper_thresh_slider.setValue(int(upper_value1))
                # Execute upper thresh funtion
                self.options_window.threshold_execute(session, lower_value1, upper_value1, lower_value2, upper_value2, self.motl_selected_instance)
        except:
            print("Error: Please enter a number")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def upper_thresh_slider(self, session):
        # Get lower and upper threshold from the slider
        lower_value1 = self.options_window.group_select_lower_thresh_slider.value()
        upper_value1 = self.options_window.group_select_upper_thresh_slider.value()
        lower_value2 = self.options_window.group_select_lower_thresh_slider2.value()
        upper_value2 = self.options_window.group_select_upper_thresh_slider2.value()
        if self.motl_selected_instance.row1_position == 1:
            # Set value in edit
            self.options_window.group_select_upper_thresh_edit.setText(str(upper_value1/100))
            # Execute the upper threshold function
            self.options_window.threshold_execute(session, lower_value1/100, upper_value1/100, lower_value2, upper_value2, self.motl_selected_instance)
        else:
            # Set value in edit
            self.options_window.group_select_upper_thresh_edit.setText(str(upper_value1))
            # Execute the upper threshold function
            self.options_window.threshold_execute(session, lower_value1, upper_value1, lower_value2, upper_value2, self.motl_selected_instance)


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def lower_thresh_edit2(self, session):
        try:
            # Get lower and upper threshold from the LineEdits
            lower_value1 = float(self.options_window.group_select_lower_thresh_edit.text())
            upper_value1 = float(self.options_window.group_select_upper_thresh_edit.text())
            lower_value2 = float(self.options_window.group_select_lower_thresh_edit2.text())
            upper_value2 = float(self.options_window.group_select_upper_thresh_edit2.text())
            if self.motl_selected_instance.row2_position == 1:
                # Set value in slider
                self.options_window.group_select_lower_thresh_slider2.setValue(int(100*lower_value2))
                # Execute lower threshold function
                self.options_window.threshold_execute(session, lower_value1, upper_value1, 100*lower_value2, 100*upper_value2, self.motl_selected_instance)
            else:
                # Set value in slider
                self.options_window.group_select_lower_thresh_slider2.setValue(int(lower_value2))
                # Execute lower threshold function
                self.options_window.threshold_execute(session, lower_value1, upper_value1, lower_value2, upper_value2, self.motl_selected_instance)
        except:
            print("Error: Please enter a number")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def lower_thresh_slider2(self, session):
        # Get lower and upper threshold from the slider
        lower_value1 = self.options_window.group_select_lower_thresh_slider.value()
        upper_value1 = self.options_window.group_select_upper_thresh_slider.value()
        lower_value2 = self.options_window.group_select_lower_thresh_slider2.value()
        upper_value2 = self.options_window.group_select_upper_thresh_slider2.value()
        if self.motl_selected_instance.row2_position == 1:
            # Set value in edit
            self.options_window.group_select_lower_thresh_edit2.setText(str(lower_value2/100))
            # Execute the lower threshold function
            self.options_window.threshold_execute(session, lower_value1, upper_value1, lower_value2/100, upper_value2/100, self.motl_selected_instance)
        else:
            # Set value in edit
            self.options_window.group_select_lower_thresh_edit2.setText(str(lower_value2))
            # Execute the lower threshold function
            self.options_window.threshold_execute(session, lower_value1, upper_value1, lower_value2, upper_value2, self.motl_selected_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def upper_thresh_edit2(self, session):
        try:
            # Get lower and upper threshold from the LineEdits
            lower_value1 = float(self.options_window.group_select_lower_thresh_edit.text())
            upper_value1 = float(self.options_window.group_select_upper_thresh_edit.text())
            lower_value2 = float(self.options_window.group_select_lower_thresh_edit2.text())
            upper_value2 = float(self.options_window.group_select_upper_thresh_edit2.text())
            if self.motl_selected_instance.row2_position == 1:
                # Set value in slider
                self.options_window.group_select_upper_thresh_slider2.setValue(int(100*upper_value2))
                # Execute upper thresh funtion
                self.options_window.threshold_execute(session, lower_value1, upper_value1, 100*lower_value2, 100*upper_value2, self.motl_selected_instance)
            else:
                # Set value in slider
                self.options_window.group_select_upper_thresh_slider2.setValue(int(upper_value2))
                # Execute upper thresh funtion
                self.options_window.threshold_execute(session, lower_value1, upper_value1, lower_value2, upper_value2, self.motl_selected_instance)
        except:
            print("Error: Please enter a number")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def upper_thresh_slider2(self, session):
        # Get lower and upper threshold from the slider
        lower_value1 = self.options_window.group_select_lower_thresh_slider.value()
        upper_value1 = self.options_window.group_select_upper_thresh_slider.value()
        lower_value2 = self.options_window.group_select_lower_thresh_slider2.value()
        upper_value2 = self.options_window.group_select_upper_thresh_slider2.value()
        if self.motl_selected_instance.row2_position == 1:
            # Set value in edit
            self.options_window.group_select_upper_thresh_edit2.setText(str(upper_value2/100))
            # Execute the upper threshold function
            self.options_window.threshold_execute(session, lower_value1, upper_value1, lower_value2/100, upper_value2/100, self.motl_selected_instance)
        else:
            # Set value in edit
            self.options_window.group_select_upper_thresh_edit2.setText(str(upper_value2))
            # Execute the upper threshold function
            self.options_window.threshold_execute(session, lower_value1, upper_value1, lower_value2, upper_value2, self.motl_selected_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def variable_edit(self, session):
        if self.motl_selected_instance.obj_filepath == None:    # Do the radius edit
            try:
                # Get text from edit
                value = float(self.options_window.group_select_variable_edit.text())
                # Set value in slider
                self.options_window.group_select_variable_slider.setValue(int(10*value))
                # Update the selection position in the tomo instance
                self.motl_selected_instance.radius_position = value
                # Update the tomo list with the updated selected tomo instance
                self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance
                # Execute the radius function
                self.options_window.radius_execute(session, value, self.motl_selected_instance)
            except:
                print("Error: Please enter a number")
        else:                       # Do the surface edit
            try:
                # Get text from edit
                value = float(self.options_window.group_select_variable_edit.text())
                # Set value in slider
                self.options_window.group_select_variable_slider.setValue(int(100*value))
                # Update the selection position in the tomo instance
                self.motl_selected_instance.surface_position = value
                # Update the tomo list with the updated selected tomo instance
                self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance
                # Execute the surface function
                self.options_window.surface_execute(session, value, self.motl_selected_instance)
            except:
                print("Error: Please enter a number")

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def variable_slider(self, session):
        if self.motl_selected_instance.obj_filepath == None:     # Do the radius slider
            # Get the value from the slider
            value = self.options_window.group_select_variable_slider.value()
            # Set value in edit
            self.options_window.group_select_variable_edit.setText(str(value/10))
            # Execute the radius function
            self.options_window.radius_execute(session, value/10, self.motl_selected_instance)
        else:                                                    # Do the surface slider
            # Get the value from the slider
            value = self.options_window.group_select_variable_slider.value()
            # Set value in edit
            self.options_window.group_select_variable_edit.setText(str(value/100))
            # Execute the surface function
            self.options_window.surface_execute(session, value/100, self.motl_selected_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def variable_released(self):
        # Get the value from the slider
        value = self.options_window.group_select_variable_slider.value()
        if self.motl_selected_instance.obj_filepath == None:    # Save radius position
            self.motl_selected_instance.radius_position = value/10
        else:                                                   # Save surface position
            self.motl_selected_instance.surface_position = value/100
        # Update the tomo list with the updated selected tomo instance
        self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def update_button_pressed(self, session):

        # Update position and rotation
        for i in range(len(self.motl_selected_instance.motivelist)):
            object = self.motl_selected_instance.motivelist[i][20]
            if isinstance(object, Volume):
                # Get the position matrix from the volume object
                position_matrix = object.position.matrix
                # Determine spatial coordinates and rotation angles
                x_coord = position_matrix[0][3]
                y_coord = position_matrix[1][3]
                z_coord = position_matrix[2][3]
                # Also get the angles
                psi, theta, phi = getEulerAngles(position_matrix)
                # Update the coordinates and angles in the motivelist
                self.motl_selected_instance.motivelist[i][7] = x_coord
                self.motl_selected_instance.motivelist[i][8] = y_coord
                self.motl_selected_instance.motivelist[i][9] = z_coord
                self.motl_selected_instance.motivelist[i][16] = phi
                self.motl_selected_instance.motivelist[i][17] = psi
                self.motl_selected_instance.motivelist[i][18] = theta
            else:
                # From markers only get the positions
                coords = object.coord
                # Update the coordinates in the motivelist
                self.motl_selected_instance.motivelist[i][7] = coords[0]
                self.motl_selected_instance.motivelist[i][8] = coords[1]
                self.motl_selected_instance.motivelist[i][9] = coords[2]

        # Update the tomo list with the updated selected tomo instance
        self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def add_button_pressed(self, session):
        # We want to add all markers to the selected motivelist -> Not those
        # That are already part of the motivelist

        run(session,"mousemode rightMode "+'"rotate and select"')
        run(session,"mousemode middleMode "+'"rotate selected atoms"')
        run(session,"mousemode leftMode "+'"translate selected atoms"')

        # At first get all the markers in a set
        marker_set = [markerset for markerset in session.models.list() if isinstance(markerset, MarkerSet) ]
        # Get all the objects associated with the motivelist
        obj_list = []
        for motivelist in self.motl_list:
            for particle in motivelist.motivelist:
                obj_list.append(particle[20])
        # Define a list of all the markers that shall be added
        marker_instance = []


        # If no volume for the motivelist has been selected, check which of the
        # Markers still need to be added to motivelist
        if self.motl_selected_instance.obj_name == None:
            # Get the existing ID from the other markers
            id = [set for set in session.models.list() if isinstance(set, MarkerSet)][0].id_string
            # Go through all markers of the set -> If not part of motivelist, add it
            for set in marker_set:          # Go through all marker sets (in case there are more than one)
                for marker in set.atoms:    # Go through all atoms of selected set
                    if (marker not in obj_list) and (marker.hide == False):
                        marker_instance.append(marker)
                        # Color the marker in selected blue
                        marker.color = [0, 255, 255, 255]
                    else:
                        print("{} skipped because already part of motivelist.".format(marker))

            # Now we have a list of all markers that shall be added to the motivelist
            self.motl_selected_instance.add_marker(marker_instance, id)
            # Update the sliders
            self.options_window.build_motl_sliders(session, self.motl_selected_instance)
            # Update the tomo list with the updated selected tomo instance
            self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance

        else:   # Add markers to motivelist and show them as selected volume
            for set in marker_set:
                for marker in set.atoms :
                    if marker.hide == False :
                        marker_instance.append(marker)

            # Add the markers as Volumes
            self.motl_selected_instance.add_marker_as_volume(session, marker_instance)
            # Update the sliders
            self.options_window.build_motl_sliders(session, self.motl_selected_instance)
            # Update the tomo list with the updated selected tomo instance
            self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance



# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #
    # def select_via_DblClick(self, session, event: QMouseEvent ):
    #
    #     if  event.MouseButtonDblClick:
    #
    #         run(session, "redo")
    #         if self.group_select_selection_clampview.isChecked():
    #             run(session,"view sel clip false pad  0.9")
    #
    #         return
    #
    #     else :
    #
    #         return

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


    def print_button_pressed(self, session):
        # Print the selected motivelist
        for i in range(len(self.motl_selected_instance.motivelist)):
            print("Particle {}:".format(i+1), self.motl_selected_instance.motivelist[i][:20])

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def delete_button_pressed(self, session):
        # Delete the selected markers from the motivelist
        markers = selected_markers(session)
        for marker in markers:
            object_list = []        # Object list needs to be updated everytime a marker gets remove so the indices are still correct
            object_list = [particle[20] for particle in self.motl_selected_instance.motivelist]
            if marker in object_list:   # Delete this marker from the motivelist
                # Select the marker
                index = object_list.index(marker)
                particle = self.motl_selected_instance.motivelist[index]
                # Delete particle from motivelist
                self.motl_selected_instance.motivelist.remove(particle)
                # And remove the marker
                marker.delete()
        # Delete the selected volumes from the motivelist
        volumes = [v for v in session.selection.models()]
        for volume in volumes:
            object_list = []         # Object list needs to be updated everytime a volume gets remove so the indices are still correct
            object_list = [particle[20] for particle in self.motl_selected_instance.motivelist]
            if volume in object_list:    # Delete this volume from the motivelist
                # Select the volume
                index = object_list.index(volume)
                particle = self.motl_selected_instance.motivelist[index]
                # Delete particle from motivelist
                self.motl_selected_instance.motivelist.remove(particle)
                # And close the volume
                volume.delete()

        # Update the sliders
        self.options_window.build_motl_sliders(session, self.motl_selected_instance)
        # Update the tomo list with the updated selected tomo instance
        self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def reset_selected_pressed(self, session):
        object_list = [particle[20] for particle in self.motl_selected_instance.motivelist]
        id_list = [particle[21] for particle in self.motl_selected_instance.motivelist]

        # Reset the markers
        markers = selected_markers(session)
        for marker in markers:
            # Get index from marker
            index = object_list.index(marker)
            # Get coordinates and angles
            x_coord = self.motl_selected_instance.motivelist[index][7]
            y_coord = self.motl_selected_instance.motivelist[index][8]
            z_coord = self.motl_selected_instance.motivelist[index][9]
            # Reset the marker position
            marker.coord = [x_coord, y_coord, z_coord]

        # Reset the volumes
        volumes = [v for v in session.models.list() if isinstance(v, Volume)]
        for volume in volumes:
            try:
                # Get the index from the volume
                index = object_list.index(volume)

                position_matrix = volume.position.matrix
                # Determine the angles
                psi, theta, phi = getEulerAngles(position_matrix)
                # Get coordinates and angles
                x_coord = self.motl_selected_instance.motivelist[index][7]
                y_coord = self.motl_selected_instance.motivelist[index][8]
                z_coord = self.motl_selected_instance.motivelist[index][9]
                # phi = self.motl_selected_instance.motivelist[index][16]
                # psi = self.motl_selected_instance.motivelist[index][17]
                # theta = self.motl_selected_instance.motivelist[index][18]
                # Get the corresponding rotation-translation matrix
                matrix = detRotMat(phi, psi, theta)
                matrix[0].append(x_coord)
                matrix[1].append(y_coord)
                matrix[2].append(z_coord)

                # Prepare the command
                command = "view matrix models #{}".format(id_list[index])
                for i in range(3):
                    for j in range(4):
                        command += ",{}".format(matrix[i][j])
                run(session, command)
            except:
                print("Skipped {} because not part of motivelist.".format(volume))

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def reset_all_pressed(self, session):
        obj_list = [particle[20] for particle in self.motl_selected_instance.motivelist]

        for i in range(len(obj_list)):
            object = obj_list[i]
            if isinstance(object, Volume):

                position_matrix = object.position.matrix
                # Determine the angles
                psi, theta, phi = getEulerAngles(position_matrix)
                # Get coordinates
                x_coord = self.motl_selected_instance.motivelist[i][7]
                y_coord = self.motl_selected_instance.motivelist[i][8]
                z_coord = self.motl_selected_instance.motivelist[i][9]
                # phi = self.motl_selected_instance.motivelist[i][16]
                # psi = self.motl_selected_instance.motivelist[i][17]
                # theta = self.motl_selected_instance.motivelist[i][18]
                # Get the corresponding rotation-translation matrix
                matrix = detRotMat(phi, psi, theta)
                matrix[0].append(x_coord)
                matrix[1].append(y_coord)
                matrix[2].append(z_coord)

                # Prepare the command
                id  = self.motl_selected_instance.motivelist[i][21]
                command = "view matrix models #{}".format(id)
                for i in range(3):
                    for j in range(4):
                        command += ",{}".format(matrix[i][j])
                run(session, command)
            else:
                # Get coordinates and angles
                x_coord = self.motl_selected_instance.motivelist[i][7]
                y_coord = self.motl_selected_instance.motivelist[i][8]
                z_coord = self.motl_selected_instance.motivelist[i][9]
                # Reset the marker position
                object.coord = [x_coord, y_coord, z_coord]

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def browse_edited(self, session):
        # Get the filepath from the LineEdit as a string
        filepath = self.options_window.browse_edit.text()
        filename = os.path.basename(filepath)
        # Set name and path in motl instance
        self.motl_selected_instance.obj_name = filename
        self.motl_selected_instance.obj_filepath = filepath
        # Execute the load object function
        self.load_obj_to_motl(session)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def browse_pushed(self, session):
        # Initialize filepath and filename
        filepath = None
        filename = None
        # Open a file dialog to select the filepath of the wanted object
        # Activate the selector
        self.select = self.file_dialog_open.exec()
        # Get the clicked directory
        if self.select:
            filepath = self.file_dialog_open.selectedFiles()[0]
            filename = os.path.basename(filepath)
        # Write the filepath in the LineEdit
        self.options_window.browse_edit.setText(filepath)
        # Set name and path in motl instance
        self.motl_selected_instance.obj_name = filename
        self.motl_selected_instance.obj_filepath = filepath
        # Execute the load object function
        self.load_obj_to_motl(session)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def load_obj_to_motl(self, session):
        run(session, "select clear")
        # Make a id list of the markers and an index list for where to place the objects
        id_list = []
        index_list = []
        for i in range(len(self.motl_selected_instance.motivelist)):
            id = self.motl_selected_instance.motivelist[i][21]
            object = self.motl_selected_instance.motivelist[i][20]
            if object.hide == False:
                if not isinstance(object, Volume):
                    id_list.append(id[0])
                    index_list.append(i)
                    object.hide = True



        # Just a quick routine to get the surface level
        # It's a bad workaround, but it works
        run(session, "open {}".format(self.motl_selected_instance.obj_filepath))
        volumes = [v for v in session.models.list() if isinstance(v, Volume)]
        surface_level = volumes[-1].surfaces[0].level
        id = volumes[-1].id_string
        run(session, "close #{}".format(id))

        # Initialize variables
        current_volume = None
        vol_data = []

        if ".em" in self.motl_selected_instance.obj_filepath:
            # Get the shape of the data
            vol_data = emread(self.motl_selected_instance.obj_filepath)
            dimensions = np.asarray(vol_data.shape)
            voxel_size = [1, 1, 1]  # Which is default by EM file

            # Us the dimensions and the voxel size to determine the origin
            origin = [-ma.floor(dimensions[0]*voxel_size[0]/2)+1,-ma.floor(dimensions[1]*voxel_size[1]/2)+1,-ma.floor(dimensions[2]*voxel_size[2]/2)+1]

            # Change data to a ChimeraX GridData
            data_grid = ArrayGridData(vol_data, origin=origin, step=voxel_size, name=self.motl_selected_instance.obj_name)

        elif ".mrc" in self.motl_selected_instance.obj_filepath:
            # Get the shape and the voxel size of the data and the data itself
            with mrcfile.open(self.motl_selected_instance.obj_filepath) as mrc:
                dimensions = np.asarray([mrc.header.nx, mrc.header.ny, mrc.header.nz])
                voxel_size = mrc.voxel_size.copy()
                vol_data = mrc.data
            # with the dimensions determine the origin, which is the center of the object
            origin = [-ma.floor(dimensions[0]*voxel_size.x/2)+1,-ma.floor(dimensions[1]*voxel_size.y/2)+1,-ma.floor(dimensions[2]*voxel_size.z/2)+1]
            step = np.asarray([voxel_size.x, voxel_size.y, voxel_size.z])

            # Change data to a ChimeraX GridData
            # mrc_grid = ArrayGridData(mrc_data, origin=origin, step=step, rotation=rot_mat, name=mrc_filename)
            data_grid = ArrayGridData(vol_data, origin=origin, step=step, name=self.motl_selected_instance.obj_name)

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
            volume_from_grid_data(data_grid, session, 'surface', (id_list[i],self.motl_selected_instance.list_index+1))

            # Add new volume to the object list in the motl instance
            current_volume = [v for v in session.models.list() if isinstance(v, Volume)][-1]
            # Add surface to the volume with default selected colors
            current_volume.add_surface(surface_level, rgba=(0, 1, 1, 1), display=True)
            # Add volume and ID to motivelist
            self.motl_selected_instance.motivelist[i][20] = current_volume

            self.motl_selected_instance.motivelist[i][21] = current_volume.id_string
            print(current_volume.id_string)

            # Use ChimeraX's view matrix method to rotate and translate
            # For this we need the rotation matrix appended by the translation vector
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
            run(session, "volume #{} style surface capFaces false".format(current_volume.id_string))

        # Set minimum, maximum and current surface level in motl instance
        self.motl_selected_instance.set_surface_level(vol_data.min(), vol_data.max(), surface_level)
        # Also set the surface position (slider) here
        self.motl_selected_instance.surface_position = surface_level

        # Update the motl list with the updated selected motl instance
        self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance

        # And finally rebuild the sliders
        self.options_window.row1_execute(session, int(self.options_window.group_select_row1_edit.text()), self.motl_selected_instance)
        self.options_window.row2_execute(session, int(self.options_window.group_select_row2_edit.text()), self.motl_selected_instance)
        self.options_window.build_motl_sliders(session, self.motl_selected_instance)


        # # At first delete the markers
        # for id in set(id_list):
        #     run(session, "delete #{}".format(id))


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
