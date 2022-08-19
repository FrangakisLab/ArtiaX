# vim: set expandtab shiftwidth=4 softtabstop=4:

from Qt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
)


class SphereOptions(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.sphere = None

        layout = QVBoxLayout()
        sphere_options_label = QLabel("Sphere Options")
        layout.addWidget(sphere_options_label)

        #Update
        self.update_button = QPushButton("Update Sphere")
        self.update_button.setToolTip("Updates the sphere to fit the particles. Useful when the boundary doesn't "
                                      "match the desired boundary; simply move the particles that define the boundary "
                                      "and press this button to update the boundary.")
        layout.addWidget(self.update_button)


        #Reorient
        self.reorient_button = QPushButton("Reorient particles")
        self.reorient_button.setToolTip("Reorient the selected particles so that their z-axis points away from sphere"
                                        " center")
        layout.addWidget(self.reorient_button)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        self.setLayout(layout)

        self._connect()

    def set_sphere(self, sphere):
        self.sphere = sphere

    def _connect(self):
        self.update_button.clicked.connect(self._update)
        self.reorient_button.clicked.connect(self._reorient)

    def _update(self):
        if self.sphere is not None:
            self.sphere.recalc_and_update()

    def _reorient(self):
        if self.sphere is not None:
            self.sphere.orient_particles()
