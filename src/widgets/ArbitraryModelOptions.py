# vim: set expandtab shiftwidth=4 softtabstop=4:

from Qt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
)


class ArbitraryModelOptions(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.arbitrary_model = None

        layout = QVBoxLayout()
        arbitrary_model_options_label = QLabel("Arbitrary Model Options")
        layout.addWidget(arbitrary_model_options_label)

        self.setLayout(layout)

    def set_arbitrary_model(self, arbitrary_model):
        self.arbitrary_model = arbitrary_model
