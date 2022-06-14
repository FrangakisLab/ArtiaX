# General imports
import numpy as np

# ChimeraX imports
from chimerax.core.commands import run
from chimerax.core.errors import UserError
from chimerax.core.models import Model
from chimerax.map import Volume
from chimerax.atomic import Atom
from chimerax.graphics import Drawing


class GeoModel(Model):
    """Handles geometric models"""

    def __init__(self, name, session, pos, r):
        super().__init__(name, session)

        vertices, normals, triangles, vertex_colors = self.define_sphere(pos, r)
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = vertex_colors

    # TODO move this to a good spot and fix transparancy
    def define_sphere(self, pos, r):
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')
        b.transparency_command('.transparency 0.7'.split())
        b.color_command('.color 1 0 0'.split())
        b.sphere_command('.sphere {} {} {} {}'.format(pos[0], pos[1], pos[2], r).split())

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors
