# vim: set expandtab shiftwidth=4 softtabstop=4:

import os as os
import numpy as np


from functools import partial
from chimerax.core.commands import run
from chimerax.core.tools import ToolInstance
from chimerax.map import Volume, open_map
from chimerax.core.models import Model
from chimerax.markers import MarkerSet, selected_markers
from chimerax.ui import MainToolWindow


#from src.io.Artiatomi.emwrite import emwrite
from .emread import emread
from .euler_rotation import detRotMat, getEulerAngles
from .options_window import OptionsWindow

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence

from .ArtiaX import ArtiaX
from .io import get_partlist_formats

# from PyQt5.QtGui import QAbstractItemView
from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QMenu,
    QMenuBar,
    QPushButton,
    QShortcut,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QButtonGroup,
    QAbstractItemView
)

# Define the tomo class which is a ChimeraX tool window
class ArtiaXUI(ToolInstance):

    # Inheriting from ToolInstance makes us known to the ChimeraX tool manager,
    # so we can be notified and take appropiate action when sessions are closed,
    # save, or restored, and we will be listed among running tools and so on.

    # If cleaning up is needed on finish, override the 'delete' method
    # but be sure to call 'delete' from the superclass at the end

    # Does this instance persist when session closes
    SESSION_ENDURING = False
    # We do save/restore in sessions
    SESSION_SAVE = True
    # Let ChimeraX know about our help page
    help = "help:user/tools/tutorial.html"

    #pixel_size_old = 1.0

# ==============================================================================
# Instance Initialization ======================================================
# ==============================================================================


    def __init__(self, session, tool_name):
        # 'session'     - chimerax.core.session.Session instance
        # 'tool_name'   - string

        # Initialize base class
        super().__init__(session, tool_name)

        # Display Name
        self.display_name = "ArtiaX"

        # Set the font
        self.font = QFont("Arial", 7)

        # UI
        self.tool_window = MainToolWindow(self)
        self.tool_window.fill_context_menu = self.fill_context_menu
        self._build_ui()

        # Connect the shortcurts to functions in the options window
        #self.define_shortcuts(session)

        if not hasattr(session, 'ArtiaX'):
            session.ArtiaX = ArtiaX(self)

        self._build_options_window(tool_name)
        self._connect_ui()

# ==============================================================================
# Interface construction =======================================================
# ==============================================================================

    def _build_ui(self):

        # Volume open dialog
        caption = 'Choose a volume.'
        self.volume_open_dialog = QFileDialog(caption=caption)
        self.volume_open_dialog.setFileMode(QFileDialog.ExistingFiles)
        self.volume_open_dialog.setNameFilters(["Volume (*.em *.mrc *.mrcs *.rec *.map *.hdf)"])
        self.volume_open_dialog.setAcceptMode(QFileDialog.AcceptOpen)

        # Particle list open dialog
        fmts = get_partlist_formats(self.session)
        self.partlist_filters = {}
        for fmt in fmts:
            self.partlist_filters[self.session.data_formats.qt_file_filter(fmt)] = fmt.name

        caption = 'Choose a particle list.'
        self.particle_open_dialog = QFileDialog(caption=caption)
        self.particle_open_dialog.setFileMode(QFileDialog.ExistingFiles)
        self.particle_open_dialog.setNameFilters(list(self.partlist_filters.keys()))
        self.particle_open_dialog.setAcceptMode(QFileDialog.AcceptOpen)

        caption = 'Choose a name to save the particle list.'
        self.particle_save_dialog = QFileDialog(caption=caption)
        self.particle_save_dialog.setFileMode(QFileDialog.AnyFile)
        self.particle_save_dialog.setNameFilters(list(self.partlist_filters.keys()))
        self.particle_save_dialog.setAcceptMode(QFileDialog.AcceptSave)

        # Build the menu bar
        self._build_menubar()

        # Prepare some widgets that are used later
        self._build_table_widgets()

        # Prepare main window widgets
        self._build_main_ui()

        # Build the actual GUI
        layout = QVBoxLayout()
        layout.addLayout(self.menu_bar_widget)
        #layout.addWidget(self.menu_bar_widget)
        layout.addWidget(self.group_tomo)
        layout.addWidget(self.group_partlist)

        # Set the layout
        self.tool_window.ui_area.setLayout(layout)

        # Show the window on the user-preferred side of the
        # ChimeraX main window
        self.tool_window.manage("left")


