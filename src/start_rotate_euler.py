''' Script to rotate models at actual center by Euler angles '''

# Currently the close button is just simply commented out
# It has no featuers other than printing something to the log
# Also, the window can be closed with ChimeraX's default close button
# So, the close buttn is redundant

from functools import partial
from chimerax.core.commands import run, Command
from chimerax.core.tools import ToolInstance
import os
import math as ma
# from cp import cp_motive
# from convert import convert
import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget
)

# Get current working directory
cwd = os.getcwd()

class Rotate_Euler(ToolInstance):

    # Inheriting from ToolInstance makes us known to the ChimeraX tool manager,
    # so we can be notified and take appropiate action when sessions are closed,
    # save, or restored, and we will be listed among running tools and so on.

    # If cleaning up is needed on finish, override the 'delete' method
    # but be sure to call 'delete' from the superclass at the end

    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = True         # We do save/restore in sessions
    help = "help:user/tools/tutorial.html"
                                # Let ChimeraX know about our help page

    def __init__(self, session, tool_name):
        # 'session'     - chimerax.core.session.Session instance
        # 'tool_name'   - string

        # Initialize base class
        super().__init__(session, tool_name)

        # Set name displayed on title bar
        self.display_name = "Rotate Euler"

        # Set the tool window
        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self)

        # Context menu
        self.tool_window.fill_context_menu = self.fill_context_menu

        # Create a new window
        self._build_ui(session)

    def _build_ui(self, session):

        # Initialize all widgets
        self.line_edit_phi = QLineEdit("0")            # Phi entry
        self.line_edit_psi = QLineEdit("0")            # Psi entry
        self.line_edit_theta = QLineEdit("0")          # Theta entry
        self.line_edit_objID = QLineEdit()          # Object ID entry
        self.check_box = QCheckBox()                   # Check box if true or false
        self.rotate_button = QPushButton("Rotate")     # Executes Rotation
        self.close_button = QPushButton("Close")       # Closes window
        self.reset_button = QPushButton("Reset")       # Resets rotations

        # Initiliaze some local variables
        self.phi = 0        # Default angle phi
        self.psi = 0        # Default angle psi
        self.theta = 0      # Default angle theta
        self.objID = -10    # default object ID

        # Also introduce global angles
        self.old_phi = 0
        self.old_psi = 0
        self.old_theta = 0

        # Define a local coordinate system with three unit base-vectors
        # Use as axes to rotate around
        self.base_1 = [1, 0, 0]
        self.base_2 = [0, 1, 0]
        self.base_3 = [0, 0, 1]

        # Connect all widgets to their corresponding function
        self.line_edit_phi.editingFinished.connect(self.set_phi)
        self.line_edit_psi.editingFinished.connect(self.set_psi)
        self.line_edit_theta.editingFinished.connect(self.set_theta)
        self.line_edit_objID.editingFinished.connect(self.set_objID)
        # self.check_box.connect(self.rotate_box_pressed)
        self.rotate_button.clicked.connect(partial(self.rotate_button_pressed, session))
        self.reset_button.clicked.connect(partial(self.reset_button_pressed, session))
        self.close_button.clicked.connect(self.close_button_pressed)

        # Build the top row consisting of three text fields
        layout_row_1 = QHBoxLayout()
        layout_row_1.addWidget(QLabel("Phi:"))
        layout_row_1.addWidget(self.line_edit_phi)
        layout_row_1.addWidget(QLabel("Psi:"))
        layout_row_1.addWidget(self.line_edit_psi)
        layout_row_1.addWidget(QLabel("Theta:"))
        layout_row_1.addWidget(self.line_edit_theta)

        layout_row_2 = QHBoxLayout()
        layout_row_2.addWidget(QLabel("Modelnumber:"))
        layout_row_2.addWidget(self.line_edit_objID)
        layout_row_2.addWidget(self.check_box)
        layout_row_2.addWidget(QLabel("Rotate all with same name"))

        layout_row_3 = QHBoxLayout()
        layout_row_3.addWidget(self.rotate_button)
        layout_row_3.addWidget(self.reset_button)
        # layout_row_3.addWidget(self.close_button)

        # Combine all row layouts
        layout = QVBoxLayout()
        layout.addLayout(layout_row_1)
        layout.addLayout(layout_row_2)
        layout.addLayout(layout_row_3)

        # Set the layout
        self.tool_window.ui_area.setLayout(layout)

        # Show the window on the user-preferred side of the
        # ChimeraX main window
        self.tool_window.manage('side')

