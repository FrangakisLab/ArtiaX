# General imports
import numpy as np
import math
from scipy import interpolate
from itertools import chain

# ChimeraX imports
from chimerax.core.commands import run
from chimerax.core.errors import UserError
from chimerax.core.models import Model
from chimerax.map import Volume
from chimerax.atomic import Atom
from chimerax.graphics import Drawing
from .GeoModel import GeoModel
from chimerax.geometry import z_align

class Plane(GeoModel):
    """Plane"""

    def __init__(self, name, session, particles, grid_x, grid_y, grid_z, resolution, method):
        super().__init__(name, session)
        self.particles = particles

        self.grid_x = grid_x
        self.grid_y = grid_y
        self.grid_z = grid_z

        self.fitting_options = True
        self.method = method
        self.allowed_methods = ['nearest', 'linear', 'cubic']
        self.resolution = resolution
        self.resolution_edit_range = (10, 200)
        self.use_base = False
        self.base_level = 0
        self.base_level_edit_range = (-10, 10)

        self.update()

    def define_plane(self):
        vertices = np.dstack((self.grid_x.flatten(), self.grid_y.flatten(), self.grid_z.flatten()))
        triangles = np.array((0,3))
        # TODO comment away stuff below and calculate d,v,n on your own

        points = np.dstack((self.grid_x, self.grid_y, self.grid_z))
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')
        nr_rows = len(self.grid_x)
        nr_cols = len(self.grid_x[0])
        for i, row in enumerate(points):
            for j, point in enumerate(row):
                if not math.isnan(point[2]):
                    if i+1 < nr_rows and not math.isnan(points[i+1][j][2]):
                        if j-1 >= 0 and not math.isnan(points[i+1][j-1][2]):
                            b.polygon_command(".polygon {} {} {} {} {} {} {} {} {}".format(*point, *points[i+1][j],
                                                                                           *points[i+1][j-1]).split())
                        if j+1 < nr_cols and not math.isnan(points[i][j+1][2]):
                            b.polygon_command(".polygon {} {} {} {} {} {} {} {} {}".format(*point, *points[i+1][j],
                                                                                           *points[i][j+1]).split())

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    def update(self):
        vertices, normals, triangles, vertex_colors = self.define_plane()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full(np.shape(vertex_colors), self.color)

    def recalc_and_update(self):
        if self.use_base:
            self.grid_x, self.grid_y, self.grid_z = get_grid(self.session, self.particles, self.resolution, self.method,
                                                             self.base_level)
        else:
            self.grid_x, self.grid_y, self.grid_z = get_grid(self.session, self.particles, self.resolution, self.method)
        self.update()

    def change_method(self, method):
        if self.method != method and method in self.allowed_methods:
            self.method = method
            self.recalc_and_update()

    def change_resolution(self, res):
        if self.resolution != res:
            self.resolution = res
            self.recalc_and_update()

    def change_base(self, b):
        if self.base_level != b:
            self.base_level = b
            self.recalc_and_update()


def get_grid(session, particles, resolution, method, base=None, particle_pos=None):
    if particle_pos is None:
        particle_pos = np.zeros((0, 3))  # each row is one currently selected particle, with columns being x,y,z
        for particle in particles:
            x_pos = particle.coord[0]
            y_pos = particle.coord[1]
            z_pos = particle.coord[2]
            particle_pos = np.append(particle_pos, [[x_pos, y_pos, z_pos]], axis=0)

    lower = np.amin(particle_pos, axis=0)
    upper = np.amax(particle_pos, axis=0)
    resolution = complex(0, resolution)
    grid_x, grid_y = np.mgrid[lower[0]:upper[0]:resolution, lower[1]:upper[1]:resolution]
    if base is None:
        grid_z = interpolate.griddata(particle_pos[:, :2], particle_pos[:, 2], (grid_x, grid_y), method=method)
    else:
        grid_z = interpolate.griddata(particle_pos[:, :2], particle_pos[:, 2], (grid_x, grid_y), method=method,
                                      fill_value=base)
    return grid_x, grid_y, grid_z
