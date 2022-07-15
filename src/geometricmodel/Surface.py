# General imports
import numpy as np
import math
from scipy import interpolate

# ArtiaX imports
from .GeoModel import GeoModel


class Surface(GeoModel):
    """Surface"""

    def __init__(self, name, session, particles, particle_pos, normal, points, resolution, method):
        super().__init__(name, session)
        self.particles = particles
        self.particle_pos = particle_pos
        self.normal = normal

        self.points = points

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
        nr_points = len(self.points)*len(self.points)
        vertices = np.zeros((nr_points*6, 3), dtype=np.float32)
        triangles = np.zeros((nr_points*2, 3), dtype=np.int32)
        normals = np.zeros((nr_points*6, 3), dtype=np.float32)
        nr_cols = len(self.points[0])
        vertex_index = 0
        triangles_index = 0

        for i, row in enumerate(self.points):
            for j, point in enumerate(row):
                if not math.isnan(point[2]):
                    if i-1 >= 0 and not math.isnan(self.points[i-1][j][2]):
                        if j-1 >= 0 and not math.isnan(self.points[i][j-1][2]):
                            vertices[vertex_index:vertex_index+3] = [point, self.points[i][j-1], self.points[i-1][j]]
                            triangles[triangles_index] = [vertex_index, vertex_index+1, vertex_index+2]
                            normal = np.cross(self.points[i][j-1] - point, self.points[i-1][j] - point)
                            normal = normal / np.linalg.norm(normal)
                            normals[vertex_index: vertex_index+3] = [normal, normal, normal]
                            vertex_index += 3
                            triangles_index += 1
                        if j+1 < nr_cols and not math.isnan(self.points[i-1][j+1][2]):
                            vertices[vertex_index:vertex_index + 3] = [point, self.points[i-1][j], self.points[i-1][j+1]]
                            triangles[triangles_index] = [vertex_index, vertex_index + 1, vertex_index + 2]
                            normal = np.cross(self.points[i-1][j+1] - self.points[i-1][j], point - self.points[i-1][j])
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
        self.normal, self.particle_pos = get_normal_and_pos(self.particles)
        if self.use_base:
            self.points = get_grid(self.particle_pos, self.normal, self.resolution, self.method, base=self.base_level)
        else:
            self.points = get_grid(self.particle_pos, self.normal, self.resolution, self.method)
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


def get_grid(particle_pos, normal, resolution, method, base=None):
    # Create ON system u,v,n
    u = np.array([1,0,0], dtype=np.float64)
    u -= u.dot(normal) * normal
    u /= np.linalg.norm(u)
    v = np.cross(normal, u)

    # Transform points to new system
    T = [u,v,normal]
    particle_pos_uvn = np.matmul(T,particle_pos.T).T
    lower = np.amin(particle_pos_uvn, axis=0)
    upper = np.amax(particle_pos_uvn, axis=0)
    resolution = complex(0, resolution)
    grid_u, grid_v = np.mgrid[lower[0]:upper[0]:resolution, lower[1]:upper[1]:resolution]

    # Calculate mesh in new system
    if base is None:
        grid_n = interpolate.griddata(particle_pos_uvn[:, :2], particle_pos_uvn[:, 2], (grid_u, grid_v), method=method)
    else:
        grid_n = interpolate.griddata(particle_pos_uvn[:, :2], particle_pos_uvn[:, 2], (grid_u, grid_v), method=method,
                                      fill_value=base)

    # Translate back to old system
    points_uvn = np.dstack((grid_u, grid_v, grid_n))
    points = np.zeros(points_uvn.shape)
    for i, row in enumerate(points_uvn):
        points[i] = np.matmul(np.linalg.inv(T), row.T).T

    return points


def get_normal_and_pos(particles, particle_pos=None):
    return_pos = False
    if particle_pos is None:
        return_pos = True
        particle_pos = np.zeros((len(particles), 3))
        # Each row is one currently selected particle, with columns being x,y,z
        for i, particle in enumerate(particles):
            particle_pos[i] = [particle.coord[0], particle.coord[1], particle.coord[2]]

    # subtract out the centroid and take the SVD
    svd = np.linalg.svd(particle_pos - particle_pos.mean(0))
    # Normal is now the last row of the 3x3 scd[2] (vh) matrix
    normal = svd[2][2, :]
    # Make sure z part is positive otherwise it didnt work
    if normal[2] < 0:
        normal = -normal

    if return_pos:
        return normal, particle_pos
    else:
        return normal
