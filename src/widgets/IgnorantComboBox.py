# vim: set expandtab shiftwidth=4 softtabstop=4:

# Qt
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QComboBox


class IgnorantComboBox(QComboBox):
    """ Combobox that doesn't acquire focus when scrolling over it."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, e: QWheelEvent) -> None:
        if not self.hasFocus():
            e.ignore()
        else:
            super().wheelEvent(e)

