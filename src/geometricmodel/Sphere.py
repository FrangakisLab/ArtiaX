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
        self.change_transparency(100)

        self.center = pos
        self.r = r

        self.update()
        print("Created sphere with center: {} and radius: {}".format(pos, r))

    def define_sphere(self):
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')
        b.sphere_command('.sphere {} {} {} {}'.format(self.center[0], self.center[1], self.center[2], self.r).split())

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    def update(self):
        vertices, normals, triangles, vertex_colors = self.define_sphere()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full(np.shape(vertex_colors), self.color)

    def change_radius(self, r):
        self.r = r
        self.update()

    def translate(self, pos):
        self.center = pos
        self.update()