# ==============================================================================
# Set shortcuts =============================================
# ==============================================================================

    def _define_shortcuts(self, session):
        # Define the shortcuts
        self.jump_1_forwards = QShortcut(QKeySequence(Qt.Key_F4), self.options_window.group_slices_next_1)
        self.jump_10_forwards = QShortcut(QKeySequence(Qt.Key_F8), self.options_window.group_slices_next_10)
        self.jump_1_backwards = QShortcut(QKeySequence(Qt.Key_F3), self.options_window.group_slices_previous_1)
        self.jump_10_backwards = QShortcut(QKeySequence(Qt.Key_F7), self.options_window.group_slices_previous_10)
        # Connect actions to functions
        # self.jump_1_forwards.activated.connect(partial(self.skip_planes, session, 1))
        # self.jump_10_forwards.activated.connect(partial(self.skip_planes, session, 10))
        # self.jump_1_backwards.activated.connect(partial(self.skip_planes, session, -1))
        # self.jump_10_backwards.activated.connect(partial(self.skip_planes, session, -10))


# ==============================================================================
# Prepare GUI functions ========================================================
# ==============================================================================


    def _build_menubar(self):
        # Use a QHBoxLayout for the menu bar
        self.menu_bar_widget = QHBoxLayout()

        # A dropdown menu for the menu bar
        #menu_bar = QToolButton()
        #menu_bar.setPopupMode(QToolButton.MenuButtonPopup)

        # Define all the buttons and connect them to corresponding function
        self.menu_open_tomogram = QAction("Open Tomogram")
        self.menu_open_parts = QAction("Load Particle List")
        self.menu_save_parts = QAction("Save Particle List")

        # Prepare the file menu
        self.menu = QMenu("&File")
        self.menu.addAction(self.menu_open_tomogram)
        self.menu.addSeparator()
        self.menu.addAction(self.menu_open_parts)
        self.menu.addAction(self.menu_save_parts)

        # Add to the actual menu
        self.menu_bar = QMenuBar()
        self.menu_bar.addMenu(self.menu)
        # Add the menu bar to the widget
        self.menu_bar_widget.addWidget(self.menu_bar)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _build_table_widgets(self):
        """Build the two table widgets."""

        # A display table for the tomograms
        self.table_tomo = QTableWidget()
        self.table_tomo.setFont(self.font)
        self.table_tomo.setRowCount(0)
        self.table_tomo.setColumnCount(3)
        self.table_tomo.setSelectionBehavior(QAbstractItemView.SelectRows)
        header_1 = self.table_tomo.horizontalHeader()
        header_1.setSectionResizeMode(0, QHeaderView.Stretch)
        header_1.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_1.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_tomo.setHorizontalHeaderLabels(["Name", "Show", "Options"])

        # A display table for the motivelists
        self.table_part = QTableWidget()
        self.table_part.setFont(self.font)
        self.table_part.setRowCount(0)
        self.table_part.setColumnCount(3)
        self.table_part.setSelectionBehavior(QAbstractItemView.SelectRows)
        header_2 = self.table_part.horizontalHeader()
        header_2.setSectionResizeMode(0, QHeaderView.Stretch)
        header_2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_part.setHorizontalHeaderLabels(["Name", "Show", "Options"])

        # Groups for tomo check boxes
        self.tomo_show_group = QButtonGroup()
        self.tomo_show_group.setExclusive(False)
        self.tomo_options_group = QButtonGroup()
        self.tomo_options_group.setExclusive(True)

        # Groups for particle list check boxes
        self.part_show_group = QButtonGroup()
        self.part_show_group.setExclusive(False)
        self.part_options_group = QButtonGroup()
        self.part_options_group.setExclusive(True)

        # Group for options check boxes
        self.tomo_options_widgets = []
        self.motl_options_widgets = []


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def _build_main_ui(self):
        '''Add the table widgets and some buttons the the main layout.'''
        
        ##### Group Box "Tomograms" #####
        self.group_tomo = QGroupBox("Tomograms")
        self.group_tomo.setFont(self.font)
        # Group Box Layout
        group_tomo_layout = QVBoxLayout()
        
        # Contents
        self.group_tomo_close_button = QPushButton("Close selected tomogram")
        
        group_tomo_layout.addWidget(self.table_tomo)
        group_tomo_layout.addWidget(self.group_tomo_close_button)
        
        # Add layout to the group
        self.group_tomo.setLayout(group_tomo_layout)
        ##### Group Box "Tomograms" #####

        ##### Group Box "Particle Lists" #####
        self.group_partlist = QGroupBox("Particle Lists")
        self.group_partlist.setFont(self.font)
        # Group Box Layout
        group_partlist_layout = QVBoxLayout()
        
        # Contents
        group_partlist_button_layout = QHBoxLayout()
        self.group_partlist_create_button = QPushButton("Create new motivelist")
        self.group_partlist_close_button = QPushButton("Close selected motivelist")
        
        group_partlist_button_layout.addWidget(self.group_partlist_create_button)
        group_partlist_button_layout.addWidget(self.group_partlist_close_button)
        
        # Add button layout to group layout
        group_partlist_layout.addWidget(self.table_part)
        group_partlist_layout.addLayout(group_partlist_button_layout)
        # Add layout to the group
        self.group_partlist.setLayout(group_partlist_layout)
        ##### Group Box "Particle Lists" #####


    def _connect_ui(self):
        self._connect_tomo_ui()
        self._connect_part_ui()

    def _connect_tomo_ui(self):
        ui = self
        ow = self.ow
        artia = self.session.ArtiaX

        # Menu bar items
        ui.menu_open_tomogram.triggered.connect(partial(self._open_volume))

        # Tomo table
        ui.table_tomo.itemClicked.connect(partial(self._tomo_table_selected))
        ui.table_tomo.itemChanged.connect(partial(self._tomo_table_name_changed))
        ui.group_tomo_close_button.clicked.connect(partial(self._close_volume))


    def _connect_part_ui(self):
        ui = self
        ow = self.ow
        artia = self.session.ArtiaX

        # Menu bar items
        ui.menu_open_parts.triggered.connect(partial(self._open_partlist))
        ui.menu_save_parts.triggered.connect(partial(self._save_partlist))

        # Partlist table
        ui.table_part.itemClicked.connect(partial(self._partlist_table_selected))
        ui.table_part.itemChanged.connect(partial(self._partlist_table_name_changed))
        ui.group_partlist_create_button.clicked.connect(partial(self._create_partlist))
        ui.group_partlist_close_button.clicked.connect(partial(self._close_partlist))

    # ==============================================================================
