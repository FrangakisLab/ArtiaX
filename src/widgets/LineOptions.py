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
from .LabelEditRangeSlider import LabelEditRangeSlider

class LineOptions(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.geomodel = None

        self.layout = QVBoxLayout()

        self.spacing_slider = LabelEditRangeSlider((0,200), "spacing")

        self.layout.addWidget(self.spacing_slider)
        self.setLayout(self.layout)