# ==============================================================================
# Define the functions that the widgets do when they send a signal =============
# ==============================================================================

    def set_phi(self):
        try:
            self.phi = float(self.line_edit_phi.text())
        except:
            print("Please insert a float number as the angle!")


    def set_psi(self):
        try:
            self.psi = float(self.line_edit_psi.text())
        except:
            print("Please insert a float number as the angle!")


    def set_theta(self):
        try:
            self.theta = float(self.line_edit_theta.text())
        except:
            print("Please insert a float number as the angle!")


    def set_objID(self):
        try:
            self.objID = int(self.line_edit_objID.text())
        except:
            print("Please insert a valid integer as the object ID!")


    def rotate_button_pressed(self, session):
        self.execute_rot(session, True)


    # The reset button resets every entry and rewinds the rotation for current
    # Object ID
    def reset_button_pressed(self, session):

        # Reset variables
        self.phi = 0
        self.psi = 0
        self.theta = 0
        self.line_edit_phi.setText("0")
        self.line_edit_psi.setText("0")
        self.line_edit_theta.setText("0")
        self.line_edit_objID = QLineEdit()  
        if self.check_box.isChecked():
            self.check_box.setChecked(False)

        # Reset rotation (do backwards rotation around global angles)
        self.execute_rot(session, False)

        # Reset global angles
        self.old_phi = 0
        self.old_psi = 0
        self.old_theta = 0

        # Reset coordinate system
        self.base_1 = [1, 0, 0]
        self.base_2 = [0, 1, 0]
        self.base_3 = [0, 0, 1]

    def close_button_pressed(self):
        print("Well... I could close the window but I really do not want to.")


    # Function that fills the context menu
    def fill_context_menu(self, menu, x, y):
        # Add any tool-specific items to the given context menu (a QMenu instance).
        # The menu will then be automatically filled out with generic tool-related actions
        # (e.g. Hide Tool, Help, Dockable Tool, etc.)
        #
        # The x,y args are the x() and y() values of QContextMenuEvent, in the rare case
        # where the items put in the menu depends on where in the tool interface the menu
        # was raised.
        clear_action = QAction("Clear", menu)
        clear_action.triggered.connect(lambda *args: self.line_edit_phi.clear())
        clear_action.triggered.connect(lambda *args: self.line_edit_psi.clear())
        clear_action.triggered.connect(lambda *args: self.line_edit_theta.clear())
        clear_action.triggered.connect(lambda *args: self.line_edit_objID.clear())
        menu.addAction(clear_action)


    def take_snapshot(self, session, flags):
        return {
            'version': 1,
            'current text': self.line_edit_phi.text()
        }


    @classmethod
    def restore_snapshot(class_obj, session, data):
        # Instead of using a fixed string when calling the constructor below, we could
        # have saved the tool name during take_snapshot() (from self.tool_name, inherited
        # from ToolInstance) and used that saved tool name.  There are pros and cons to
        # both approaches.
        inst = class_obj(session, "Rotate Euler")
        inst.line_edit_phi.setText(data['current text'])
        return inst