# Menu Bar Functions ===========================================================
# ==============================================================================

    def _open_volume(self):
        artia = self.session.ArtiaX

        file = self._choose_volume()

        if file is not None and len(file):
            artia.open_tomogram(file[0])

    def _choose_volume(self):
        if self.volume_open_dialog.exec():
            return self.volume_open_dialog.selectedFiles()

    def _open_partlist(self):
        artia = self.session.ArtiaX

        file, format = self._choose_partlist()

        if file is not None and len(file):
            fmt_name = self.partlist_filters[format]
            artia.open_partlist(file[0], fmt_name)

    def _choose_partlist(self):
        if self.particle_open_dialog.exec():
            return self.particle_open_dialog.selectedFiles(), self.particle_open_dialog.selectedNameFilter()

    def _create_partlist(self):
        artia = self.session.ArtiaX
        artia.create_partlist()

    def _save_partlist(self):
        artia = self.session.ArtiaX

        file, format = self._choose_partlist_save()

        if file is not None and len(file):
            fmt_name = self.partlist_filters[format]
            artia.save_partlist(artia.selected_partlist, file[0], fmt_name)

    def _choose_partlist_save(self):
        if self.particle_save_dialog.exec():
            return self.particle_save_dialog.selectedFiles(), self.particle_save_dialog.selectedNameFilter()

    def _close_volume(self):
        artia = self.session.ArtiaX

        if artia.selected_tomogram is None or artia.tomograms.count == 0:
            return

        artia.close_tomogram(artia.selected_tomogram)

    def _close_partlist(self):
        artia = self.session.ArtiaX

        if artia.selected_partlist is None or artia.partlists.count == 0:
            return

        artia.close_partlist(artia.selected_partlist)

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

            row = self.table_part.rowCount()
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
            self.table_part.setItem(self.motl_selected_instance.table_row, 0, QTableWidgetItem(motl_filename))

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

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def motl_create_button_pressed(self, session):

        # Create a new motl instance with a default name
        number_rows = self.table_part.rowCount()
        name = "Motivelist {}".format(number_rows + 1)
        from .object_settings import MotlInstance
        motl_instance = MotlInstance(name, number_rows, len(self.motl_list))

        # Append motl instance in motl list
        self.motl_list.append(motl_instance)
        # Update motl table (table_part)
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
            self.table_part.removeRow(self.motl_selected_instance.table_row)
            # Reconnect all the QCheckBoxes with the right variables


            # Remove the motl from the motl_list
            self.motl_list.remove(self.motl_selected_instance)

            # It is also nice to have a message printed in the Log that
            # The tomogram got closed
            print("{} has been closed.".format(self.motl_selected_instance.name))

            # Also update the options window
            self.options_window.change_gui("default")
            self.options_window.group_pixel_size_pixlabel.setText("1.0")

            # And finally set the selected tomo instance to default
            self.motl_selected_instance = None


