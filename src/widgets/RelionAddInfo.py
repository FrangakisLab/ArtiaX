# vim: set expandtab shiftwidth=4 softtabstop=4:

#Qt
from Qt.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox


class CoordInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.name_input = None

        # Initialize the UI
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Create input fields for name
        self.name_input = QLineEdit()

        layout.addWidget(QLabel("Enter corresponding tomogram name, will overwrite existing name:"))
        layout.addWidget(self.name_input)

        # Submit button
        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.submit_input)
        layout.addWidget(submit_button)

        self.setLayout(layout)
        self.setWindowTitle("Additional Information")

    def submit_input(self):
        # Validate input
        try:
            tomogram_name = self.name_input.text()  # Get the name as a string

            if not tomogram_name:
                raise ValueError("Name cannot be empty")  # Ensure name is not empty
            # Return the values and accept the dialog
            self.accept()

            # Return the coordinates as a tuple
            return tomogram_name

        except ValueError:
            # If there's a validation error, show a message
            QMessageBox.warning(self, "Input Error", "Please enter valid name")
            return None

    def get_info(self):
        """Returns the name if valid, or None if the user cancels the dialog."""
        if self.exec_() == QDialog.Accepted:
            return self.name_input.text()
        else:
            return None