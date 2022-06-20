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

class Sphere(GeoModel):
    """Sphere"""

    def __init__(self, name, session, pos, r):
        super().__init__(name, session)

        self.pos = pos
        self.r = r

        self.update()

    def define_sphere(self):
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')
        b.transparency_command('.transparency {}'.format(self._color[3]/255).split())
        bild_color = np.multiply(self.color, 1/255)
        b.color_command('.color {} {} {}'.format(*bild_color).split())
        b.sphere_command('.sphere {} {} {} {}'.format(self.pos[0], self.pos[1], self.pos[2], self.r).split())

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    def update(self):
        vertices, normals, triangles, vertex_colors = self.define_sphere()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = vertex_colors

    def change_radius(self, r):
        self.r = r
        self.update()

    def translate(self, pos):
        self.pos = pos
        self.update()