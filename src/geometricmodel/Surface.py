# General imports
import numpy as np
import math
from scipy import interpolate

# ChimeraX imports
from chimerax.geometry import z_align, rotation, translation
from chimerax.bild.bild import _BildFile
from chimerax.atomic import AtomicShapeDrawing

# ArtiaX imports
from .GeoModel import GEOMODEL_CHANGED
from .PopulatedModel import PopulatedModel
from ..particle.SurfaceCollectionModel import SurfaceCollectionModel


class Surface(PopulatedModel):
    """Surface"""

    def __init__(self, name, session, particles, particle_pos, resolution, method):
        super().__init__(name, session)
        self.particles = particles
        self.particle_pos = particle_pos

        self.normal = get_normal_and_pos(particles, particle_pos)
        self.points = get_grid(particle_pos, self.normal, resolution, method)

        self.fitting_options = True
        self.method = method
        self.allowed_methods = ['nearest', 'linear', 'cubic']
        self.resolution = resolution
        self.resolution_edit_range = (10, 100)
        self.use_base = False
        self.base_level = 0
        self.base_level_edit_range = (-10, 10)

        self.rotation = 0

        self.update()

    def define_plane(self):
        nr_points = len(self.points)*len(self.points)
        vertices = np.zeros((nr_points*6, 3), dtype=np.float32)
        triangles = np.zeros((nr_points*2, 3), dtype=np.int32)
        normals = np.zeros((nr_points*6, 3), dtype=np.float32)
        nr_cols = len(self.points[0])
        vertex_index = 0
        triangles_index = 0
        self.ordered_normals = np.ones((len(self.points), len(self.points), 6), dtype=np.int32) * -1

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
                            self.ordered_normals[i][j][0] = vertex_index
                            self.ordered_normals[i][j-1][np.where(self.ordered_normals[i][j-1] == -1)[0][0]] = vertex_index
                            self.ordered_normals[i-1][j][np.where(self.ordered_normals[i-1][j] == -1)[0][0]] = vertex_index

                            vertex_index += 3
                            triangles_index += 1
                        if j+1 < nr_cols and not math.isnan(self.points[i-1][j+1][2]):
                            vertices[vertex_index:vertex_index + 3] = [point, self.points[i-1][j], self.points[i-1][j+1]]
                            triangles[triangles_index] = [vertex_index, vertex_index + 1, vertex_index + 2]
                            normal = np.cross(self.points[i-1][j+1] - self.points[i-1][j], point - self.points[i-1][j])
                            normal = normal / np.linalg.norm(normal)
                            normals[vertex_index: vertex_index + 3] = [normal, normal, normal]
                            self.ordered_normals[i][j][0] = vertex_index
                            self.ordered_normals[i-1][j][np.where(self.ordered_normals[i-1][j] == -1)[0][0]] = vertex_index
                            self.ordered_normals[i-1][j+1][np.where(self.ordered_normals[i-1][j+1] == -1)[0][0]] = vertex_index

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

    def create_spheres(self):
        self.has_particles = True
        self.triggers.activate_trigger(GEOMODEL_CHANGED, self)
        # Remove old spheres if any exist
        if len(self.indices):
            self.collection_model.delete_places(self.indices)
        self.spheres_places = []

        for i, row in enumerate(self.points):
            for j, vertex in enumerate(row):
                if not math.isnan(vertex[2]):
                    normal_indices = self.ordered_normals[i][j][self.ordered_normals[i][j] != -1]
                    normals = np.zeros((len(normal_indices), 3))
                    for k, index in enumerate(normal_indices):
                        normals[k] = self.normals[index]

                    normal = np.add.reduce(normals)
                    normal = - normal / np.linalg.norm(normal)  # - needed to make them point to pos z
                    rot_to_normal = z_align(vertex, vertex + normal).zero_translation().inverse()
                    theta = 0
                    if i+1 < len(self.points) and not math.isnan(self.points[i+1][j][2]):
                        to_next_point = self.points[i+1][j] - vertex
                        to_next_point = to_next_point - np.dot(to_next_point, normal) * normal  # projected onto plane
                        to_next_point = to_next_point/np.linalg.norm(to_next_point)
                        x_axes = rot_to_normal.transform_vector((1, 0, 0))
                        cross = np.cross(to_next_point, x_axes)
                        theta = math.acos(np.dot(x_axes, to_next_point)) * 180 / math.pi
                        if cross[2] > 0:
                            theta = -theta
                    rot_around_normal = rotation(rot_to_normal.z_axis(), theta + self.rotation)
                    rot = rot_around_normal * rot_to_normal
                    place = translation(vertex) * rot
                    self.spheres_places = np.append(self.spheres_places, place)

        self.indices = [str(i) for i in range(0, len(self.spheres_places))]
        self.collection_model.add_places(self.indices, self.spheres_places)
        self.collection_model.color = self.color

    def change_rotation(self, phi):
        if self.rotation != phi:
            self.rotation = phi
            self.create_spheres()


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