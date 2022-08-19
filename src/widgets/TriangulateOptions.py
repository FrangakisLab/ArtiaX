# vim: set expandtab shiftwidth=4 softtabstop=4:

from Qt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
)


class TriangulateOptions(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.triangulation_surface = None

        layout = QVBoxLayout()
        triangulation_options_label = QLabel("Triangulation Surface Options")
        layout.addWidget(triangulation_options_label)

        #Update
        self.update_button = QPushButton("Update Triangulation Surface")
        self.update_button.setToolTip("Updates the triangulation surface to fit the particles. Useful when the boundary"
                                      " doesn't match the desired boundary; simply move the particles that define the "
                                      "boundary and press this button to update the boundary.")
        layout.addWidget(self.update_button)

        #Reorient
        self.reorient_button = QPushButton("Reorient particles")
        self.reorient_button.setToolTip("Reorient the selected particles so that their z-axis points away from the "
                                        "surface")
        layout.addWidget(self.reorient_button)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        self.setLayout(layout)

        self._connect()

    def set_tri_surface(self, tri_surface):
        self.triangulation_surface = tri_surface

    def _connect(self):
        self.update_button.clicked.connect(self._update)
        self.reorient_button.clicked.connect(self._reorient)

    def _update(self):
        if self.triangulation_surface is not None:
            self.triangulation_surface.recalc_and_update()

    def _reorient(self):
        if self.triangulation_surface is not None:
            from ..geometricmodel.GeoModel import get_curr_selected_particles
            s_particles = get_curr_selected_particles(self.session, return_particles=True, return_pos=False)
            self.triangulation_surface.orient_particles(s_particles)

