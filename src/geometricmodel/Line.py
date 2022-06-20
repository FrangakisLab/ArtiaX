# General imports
import numpy as np
import math

# ChimeraX imports
from chimerax.core.commands import run
from chimerax.core.errors import UserError
from chimerax.core.models import Model
from chimerax.map import Volume
from chimerax.atomic import Atom
from chimerax.graphics import Drawing
from .GeoModel import GeoModel


class Line(GeoModel):
    """Line between two points"""

    def __init__(self, name, session, start, end):
        super().__init__(name, session)

        self.start = start
        self.end = end

        self.update()

    def define_line(self):
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')
        b.transparency_command('.transparency {}'.format(self._color[3]/255).split())
        bild_color = np.multiply(self.color, 1/255)
        b.color_command('.color {} {} {}'.format(*bild_color).split())
        b.cylinder_command(".vector {} {} {} {} {} {} 1".format(*self.start, *self.end).split())

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    def update(self):
        vertices, normals, triangles, vertex_colors = self.define_line()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = vertex_colors
