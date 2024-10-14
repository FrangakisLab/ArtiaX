# vim: set expandtab shiftwidth=4 softtabstop=4:

#Qt
from Qt.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox, QGridLayout, QHBoxLayout, QFrame


class CoordInputDialogRead(QDialog):
    def __init__(self, session=None, parent=None):
        super().__init__(parent)

        self.session = session
        self.x_input = None
        self.y_input = None
        self.z_input = None
        self.pixsize_input = None
        self.prefix_input = None
        self.suffix_input = None
        self.vol_combobox = None

        # Initialize the UI
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Create a dropdown for tomogram selection
        self.vol_combobox = QComboBox()
        layout.addWidget(QLabel("Select tomogram to get dimensions and voxel size in binned pixels (or leave as 'Custom')"))
        layout.addWidget(self.vol_combobox)

        # Populate the combobox with tomograms and a 'Custom' option
        self.vol_combobox.addItem("Custom", None)  # Allow custom input

        selected_tomogram = self.session.ArtiaX.selected_tomogram
        selected_index = None

        # Populate with tomograms
        for idx, vol in enumerate(self.session.ArtiaX.tomograms.iter()):
            self.vol_combobox.addItem(f"#{vol.id_string} - {vol.name}", vol)
            if selected_tomogram == vol:
                selected_index = idx + 1  # Account for 'Custom' option

        if selected_index is not None:
            self.vol_combobox.setCurrentIndex(selected_index)

        # Create a grid layout for volume dimensions and voxel size
        grid_layout = QGridLayout()

        # Create input fields for x, y, and z coordinates
        self.x_input = QLineEdit()
        self.y_input = QLineEdit()
        self.z_input = QLineEdit()
        self.pixsize_input = QLineEdit()
        self.prefix_input = QLineEdit()
        self.suffix_input = QLineEdit()

        # layout.addWidget(QLabel("Enter size of corresponding tomogram in binned pixels (x):"))
        # layout.addWidget(self.x_input)
        # layout.addWidget(QLabel("Enter size of corresponding tomogram in binned pixels (Y):"))
        # layout.addWidget(self.y_input)
        # layout.addWidget(QLabel("Enter size of corresponding tomogram in binned pixels (Z):"))
        # layout.addWidget(self.z_input)
        # layout.addWidget(QLabel("Enter pixelsize:"))
        # layout.addWidget(self.pixsize_input)
        # layout.addWidget(QLabel("Enter Tomogram number prefix in 'rlnTomoName':"))
        # layout.addWidget(self.prefix_input)
        # layout.addWidget(QLabel("Enter Tomogram number sufffix in 'rlnTomoName':"))
        # layout.addWidget(self.suffix_input)

        # # Add tomogram size inputs to the grid layout
        # grid_layout.addWidget(QLabel("Enter size of corresponding tomogram in binned pixels (X):"), 0, 0)
        # grid_layout.addWidget(self.x_input, 0, 1)
        #
        # grid_layout.addWidget(QLabel("Enter size of corresponding tomogram in binned pixels (Y):"), 1, 0)
        # grid_layout.addWidget(self.y_input, 1, 1)
        #
        # grid_layout.addWidget(QLabel("Enter size of corresponding tomogram in binned pixels (Z):"), 2, 0)
        # grid_layout.addWidget(self.z_input, 2, 1)
        #
        # grid_layout.addWidget(QLabel("Enter voxel size (angstrom):"), 3, 0)
        # grid_layout.addWidget(self.pixsize_input, 3, 1)
        #
        # grid_layout.addWidget(QLabel("Enter Tomogram number prefix in 'rlnTomoName':"), 4, 0)
        # grid_layout.addWidget(self.prefix_input, 4, 1)
        #
        # grid_layout.addWidget(QLabel("Enter Tomogram number suffix in 'rlnTomoName':"), 5, 0)
        # grid_layout.addWidget(self.suffix_input, 5, 1)

        # Horizontal layout for X, Y, Z
        xyz_layout = QHBoxLayout()
        xyz_layout.addWidget(self.x_input)
        xyz_layout.addWidget(QLabel("X"))
        xyz_layout.addWidget(self.y_input)
        xyz_layout.addWidget(QLabel("Y"))
        xyz_layout.addWidget(self.z_input)
        xyz_layout.addWidget(QLabel("Z"))

        # Add tomogram size inputs to the grid layout
        grid_layout.addWidget(QLabel("Set Volume Dimensions:"), 0, 0)
        grid_layout.addLayout(xyz_layout, 0, 1)  # Adding horizontal layout for X, Y, Z

        grid_layout.addWidget(QLabel("Enter voxel size (angstrom):"), 1, 0)
        grid_layout.addWidget(self.pixsize_input, 1, 1)

        # Add the grid layout to the main layout
        layout.addLayout(grid_layout)

        # Add a horizontal line for separation
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)  # Horizontal line
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Create labels and input fields for prefix and suffix
        layout.addWidget(QLabel("Enter Tomogram number prefix in 'rlnTomoName':"))
        layout.addWidget(self.prefix_input)
        layout.addWidget(QLabel("Enter Tomogram number suffix in 'rlnTomoName':"))
        layout.addWidget(self.suffix_input)



        # Submit button
        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.submit_input)
        layout.addWidget(submit_button)

        self.setLayout(layout)
        self.setWindowTitle("Additional Information")

        # Connect tomogram selection to dimension and voxel size update
        self.vol_combobox.currentIndexChanged.connect(self._on_tomogram_selected)

    def _on_tomogram_selected(self, idx):
        vol = self.vol_combobox.itemData(idx)
        if vol is None:
            # If "Custom" is selected, clear fields
            self.x_input.setText("")
            self.y_input.setText("")
            self.z_input.setText("")
            self.pixsize_input.setText("")
        else:
            # Fill in the fields with tomogram data
            x, y, z = vol.data.size
            voxelsize = vol.data.step[0]
            self.x_input.setText(str(x))
            self.y_input.setText(str(y))
            self.z_input.setText(str(z))
            self.pixsize_input.setText(str(voxelsize))

    def submit_input(self):
        # Validate input
        try:
            x_size = int(self.x_input.text())
            y_size = int(self.y_input.text())
            z_size = int(self.z_input.text())
            pixsize = float(self.pixsize_input.text())  # Get the name as a string
            prefix = self.prefix_input.text() or None
            suffix = self.suffix_input.text() or None

            # Return the values and accept the dialog
            self.accept()

            # Return the coordinates as a tuple
            return x_size, y_size, z_size, pixsize, prefix, suffix

        except ValueError:
            # If there's a validation error, show a message
            QMessageBox.warning(self, "Input Error", "Please enter valid integer values for X, Y, and Z and for the pixelsize and strings for prefix and suffix.")
            return None, None, None, None, None, None

    def get_info_read(self):
        """Returns the X, Y, Z coordinates and pixsize if valid, or None if the user cancels the dialog."""
        if self.exec_() == QDialog.Accepted:
            return self.submit_input()
        else:
            return None, None, None, None, None, None