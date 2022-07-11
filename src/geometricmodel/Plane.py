# General imports
import numpy as np
import math
from scipy import interpolate
from itertools import chain
import pyvista as pv

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

    def __init__(self, name, session, particles, grid_x, grid_y, grid_z):
        super().__init__(name, session)
        self.particles = particles

        self.grid_x = grid_x
        self.grid_y = grid_y
        self.grid_z = grid_z

        self.update()

    def define_plane(self):
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')

        command_string = [".polygon"]
        flat_x = list(chain(*self.grid_x))
        flat_y = list(chain(*self.grid_y))
        flat_z = list(chain(*self.grid_z))
        points = np.vstack(flat_x, flat_y, flat_z)

        cloud = pv.PolyData(points)
        surf = cloud.delaunay_2d()
        for i in range(0, len(flat_x)):
            command_string.append(str(flat_x[i]))
            command_string.append(str(flat_y[i]))
            command_string.append(str(flat_z[i]))
        b.polygon_command(command_string)

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    def update(self):
        vertices, normals, triangles, vertex_colors = self.define_plane()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full(np.shape(vertex_colors), self.color)

def get_grid(session, particles, resolution, method, particle_pos=None):
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
    grid_z = interpolate.griddata(particle_pos[:, :2], particle_pos[:, 2], (grid_x, grid_y), method=method)
    return grid_x, grid_y, grid_z

points = [[0,0,1], [0, 1, 2], [1, 0, 2], [1, 1, 2]]
d = AtomicShapeDrawing('shapes')
command_string = ".pylogon 0 0 1 0 1 2 1 0 2"
b.polygon_command(command_string.split())
d.add_shapes(b.shapes)
l.set_geometry(d.vertices, d.normals, d.triangles)