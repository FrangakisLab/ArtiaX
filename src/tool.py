# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
from functools import partial

# ChimeraX
from chimerax.core.tools import ToolInstance
from chimerax.ui import MainToolWindow

# Qt
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QMenu,
    QMenuBar,
    QPushButton,
    QShortcut,
    QVBoxLayout,
)

# This package
from .ArtiaX import ArtiaX
from .options_window import OptionsWindow
from .io import get_partlist_formats

class ArtiaXUI(ToolInstance):

    # Does this instance persist when session closes
    SESSION_ENDURING = False
    # We do save/restore in sessions
    SESSION_SAVE = True
    # Let ChimeraX know about our help page
    help = "help:user/tools/tutorial.html"

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
        self.tool_window = MainToolWindow(self, close_destroys=False)


        # Connect the shortcurts to functions in the options window
        #self.define_shortcuts(session)

        # Base Model if it doesn't exist yet
        if not hasattr(session, 'ArtiaX'):
            session.ArtiaX = ArtiaX(self)

        self._build_ui()
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
        artia = self.session.ArtiaX

        from .widgets import ManagerTableWidget

        # A display table for the tomograms
        self.table_tomo = ManagerTableWidget(self.session,
                                             artia.tomograms,
                                             self._show_tomo,
                                             self._show_tomo_options)

        # A display table for the motivelists
        self.table_part = ManagerTableWidget(self.session,
                                             artia.partlists,
                                             self._show_partlist,
                                             self._show_partlist_options)

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
        self.group_partlist_create_button = QPushButton("Create new particle list")
        self.group_partlist_close_button = QPushButton("Close selected particle list")
        
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

# ==============================================================================
# Table Functions ==============================================================
# ==============================================================================

    def _update_tomo_table(self):
        artia = self.session.ArtiaX
        sel_id, opt_id = self.table_tomo.update_table(artia.options_tomogram)
        artia.selected_tomogram = sel_id
        artia.options_tomogram = opt_id

    def _update_partlist_table(self):
        artia = self.session.ArtiaX
        sel_id, opt_id = self.table_part.update_table(self.session.ArtiaX.options_partlist)
        artia.selected_partlist = sel_id
        artia.options_partlist = opt_id

    def _tomo_table_selected(self, item):
        artia = self.session.ArtiaX

        if item is not None:
            artia.selected_tomogram = artia.tomograms.get_id(item.row())

    def _tomo_table_name_changed(self, item):
        artia = self.session.ArtiaX
        if (item is not None) and (item.column() == 1):
            name = item.text()
            row = item.row()
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

        if state:
            self.ow._show_tab("tomogram")

    def _partlist_table_selected(self, item):
        artia = self.session.ArtiaX

        if item is not None:
            artia.selected_partlist = artia.partlists.get_id(item.row())

    def _partlist_table_name_changed(self, item):
        artia = self.session.ArtiaX
        if (item is not None) and (item.column() == 1):
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

        if state:
            self.ow._show_tab("partlist")

# ==============================================================================
# Shortcut Functions ===========================================================
# ==============================================================================

# The following 4 jump functions only work if a tomogram is selected
    def jump_1_forwards_pressed(self, session):
        print("Yes, the shortcut worked.")


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