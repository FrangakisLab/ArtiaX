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
    QToolButton,
    QGroupBox,
    QLabel,
)

# This package
from .LabelEditSlider import LabelEditSlider



class ColorGeomodelWidget(QWidget):

    # from P. Green-Armytage (2010): A Colour Alphabet and the Limits of Colour Coding. //
    # Colour: Design & Creativity (5) (2010): 10, 1-23
    # https://eleanormaclure.files.wordpress.com/2011/03/colour-coding.pdf
    # skipped ebony, yellow
    green_armytage = [[(240, 163, 255, 255), (  0, 117, 220, 255), (153,  63,   0, 255)],
                      [( 76,   0,  92, 255), (  0,  92,  49, 255), ( 43, 206,  72, 255)],
                      [(255, 204, 153, 255), (128, 128, 128, 255), (148, 255, 181, 255)],
                      [(143, 124,   0, 255), (157, 204,   0, 255), (194,   0, 136, 255)],
                      [(  0,  51, 128, 255), (255, 164,   5, 255), (255, 168, 187, 255)],
                      [( 66, 102,   0, 255), (255,   0,  16, 255), ( 94, 241, 242, 255)],
                      [(  0, 153, 143, 255), (224, 255, 102, 255), (116,  10, 255, 255)],
                      [(153,   0,   0, 255), (255, 255, 128, 255), (255,  80,   5, 255)]]

    colorChanged = Signal(tuple, np.ndarray)
    colormapChanged = Signal(tuple, str, str, float, float)

    def __init__(self, session, parent=None):
        super().__init__(parent=parent)

        self.session = session
        self.geomodel = None
        self._color = None

        # The contents
        self._layout = QHBoxLayout()
        self.group = QWidget()

        # Buttons
        _button_layout = QGridLayout()
        self.col_cols = 8
        self.col_rows = 3
        self.buttons = [[QToolButton() for i in range(self.col_rows)] for j in range(self.col_cols)]
        for col in range(self.col_cols):
            for row in range(self.col_rows):
                w = self.buttons[col][row]
                color = self.green_armytage[col][row]
                w.setStyleSheet('background-color: rgba({},{},{},{});'.format(*color))
                _button_layout.addWidget(w, row, col, 1, 1)

        _right_side_layout = QVBoxLayout()
        self.pick_color_button = QPushButton("Pick Custom")

        self._display_label = QLabel("Current Color")
        self.current_color_label = QLabel()
        self.current_color_label.setMinimumSize(50, 30)

        _right_side_layout.addStretch()
        _right_side_layout.addWidget(self._display_label, alignment=Qt.AlignCenter)
        _right_side_layout.addWidget(self.current_color_label, alignment=Qt.AlignCenter)
        _right_side_layout.addWidget(self.pick_color_button, alignment=Qt.AlignCenter)
        _right_side_layout.addStretch()

        # Transparency slider
        self.transparency_slider = LabelEditSlider((0, 100), 'Transparency [%]:')
        self.transparency_slider.value = 0

        _full_layout = QVBoxLayout()
        _color_box_layout = QHBoxLayout()

        _color_box_layout.addLayout(_button_layout)
        _color_box_layout.addLayout(_right_side_layout)
        _full_layout.addLayout(_color_box_layout)
        _full_layout.addWidget(self.transparency_slider)
        self.group.setLayout(_full_layout)

        self.color_group = QGroupBox("Color")
        self._color_group_layout = QStackedLayout()
        self._color_group_layout.addWidget(self.group)
        self.color_group.setLayout(self._color_group_layout)

        self._layout.addWidget(self.color_group)
        self.setLayout(self._layout)

        self._connect()

    def set_geomodel(self, geomodel):
        self.geomodel = geomodel
        self._color = np.array(geomodel.color, dtype=np.uint8)
        self._set_color()

        self._color_changed()


    def _connect(self):
        # Buttons
        for col in range(self.col_cols):
            for row in range(self.col_rows):
                self.buttons[col][row].clicked.connect(partial(self._col_clicked, self.green_armytage[col][row]))
        self.pick_color_button.clicked.connect(self._pick_color)

        #Transparency
        self.transparency_slider.valueChanged.connect(self._transparency_changed)


    def _col_clicked(self, color):
        self._color[:3] = np.array(color[:3], dtype=np.uint8)
        self._set_color()

        self._color_changed()

    def _set_color(self):
        self.current_color_label.setStyleSheet('background-color: rgba({},{},{},255);'.format(*tuple(self._color[:3])))
        self.transparency_slider.value = (255 - self._color[3]) * 100 / 255

    def _pick_color(self):
        from Qt.QtWidgets import QColorDialog
        cd = QColorDialog(self.window())
        cd.setOption(cd.NoButtons, True)
        cd.currentColorChanged.connect(self._picker_cb)
        cd.destroyed.connect(self._picker_destroyed_cb)
        cd.setOption(cd.ShowAlphaChannel, False)
        if self._color is not None:
            cd.setCurrentColor(QColor(*tuple(self._color)))
        cd.show()

    def _picker_cb(self, color: QColor):
        self._color = np.array([color.red(), color.green(), color.blue(), color.alpha()], dtype=np.uint8)
        self._set_color()

        self._color_changed()

    def _picker_destroyed_cb(self):
        pass

    def _color_changed(self):
        self.colorChanged.emit(self.geomodel.id, self._color)

    def _transparency_changed(self, value):
        alpha = round((100 - value) * 255 / 100)
        self._color[3] = alpha
        self._color_changed()
