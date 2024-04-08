# General imports
import numpy as np
import math
from scipy import interpolate

# ChimeraX imports
from chimerax.geometry import z_align, rotation, translation
from chimerax.core.models import Model

# ArtiaX imports
from .GeoModel import GEOMODEL_CHANGED
from .PopulatedModel import PopulatedModel


class Surface(PopulatedModel):
    """
    Fits a surface through the given particles. Assumes the given particles define a 2D function w = f(u,v),
    where w is taken to be the normal to the best fit plane of the points. The normal and the plane is calculated
    if it is not provided. The points that define the surface are also calculated from if not provided.
    Can be used to create particles along the surface.
    """

    def __init__(self, name, session, particle_pos, resolution, method, particles=None, normal=None, points=None):
        super().__init__(name, session)
        self.particles = particles
        """n-long list containing all particles used to define the sphere."""
        self.particle_pos = particle_pos
        """(n x 3) list containing all xyz positions of the particles."""

        # Has to get either normal or particles to make a surface
        if normal is None:
            self.normal = get_normal_and_pos(particles, particle_pos)
        else:
            self.normal = normal
        """The normal is taken to be the w axis, the function value axis."""
        if points is None:
            self.points = get_grid(particle_pos, self.normal, resolution, method)
        else:
            self.points = points
        """Defines the discrete surface."""

        self.fitting_options = True
        self.method = method
        """which method to use to interpolate the surface"""
        self.allowed_methods = ['nearest', 'linear', 'cubic']
        self.resolution = resolution
        """the surface is defined by resolution*resolution number of points."""
        self.resolution_edit_range = (10, 100)
        self.use_base = False
        self.base_level = 0
        """Can add a base level for points that can't be interpolated."""
        self.base_level_edit_range = (-10, 10)

        self.rotation = 0
        """how much to rotate """

        self.update()
        session.logger.info("Created a Surface through {} particles with normal ({:.2f}, {:.2f}, "
                            "{:.2f}).".format(len(particle_pos), *self.normal))

    def define_plane(self):
        """Created manually and not with chimerax.bild to save time, as every triangle has to be made individually.
        Goes through the points one by one and creates triangles. Adds the vertices for every triangle, even if it
        already exists in the list. Also adds the normal to all three vertices... because otherwise it looked odd."""
        nr_points = len(self.points)*len(self.points)
        vertices = np.zeros((nr_points*6, 3), dtype=np.float32)
        triangles = np.zeros((nr_points*2, 3), dtype=np.int32)
        normals = np.zeros((nr_points*6, 3), dtype=np.float32)
        nr_cols = len(self.points[0])
        vertex_index = 0
        triangles_index = 0
        # Used to know which normals are associated with each vertex, which makes it easier to create the fake
        # particles later
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
        """Recalculates the points from the particles and then redraws."""
        if self.particles is not None:
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
        """Creates the fake particles in every vertex of the surface. One axis is set to point along the average
        normal of the vertex, and the other is set to point to the next particle. """
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

                    # calculates the average normal for the vertex.
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

    def write_file(self, file_name):
        with open(file_name, 'wb') as file:
            np.savez(file, model_type="Surface", particle_pos=self.particle_pos, resolution=self.resolution,
                     method=self.method, normal=self.normal, points=self.points)

    def take_snapshot(self, session, flags):
        data = {
            "particle_pos": self.particle_pos,
            "resolution": self.resolution,
            "method": self.method,
            "normal": self.normal,
            "points": self.points
        }
        data['model state'] = Model.take_snapshot(self, session, flags)
        return data

    @classmethod
    def restore_snapshot(cls, session, data):
        particle_pos = data["particle_pos"]
        resolution = data["resolution"]
        method = data["method"]
        normal = data["normal"]
        points = data["points"]
        model = cls("Surface", session, particle_pos, resolution, method, normal=normal, points=points)
        Model.set_state_from_snapshot(model, session, data['model state'])
        return model

    def reorient_to_surface(self):
        from chimerax.geometry._geometry import find_closest_points
        from chimerax.geometry import z_align
        ps = []
        pls = []
        search_length = 10
        for particle_list in self.session.ArtiaX.partlists.child_models():
            using_pl = False
            for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
                if curr_id:
                    using_pl = True
                    p = particle_list.get_particle(curr_id)
                    ps.append(p)
            if using_pl:
                pls.append(particle_list)
        coords = [p.coord for p in ps]
        points_with_close_vertex, throw, closest_verts = find_closest_points(coords, self.vertices, search_length)
        for i, point_index in enumerate(points_with_close_vertex):
            p = ps[point_index]
            normal = self.normals[closest_verts[i]]
            rotation = z_align(p.coord, p.coord + normal).zero_translation().inverse()
            p.rotation = rotation
        for pl in pls:
            pl.update_places()


def get_grid(particle_pos, normal, resolution, method, base=None):
    """ Interpolates the surface from the given particles and normal. See start of class for explanation of normal
    First translates the system to a new base (x,y,z) -> (u,v,w). Uses scipy to do the interpolation.

    Parameters
    ----------
    particle_pos
    normal
    resolution
    method
    base

    Returns
    -------
    points: (n x n x 3) list of floats. The grid containing the points defining the surface.
    """
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
    """ Calculates the best fit normal to the given particles.

    Parameters
    ----------
    particles: particles to calculate normal from.
    particle_pos: if positions are already known, they can be supplied here.

    Returns
    -------
    normal: (3x1) list of floats. The normal vector.
    particle_pos: (nx3) list of floats. The coordinates of the particles. Only returned if particle
                   pos was not already provided.
    """
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
