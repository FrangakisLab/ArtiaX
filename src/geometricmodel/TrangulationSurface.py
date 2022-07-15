# General imports
import numpy as np
import math
from scipy import interpolate

# ChimeraX imports
from chimerax.bild.bild import _BildFile
from chimerax.atomic import AtomicShapeDrawing

# ArtiaX imports
from .GeoModel import GeoModel


class TriangulationSurface(GeoModel):
    """Triangulated Plane"""

    def __init__(self, name, session, triangles):
        super().__init__(name, session)

        self.tri = triangles

        self.update()

    def define_surface(self):
        b = _BildFile(self.session, 'dummy')

        for triangle in self.tri:
            b.polygon_command(".polygon {} {} {} {} {} {} {} {} {}".format(*triangle[0], *triangle[1], *triangle[2]).split())

        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles


    def update(self):
        vertices, normals, triangles = self.define_surface()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full((len(vertices), 4), self.color)


def make_links(markers, connections):
    from chimerax.markers.markers import create_link
    for polygon in connections:
        for i in range(0, len(polygon)):
            for j in range(i+1, len(polygon)):
                try:
                    create_link(markers[polygon[i]], markers[polygon[j]])
                except TypeError:  # bond already exists
                    pass

