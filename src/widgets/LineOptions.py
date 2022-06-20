# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
import numpy as np
from functools import partial

# Qt
from Qt.QtCore import Qt, Signal
from Qt.QtGui import QColor
from Qt.QtWidgets import (
    QWidget,
    QStackedLayout,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QToolButton,
    QGroupBox,
    QLabel,
    QLineEdit,
    QLayout
)

# This package
from .LabelEditSlider import LabelEditSlider

class LineOptions(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.geomodel = None