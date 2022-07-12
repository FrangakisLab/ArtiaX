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
        self.resolution_edit_range = (10, 100)
        self.use_base = False
        self.base_level = 0
        self.base_level_edit_range = (-10, 10)

        self.update()

    def define_plane(self):
        nr_points = len(self.grid_x)*len(self.grid_x[0])
        vertices = np.zeros((nr_points*6, 3), dtype=np.float32)
        triangles = np.zeros((nr_points*2, 3), dtype=np.int32)
        normals = np.zeros((nr_points*6, 3), dtype=np.float32)
        nr_cols = len(self.grid_x[0])
        vertex_index = 0
        triangles_index = 0

        points = np.dstack((self.grid_x, self.grid_y, self.grid_z))
        for i, row in enumerate(points):
            for j, point in enumerate(row):
                if not math.isnan(point[2]):
                    if i-1 >= 0 and not math.isnan(points[i-1][j][2]):
                        if j-1 >= 0 and not math.isnan(points[i][j-1][2]):
                            vertices[vertex_index:vertex_index+3] = [point, points[i][j-1], points[i-1][j]]
                            triangles[triangles_index] = [vertex_index, vertex_index+1, vertex_index+2]
                            normal = np.cross(points[i][j-1] - point, points[i-1][j] - point)
                            normal = normal / np.linalg.norm(normal)
                            normals[vertex_index: vertex_index+3] = [normal, normal, normal]
                            vertex_index += 3
                            triangles_index += 1
                        if j+1 < nr_cols and not math.isnan(points[i-1][j+1][2]):
                            vertices[vertex_index:vertex_index + 3] = [point, points[i-1][j], points[i-1][j+1]]
                            triangles[triangles_index] = [vertex_index, vertex_index + 1, vertex_index + 2]
                            normal = np.cross(points[i-1][j+1] - points[i-1][j], point - points[i-1][j])
                            normal = normal / np.linalg.norm(normal)
                            normals[vertex_index: vertex_index + 3] = [normal, normal, normal]
                            vertex_index += 3
                            triangles_index += 1
        vertices = vertices[:vertex_index]
        triangles = triangles[:triangles_index]
        normals = normals[:vertex_index]
        triangles = triangles.astype(np.int32)

        return vertices, normals, triangles

    def update(self):
        vertices, normals, triangles = self.define_plane()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full((len(vertices), 4), self.color)

    def recalc_and_update(self):
        if self.use_base:
            self.grid_x, self.grid_y, self.grid_z = get_grid(self.session, self.particles, self.resolution, self.method,
                                                             base=self.base_level)
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
