# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
from typing import List, Tuple

# Qt
from Qt.QtCore import Qt
from Qt.QtWidgets import (
    QWidget,
    QFrame,
    QComboBox,
    QLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
)


class SaveArgsWidget(QFrame):

    def __init__(self, session, category="particle list", parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.category = category

        if not hasattr(self.session, "ArtiaX"):
            return

        self._layout = QVBoxLayout()

        # Choose Model
        artia = self.session.ArtiaX
        self._list_combo_layout = QHBoxLayout()
        if self.category == "particle list":
            self.model_label = QLabel("Particle List:")
            self.manager_model = artia.partlists
            selected = self.manager_model.get(artia.selected_partlist)
        elif self.category == "geometric model":
            self.model_label = QLabel("Geometric Model:")
            self.manager_model = artia.geomodels
            selected = self.manager_model.get(artia.selected_geomodel)

        self.model_combo = QComboBox()

        sel_idx = None
        for idx, m in enumerate(self.manager_model.child_models()):
            if selected == m:
                sel_idx = idx
            txt = "#{} - {}".format(m.id_string, m.name)
            self.model_combo.addItem(txt)

        if sel_idx is not None:
            self.model_combo.setCurrentIndex(sel_idx)
        else:
            if len(self.manager_model.child_models()) > 0:
                self.model_combo.setCurrentIndex(0)

        self._list_combo_layout.addWidget(
            self.model_label, alignment=Qt.AlignmentFlag.AlignLeft
        )
        self._list_combo_layout.addWidget(
            self.model_combo, alignment=Qt.AlignmentFlag.AlignLeft
        )

        self._layout.addLayout(self._list_combo_layout)

        layouts, widgets_alignment = self.additional_content()

        for lay in layouts:
            self._layout.addLayout(lay)

        for wid, ali in widgets_alignment:
            self._layout.addWidget(wid, alignment=ali)

        self.setLayout(self._layout)

    def additional_content(self) -> Tuple[List[QLayout], List[Tuple[QWidget, int]]]:
        """
        File formats that require additional save parameters should override this function. It should return a list of
        additional QLayouts and a list of tuples of (QWidget, QAlignment). Layouts are added first.

        Returns
        -------
        layouts : list of QLayout
            layouts to be added to the frame

        widgets_alignment : list of (QWidget, QAlignment)
            Widgets to be added to the frame and their alignment in the main layout

        """
        layouts = []
        widgets_alignment = []
        return layouts, widgets_alignment

    def additional_argument_string(self) -> str:
        """
        File formats that require additional save parameters should override this function. It should return a string
        that contains the additional arguments for the save commands derived from the widgets defined in
        SaveArgsWidget.additional_content.
        """
        return ""

    def get_argument_string(self) -> str:
        # Model index
        mdl_idx = self.model_combo.currentIndex()
        id_string = self.manager_model.get(mdl_idx).id_string

        if self.category == "particle list":
            txt = "partlist #{} {}".format(id_string, self.additional_argument_string())
        elif self.category == "geometric model":
            txt = "geomodel #{} {}".format(id_string, self.additional_argument_string())
        else:
            txt = ""

        return txt
