# vim: set expandtab shiftwidth=4 softtabstop=4:

#Qt
from Qt.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox


class CoordInputDialogRead(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.x_input = None
        self.y_input = None
        self.z_input = None
        self.pixsize_input = None

        # Initialize the UI
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Create input fields for x, y, and z coordinates
        self.x_input = QLineEdit()
        self.y_input = QLineEdit()
        self.z_input = QLineEdit()
        self.pixsize_input = QLineEdit()

        layout.addWidget(QLabel("Enter size of corresponding tomogram in binned pixels (x):"))
        layout.addWidget(self.x_input)
        layout.addWidget(QLabel("Enter size of corresponding tomogram in binned pixels (Y):"))
        layout.addWidget(self.y_input)
        layout.addWidget(QLabel("Enter size of corresponding tomogram in binned pixels (Z):"))
        layout.addWidget(self.z_input)
        layout.addWidget(QLabel("Enter pixelsize:"))
        layout.addWidget(self.pixsize_input)

        # Submit button
        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.submit_input)
        layout.addWidget(submit_button)

        self.setLayout(layout)
        self.setWindowTitle("Additional Information")

    def submit_input(self):
        # Validate input
        try:
            x_size = int(self.x_input.text())
            y_size = int(self.y_input.text())
            z_size = int(self.z_input.text())
            pixsize = int(self.pixsize_input.text())  # Get the name as a string

            # Return the values and accept the dialog
            self.accept()

            # Return the coordinates as a tuple
            return x_size, y_size, z_size, pixsize

        except ValueError:
            # If there's a validation error, show a message
            QMessageBox.warning(self, "Input Error", "Please enter valid integer values for X, Y, and Z.")
            return None, None, None, None

    def get_info_read(self):
        """Returns the X, Y, Z coordinates and pixsize if valid, or None if the user cancels the dialog."""
        if self.exec_() == QDialog.Accepted:
            return int(self.x_input.text()), int(self.y_input.text()), int(self.z_input.text()), int(self.pixsize_input.text())
        else:
            return None, None, None, None