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

    def __init__(self, name, session, particle_pairs=None, triangles=None):
        super().__init__(name, session)

        self.particle_pairs = particle_pairs
        if triangles is None:
            triangles = triangles_from_pairs(self.particle_pairs)
        self.tri = triangles

        self.update()
        session.logger.info("Created a triangulated surface.")

    def define_surface(self):
        b = _BildFile(self.session, 'dummy')

        for triangle in self.tri:
            b.polygon_command(
                ".polygon {} {} {} {} {} {} {} {} {}".format(*triangle[0], *triangle[1], *triangle[2]).split())

        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles

    def update(self):
        vertices, normals, triangles = self.define_surface()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full((len(vertices), 4), self.color)

    def recalc_and_update(self):
        if self.particle_pairs is not None:
            tris = triangles_from_pairs(self.particle_pairs)
            if len(tris) == 0:  # Particles removed so that no triangles can be made anymore
                self.particle_pairs = None
            else:
                self.tri = tris
        self.update()

    def write_file(self, file_name):
        with open(file_name, 'wb') as file:
            np.savez(file, model_type="TriangulationSurface", triangles=self.tri)


def make_links(markers, connections):
    from chimerax.markers.markers import create_link
    for polygon in connections:
        for i in range(0, len(polygon)):
            for j in range(i + 1, len(polygon)):
                try:
                    create_link(markers[polygon[i]], markers[polygon[j]])
                except TypeError:  # bond already exists
                    pass


def triangles_from_pairs(particle_pairs):
    triangles = np.zeros((0, 3, 3))
    while len(particle_pairs[0]) > 1:
        first_corner = particle_pairs[0][0]
        second_corner = particle_pairs[1][0]
        if not first_corner.deleted and not second_corner.deleted:
            bonds_that_contain_first = find_bonds_containing_corner(particle_pairs, first_corner)
            bonds_that_contain_second = find_bonds_containing_corner(particle_pairs, second_corner)
            for second_side in bonds_that_contain_second:
                third_corner = None
                if second_corner == particle_pairs[0][second_side]:
                    if not particle_pairs[1][second_side] == first_corner:
                        third_corner = particle_pairs[1][second_side]
                elif not particle_pairs[0][second_side] == first_corner:
                    third_corner = particle_pairs[0][second_side]
                if third_corner is not None and not third_corner.deleted:
                    for third_side in bonds_that_contain_first:
                        if third_corner == particle_pairs[0][third_side] or third_corner == particle_pairs[1][
                            third_side]:
                            triangles = np.append(triangles, [[first_corner.coord, second_corner.coord,
                                                               third_corner.coord]], axis=0)
        particle_pairs = np.delete(particle_pairs, 0, 1)

    return triangles


def find_bonds_containing_corner(particle_pairs, corner):
    bonds_containing_corner = np.array([])
    for bond in range(0, len(particle_pairs[0])):
        if particle_pairs[0][bond] == corner or particle_pairs[1][bond] == corner:
            bonds_containing_corner = np.append(bonds_containing_corner, bond)
    return bonds_containing_corner.astype(np.int)