# ==============================================================================
# Table Functions ==============================================================
# ==============================================================================

    def _update_tomo_table(self):
        ui = self
        artia = self.session.ArtiaX

        ui.table_tomo.setRowCount(artia.tomograms.count)

        # Delete old Buttons
        for b in ui.tomo_show_group.buttons():
            ui.tomo_show_group.removeButton(b)
            b.deleteLater()

        for b in ui.tomo_options_group.buttons():
            ui.tomo_options_group.removeButton(b)
            b.deleteLater()

        # Add new Buttons and connections
        from PyQt5.QtWidgets import QCheckBox, QTableWidgetItem
        from PyQt5.QtCore import Qt

        for idx, t in enumerate(artia.tomograms.iter()):
            # Define Checkboxes for show and options
            name_box = QTableWidgetItem(t.name)
            show_box = QCheckBox()
            options_box = QCheckBox()

            # Set the check state
            if artia.tomograms.get(idx).display:
                show_box.setCheckState(Qt.Checked)
            else:
                show_box.setCheckState(Qt.Unchecked)

            if artia.tomograms.has_id(artia.options_tomogram) and artia.tomograms.get_id(idx) == artia.options_tomogram:
                options_box.setCheckState(Qt.Checked)
            else:
                options_box.setCheckState(Qt.Unchecked)

            # Connect the Items to a function
            show_box.stateChanged.connect(partial(ui._show_tomo, idx))
            options_box.stateChanged.connect(partial(ui._show_tomo_options, idx))

            ui.table_tomo.setItem(idx, 0, name_box)
            ui.table_tomo.setCellWidget(idx, 1, show_box)
            ui.table_tomo.setCellWidget(idx, 2, options_box)

            # Add buttons to groups
            ui.tomo_show_group.addButton(show_box)
            #ui.tomo_options_widgets.append(options_box)
            ui.tomo_options_group.addButton(options_box)

        ui.table_tomo.selectRow(0)
        if artia.tomograms.count > 0:
            artia.selected_tomogram = artia.tomograms.get_id(0)
        else:
            artia.selected_tomogram = None

        if not artia.tomograms.has_id(artia.options_tomogram):
            artia.options_tomogram = None


    def _update_partlist_table(self):
        ui = self
        artia = self.session.ArtiaX

        ui.table_part.setRowCount(artia.partlists.count)

        # Delete old Buttons
        for b in ui.part_show_group.buttons():
            ui.part_show_group.removeButton(b)
            b.deleteLater()

        for b in ui.part_options_group.buttons():
            ui.part_options_group.removeButton(b)
            b.deleteLater()

        # Add new Buttons and connections
        from PyQt5.QtWidgets import QCheckBox, QTableWidgetItem
        from PyQt5.QtCore import Qt

        for idx, p in enumerate(artia.partlists.iter()):
            # Define Checkboxes for show and options
            name_box = QTableWidgetItem(p.name)
            show_box = QCheckBox()
            options_box = QCheckBox()

            # Set the check state
            if artia.partlists.get(idx).display:
                show_box.setCheckState(Qt.Checked)
            else:
                show_box.setCheckState(Qt.Unchecked)

            if artia.partlists.has_id(artia.options_partlist) and artia.partlists.get_id(idx) == artia.options_partlist:
                options_box.setCheckState(Qt.Checked)
            else:
                options_box.setCheckState(Qt.Unchecked)

            # Connect the Items to a function
            show_box.stateChanged.connect(partial(ui._show_partlist, idx))
            options_box.stateChanged.connect(partial(ui._show_partlist_options, idx))

            ui.table_part.setItem(idx, 0, name_box)
            ui.table_part.setCellWidget(idx, 1, show_box)
            ui.table_part.setCellWidget(idx, 2, options_box)

            # Add buttons to groups
            ui.part_show_group.addButton(show_box)
            ui.part_options_group.addButton(options_box)

        ui.table_part.selectRow(0)
        if artia.partlists.count > 0:
            artia.selected_partlist = artia.partlists.get_id(0)
        else:
            artia.selected_partlist = None

        if not artia.partlists.has_id(artia.options_partlist):
            artia.options_partlist = None

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _tomo_table_selected(self, item):
        artia = self.session.ArtiaX

        if item is not None:
            artia.selected_tomogram = artia.tomograms.get_id(item.row())

    def _tomo_table_name_changed(self, item):
        artia = self.session.ArtiaX
        if (item is not None) and (item.column() == 0):
            name = item.text()
            row = item.row()
            #if not artia.tomograms.set_name(row, name):
            #    item.setText(artia.tomograms.get(row).name)
            artia.tomograms.set_name(row, name)

    def _show_tomo(self, idx, state):
        artia = self.session.ArtiaX
        artia.selected_tomogram = artia.tomograms.get_id(idx)

        if state == Qt.Checked:
            artia.show_tomogram(idx)
        elif state == Qt.Unchecked:
            artia.hide_tomogram(idx)

    def _show_tomo_options(self, idx, state):
        artia = self.session.ArtiaX
        artia.options_tomogram = artia.tomograms.get_id(idx)

        if state == Qt.Checked:
            self.ow._show_tab("tomogram")

    def _partlist_table_selected(self, item):
        artia = self.session.ArtiaX

        if item is not None:
            artia.selected_partlist = artia.partlists.get_id(item.row())

    def _partlist_table_name_changed(self, item):
        artia = self.session.ArtiaX
        if (item is not None) and (item.column() == 0):
            name = item.text()
            row = item.row()
            artia.partlists.set_name(row, name)

    def _show_partlist(self, idx, state):
        artia = self.session.ArtiaX
        artia.selected_partlist = artia.partlists.get_id(idx)

        if state == Qt.Checked:
            artia.show_partlist(idx)
        elif state == Qt.Unchecked:
            artia.hide_partlist(idx)

    def _show_partlist_options(self, idx, state):
        artia = self.session.ArtiaX
        artia.options_partlist = artia.partlists.get_id(idx)

        if state == Qt.Checked:
            self.ow._show_tab("partlist")

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
            item = self.table_part.selectedItems()
            column = self.table_part.currentColumn()
            row = self.table_part.currentRow()
            motl_instance = None
            # Depending on the row, find the corresponding motl instance
            for instance in self.motl_list:
                if instance.table_row == row:
                    motl_instance = instance
                    break

            if motl_instance != None:
                if column == 0:     # Change the name
                    motl_instance.name = self.table_part.item(row, column).text()
                # elif column == 1:   # Change the object name
                #     motl_instance.obj_name = self.table_part.item(row, column).text()


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

    def _build_options_window(self, tool_name):
        # Creates an instance of the new window's class
        self.ow = OptionsWindow(self.session, tool_name)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Tomo Functions +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



    def connect_tomo_functions(self):

        session = self.session
        #Physical Position
        self.options_window.group_pixelSize_button.clicked.connect(partial(self.ApplypixSize_execute, session))
        self.options_window.group_physPos_button.clicked.connect(partial(self.physPosition_execute, session))
        # Center
        #self.options_window.group_contrast_center_edit.returnPressed.connect(partial(self.center_edited, session))
        #self.options_window.group_contrast_center_slider.valueChanged.connect(partial(self.center_slider, session))
        #self.options_window.group_contrast_center_slider.sliderReleased.connect(partial(self.center_released))
        # Width
        #self.options_window.group_contrast_width_edit.returnPressed.connect(partial(self.width_edited, session))
        #self.options_window.group_contrast_width_slider.valueChanged.connect(partial(self.width_slider, session))
        #self.options_window.group_contrast_width_slider.sliderReleased.connect(partial(self.width_released))
        # Slice
        # self.options_window.group_slices_edit.returnPressed.connect(partial(self.slice_edited, session))
        # self.options_window.group_slices_slider.valueChanged.connect(partial(self.slice_slider, session))
        # self.options_window.group_slices_slider.sliderReleased.connect(partial(self.slice_released))
        # Slices buttons
        # self.options_window.group_slices_previous_10.clicked.connect(partial(self.skip_planes, session, -10))
        # self.options_window.group_slices_previous_1.clicked.connect(partial(self.skip_planes, session, -1))
        # self.options_window.group_slices_next_1.clicked.connect(partial(self.skip_planes, session, 1))
        # self.options_window.group_slices_next_10.clicked.connect(partial(self.skip_planes, session, 10))
        # Fourier transform
        self.options_window.group_fourier_transform_execute_button.clicked.connect(partial(self.fourier_transform, session))
        # Orthoplanes
        # self.options_window.group_orthoplanes_buttonxy.clicked.connect(partial(self.orthoplanes_buttonxy_execute, session))
        # self.options_window.group_orthoplanes_buttonxz.clicked.connect(partial(self.orthoplanes_buttonxz_execute, session))
        # self.options_window.group_orthoplanes_buttonyz.clicked.connect(partial(self.orthoplanes_buttonyz_execute, session))
        # self.options_window.group_orthoplanes_buttonxyz.clicked.connect(partial(self.orthoplanes_buttonxyz_execute, session))

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

    # def skip_planes(self, session, number):
    #     # Update the slice position in the tomo instance
    #     if self.tomo_selected_instance.slice_position + number > self.tomo_selected_instance.z_dim:
    #         self.tomo_selected_instance.slice_position = self.tomo_selected_instance.z_dim
    #     elif self.tomo_selected_instance.slice_position + number < 1:
    #         self.tomo_selected_instance.slice_position = 1
    #     else:
    #         self.tomo_selected_instance.slice_position = self.tomo_selected_instance.slice_position + number
    #     # Update the slider and edit value
    #     self.options_window.group_slices_edit.setText(str(self.tomo_selected_instance.slice_position))
    #     self.options_window.group_slices_slider.setValue(self.tomo_selected_instance.slice_position)
    #     # Update the tomo list with the updated selected tomo instance
    #     self.tomo_list[self.tomo_selected_instance.list_index] = self.tomo_selected_instance
    #     # Execute the slice function
    #     self.options_window.slice_execute(session, self.tomo_selected_instance.slice_position, self.tomo_selected_instance)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def orthoplanes_buttonxy_execute(self, session):
        id = self.tomo_selected_instance.id_string
        command = "volume #{} orthoplanes xy".format(id)
        run(session, command)
        run(session, "mousemode rightMode "+'"move planes"')

    def orthoplanes_buttonxz_execute(self, session):
        id = self.tomo_selected_instance.id_string
        command = "volume #{} orthoplanes xz".format(id)
        run(session, command)
        run(session, "mousemode rightMode "+'"move planes"')

    def orthoplanes_buttonyz_execute(self, session):
        id = self.tomo_selected_instance.id_string
        command = "volume #{} orthoplanes yz".format(id)
        run(session, command)
        run(session, "mousemode rightMode "+'"move planes"')

    def orthoplanes_buttonxyz_execute(self, session):
        id = self.tomo_selected_instance.id_string
        command = "volume #{} orthoplanes xyz".format(id)
        run(session, command)
        run(session, "mousemode rightMode "+'"move planes"')

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def fourier_transform(self, session):
        # Execute the fourier transform of the current volume
        id = self.tomo_selected_instance.id_string
        command = "volume fourier #{} phase true".format(id)
        run(session, command)


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Motl Functions +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def connect_motl_functions(self, session):
        # Select slider
        self.options_window.group_select_selection_clampview.clicked.connect(partial(self.selection_check, session))
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

    def selection_check(self, session):

        list_selected = []
        #Check what is selected on the image
        for i in session.models.list():
            if i.selected:
                list_selected.append(i.id_string)

        # Execute the ClampView function
        if len(list_selected) == len(self.motl_selected_instance.motivelist):

            self.options_window.ClampView_execute(session, 0)
            self.options_window.group_select_selection_edit.setText('all')

        else:
            print()
            if  len(list_selected) > 2:
                self.options_window.ClampView_execute(session, 0)
            elif len(list_selected) <= 2:
                self.options_window.ClampView_execute(session, len(list_selected))
                string = ''
                for i in list_selected:
                    string += str(i)+' '
                self.options_window.group_select_selection_edit.setText(string)

        # Update the tomo list with the updated selected tomo instance
        self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance

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
                self.options_window.group_select_lower_thresh_slider.setValue(int(lower_value1))
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
        print('Motivelist updated!')

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

            self.motl_selected_instance.row1_position = int(self.options_window.group_select_row1_slider.value())
            self.motl_selected_instance.row2_position = int(self.options_window.group_select_row2_slider.value())

            # Add the markers as Volumes
            self.motl_selected_instance.add_marker_as_volume(session, marker_instance)

            # Update the sliders
            self.options_window.row1_execute(session, self.motl_selected_instance.row1_position, self.motl_selected_instance)
            self.options_window.row2_execute(session, self.motl_selected_instance.row2_position, self.motl_selected_instance)

            # Update the other sliders
            ###self.options_window.threshold_execute(session, self.motl_selected_instance.lower_thresh1, self.motl_selected_instance.upper_thresh1, self.motl_selected_instance.lower_thresh2, self.motl_selected_instance.upper_thresh2, self.motl_selected_instance)
            ###self.options_window.build_other_motl_sliders(session, self.motl_selected_instance.row1_position, self.motl_selected_instance)
            ###self.options_window.build_other_motl_sliders2(session, self.motl_selected_instance.row2_position, self.motl_selected_instance)

            # Update the tomo list with the updated selected tomo instance
            self.motl_list[self.motl_selected_instance.list_index] = self.motl_selected_instance

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

        self.motl_selected_instance.row1_position = int(self.options_window.group_select_row1_slider.value())
        self.motl_selected_instance.row2_position = int(self.options_window.group_select_row2_slider.value())

        # Update the sliders
        self.options_window.row1_execute(session, self.motl_selected_instance.row1_position, self.motl_selected_instance)
        self.options_window.row2_execute(session, self.motl_selected_instance.row2_position, self.motl_selected_instance)

        # Update the other sliders 
        ###self.options_window.threshold_execute(session, self.motl_selected_instance.lower_thresh1, self.motl_selected_instance.upper_thresh1, self.motl_selected_instance.lower_thresh2, self.motl_selected_instance.upper_thresh2, self.motl_selected_instance)
        ###self.options_window.build_other_motl_sliders(session, self.motl_selected_instance.row1_position, self.motl_selected_instance)
        ###self.options_window.build_other_motl_sliders2(session, self.motl_selected_instance.row2_position, self.motl_selected_instance)
        
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

        # Open the object filepath (returns tuple of 
        # Volume Object chimerax.map.volume.Volume, base class Model)
        filepath = self.motl_selected_instance.obj_filepath
        only_surface = open_map(session, filepath)

        # Add this model to the session (this causes it to be displayed and 
        # the surface to be rendered)
        session.models.add(only_surface[0])                                                                     # Cone erscheint 

        # We can now create a new Model that will only contain the surface
        # Notice that we haven't added it to the session yet, so it's invisible in the model panel)
        standalone_surface = Model('Surface', session)                                                          # Hier wird vom geladenen Tomogram ein neues Surface erstellt mit einer neuen ID 

        # We now get the geometry of the VolumeSurface and transfer it to the new Model instance 
        # using the set_geometry method. We need the vertices, normals and triangles, as well as edge_mask and triangle_mask.
        vertices = session.models[0].surfaces[0]._vertices
        normals = session.models[0].surfaces[0]._normals
        triangles = session.models[0].surfaces[0]._triangles
        edge_mask = session.models[0].surfaces[0]._edge_mask
        triangle_mask = session.models[0].surfaces[0]._triangle_mask

        standalone_surface.set_geometry(vertices, normals, triangles, edge_mask, triangle_mask)

        # We now hide the original Volume model and the VolumeSurface model
        session.models[0].show(show=False)                                       

        # We now add the new surface to the session. 
        # The Surface is now visible on screen and in the model panel.
        session.models.add([standalone_surface])                                                                # Das Surface des Tomograms wird hinzugefügtund im model panel angezeigt


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