# ==============================================================================
# Define all the functions for the Euler rotation ==============================
# ==============================================================================

    # Use the same functions as used in Chimera
    # ChimeraX related changes will be adapted
    # Returns the rotation matrix for given angles
    def euler_rotation(self, phi, psi, theta):
        # Initialize the matrix
        rot_mat = [[0 for i in range(3)] for j in range(3)]

        # Transform angles to radiants
        phi = phi*np.pi/180
        psi = psi*np.pi/180
        theta = theta*np.pi/180

        # Define every entry
        rot_mat[0][0] = np.cos(psi)*np.cos(phi) - np.cos(theta)*np.sin(psi)*np.sin(phi)
        rot_mat[1][0] = np.sin(psi)*np.cos(phi) + np.cos(theta)*np.cos(psi)*np.sin(phi)
        rot_mat[2][0] = np.sin(theta)*np.sin(phi)
        rot_mat[0][1] = -np.cos(psi)*np.sin(phi) - np.cos(theta)*np.sin(psi)*np.cos(phi)
        rot_mat[1][1] = -np.sin(psi)*np.sin(phi) + np.cos(theta)*np.cos(psi)*np.cos(phi)
        rot_mat[2][1] = np.sin(theta)*np.cos(phi)
        rot_mat[0][2] = np.sin(theta)*np.sin(psi)
        rot_mat[1][2] = -np.sin(theta)*np.cos(psi)
        rot_mat[2][2] = np.cos(theta)

        return rot_mat


    def inverse_euler_rotation(self, phi, psi, theta):
        # Initialize the matrix
        rot_mat = [[0 for i in range(3)] for j in range(3)]

        # Transform angles to radiants
        phi = phi*np.pi/180
        psi = psi*np.pi/180
        theta = theta*np.pi/180

        # Define every entry
        rot_mat[0][0] = np.cos(phi)*np.cos(psi) - np.sin(phi)*np.cos(theta)*np.sin(psi)
        rot_mat[1][0] = -np.sin(phi)*np.cos(psi) - np.cos(phi)*np.cos(theta)*np.sin(psi)
        rot_mat[2][0] = np.sin(theta)*np.sin(psi)
        rot_mat[0][1] = np.cos(phi)*np.sin(psi) + np.sin(phi)*np.cos(theta)*np.cos(psi)
        rot_mat[1][1] = -np.sin(phi)*np.sin(psi) + np.cos(phi)*np.cos(theta)*np.cos(psi)
        rot_mat[2][1] = -np.sin(theta)*np.cos(psi)
        rot_mat[0][2] = np.sin(phi)*np.sin(theta)
        rot_mat[1][2] = np.cos(phi)*np.sin(theta)
        rot_mat[2][2] = np.cos(theta)

        return rot_mat


    def mul_mat_mat(self, mat_1, mat_2):
        out = [[0 for i in range(3)] for j in range(3)]

        out[0][0] = mat_1[0][0]*mat_2[0][0] + mat_1[0][1]*mat_2[1][0] + mat_1[0][2]*mat_2[2][0]
        out[0][1] = mat_1[0][0]*mat_2[0][1] + mat_1[0][1]*mat_2[1][1] + mat_1[0][2]*mat_2[2][1]
        out[0][2] = mat_1[0][0]*mat_2[0][2] + mat_1[0][1]*mat_2[1][2] + mat_1[0][2]*mat_2[2][2]
        out[1][0] = mat_1[1][0]*mat_2[0][0] + mat_1[1][1]*mat_2[1][0] + mat_1[1][2]*mat_2[2][0]
        out[1][1] = mat_1[1][0]*mat_2[0][1] + mat_1[1][1]*mat_2[1][1] + mat_1[1][2]*mat_2[2][1]
        out[1][2] = mat_1[1][0]*mat_2[0][2] + mat_1[1][1]*mat_2[1][2] + mat_1[1][2]*mat_2[2][2]
        out[2][0] = mat_1[2][0]*mat_2[0][0] + mat_1[2][1]*mat_2[1][0] + mat_1[2][2]*mat_2[2][0]
        out[2][1] = mat_1[2][0]*mat_2[0][1] + mat_1[2][1]*mat_2[1][1] + mat_1[2][2]*mat_2[2][1]
        out[2][2] = mat_1[2][0]*mat_2[0][2] + mat_1[2][1]*mat_2[1][2] + mat_1[2][2]*mat_2[2][2]

        return out


    def mul_vec_mat(self, base_1, rot_mat):
        out = [0, 0, 0]
        base1 = [0, 0, 0]
        rot_matrix = [[0 for i in range(3)] for j in range(3)]

        base1 = base_1
        rot_matrix = rot_mat

        out[0] = rot_matrix[0][0]*base1[0] + rot_matrix[0][1]*base1[1] + rot_matrix[0][2]*base1[2]
        out[1] = rot_matrix[1][0]*base1[0] + rot_matrix[1][1]*base1[1] + rot_matrix[1][2]*base1[2]
        out[2] = rot_matrix[2][0]*base1[0] + rot_matrix[2][1]*base1[1] + rot_matrix[2][2]*base1[2]

        return out


    def get_euler_angles(self, mat):
        theta = np.arccos(mat[2][2])*180.0/np.pi

        if mat[2][2] > 0.999:
            sign = 1
            if mat[1][0] > 0:
                sign = 1.0
            else:
                sign = -1.0
            phi = sign*np.arccos(mat[0][0])*180.0/np.pi
            psi = 0.0
        else:
            phi = ma.atan2(mat[2][0], mat[2][1]) * 180.0/np.pi
            psi = ma.atan2(mat[0][2], -mat[1][2]) * 180.0/np.pi

        return phi, psi, theta


    def update_coordinate_system(self, base_1, base_2, base_3, phi, psi, theta):
        # Calculate rotation matrix
        rotation_matrix = self.euler_rotation(phi, psi, theta)

        # Rotate coordinate system
        base_1 = self.mul_vec_mat(base_1,rotation_matrix)
        base_2 = self.mul_vec_mat(base_2,rotation_matrix)
        base_3 = self.mul_vec_mat(base_3,rotation_matrix)

        # return coordinate system
        return base_1, base_2, base_3

    # Get list numbers of models with the same name
    # def same_name(listnum):


    # And finally execute the rotation
    def execute_rot(self, session, forward):
        # Check if user inserted an object ID
        if self.objID == -10:
            return print("No model number given.")

        # At first we go back to zero position
        # For this we need to at first rotate the coordinate system
        # Keep the self.bases at default
        base_1, base_2, base_3 = self.update_coordinate_system(self.base_1, self.base_2, self.base_3, self.old_phi, 0, self.old_theta)
        # Now execute the inverse rotation
        # At first around the z-axis, always update angles and base
        run(session, "turn {x:.5f},{y:.5f},{z:.5f} {ang:.5f} model #{id:}".
            format(x = base_3[0], y = base_3[1], z = base_3[2], ang = -self.old_psi, id = self.objID))
        base_1, base_2, base_3 = self.update_coordinate_system(self.base_1, self.base_2, self.base_3, self.old_phi, 0, 0)
        # Now around the x-axis, always update angles and base
        run(session, "turn {x:.5f},{y:.5f},{z:.5f} {ang:.5f} model #{id:}".
            format(x = base_1[0], y = base_1[1], z = base_1[2], ang = -self.old_theta, id = self.objID))
        base_1, base_2, base_3 = self.update_coordinate_system(self.base_1, self.base_2, self.base_3, 0, 0, 0)
        # And finally around z-axis again
        run(session, "turn {x:.5f},{y:.5f},{z:.5f} {ang:.5f} model #{id:}".
            format(x = base_3[0], y = base_3[1], z = base_3[2], ang = -self.old_phi, id = self.objID))

        print(base_1)
        print(base_2)
        print(base_3)

        base_1 = [1, 0, 0]
        base_2 = [0, 1, 0]
        base_3 = [0, 0, 1]

        # Execute the rotations (forward)
        if forward:
            # Now execute the actual rotation
            # At first around z-axis
            run(session, "turn {x:.5f},{y:.5f},{z:.5f} {ang:.5f} model #{id:}".
                format(x = base_3[0], y = base_3[1], z = base_3[2], ang = self.phi, id = self.objID))
            base_1, base_2, base_3 = self.update_coordinate_system(self.base_1, self.base_2, self.base_3, self.phi, 0 ,0 )
            # Then x-axis
            run(session, "turn {x:.5f},{y:.5f},{z:.5f} {ang:.5f} model #{id:}".
                format(x = base_1[0], y = base_1[1], z = base_1[2], ang = self.theta, id = self.objID))
            base_1, base_2, base_3 = self.update_coordinate_system(self.base_1, self.base_2, self.base_3, self.phi, 0, self.theta)
            # And finally the z-axis again
            run(session, "turn {x:.5f},{y:.5f},{z:.5f} {ang:.5f} model #{id:}".
                format(x = base_3[0], y = base_3[1], z = base_3[2], ang = self.psi, id = self.objID))
            # base_1, base_2, base_3 = self.update_coordinate_system(self.base_1, self.base_2, self.base_3, self.phi, self.psi, self.theta)

            self.old_psi = self.psi
            self.old_theta = self.theta
            self.old_phi = self.phi
        else:
            self.old_phi = 0
            self.old_psi = 0
            self.old_theta = 0
