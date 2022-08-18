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


class CurvedLine(PopulatedModel):
    """
    Fits a curved line through the given particles. Can be used to create particles along the line.
    Calculates the points and tangents if not provided.
    """

    def __init__(self, name, session, particle_pos, degree, smooth, resolution, particles=None, points=None,
                 der_points=None):
        super().__init__(name, session)

        self.particles = particles
        """n-long list containing all particles used to define the sphere."""
        self.particle_pos = particle_pos
        """(n x 3) list containing all xyz positions of the particles."""

        if points is None or der_points is None:
            self.points, self.der_points = get_points(particle_pos, smooth, degree, resolution)
        else:
            self.points = points
            self.der_points = der_points
        """(3 x n) list with all the points/derivatives used to define the line. points[0] contains all the x values, 
        points[1] all y values etc"""

        self.degree = degree
        """Polynomial degree used to fit line."""
        self.smooth = smooth
        """Decides how much to smooth the polynomial. smooth = 0 forces the line to go through all particles."""
        self.smooth_edit_range = [math.floor(len(particle_pos) - math.sqrt(2 * len(particle_pos))),
                                  math.ceil(len(particle_pos) + math.sqrt(2 * len(particle_pos)))]
        self.resolution = resolution
        """How many points to define the line by."""
        self.resolution_edit_range = (50, 500)

        self.fitting_options = True
        self.display_options = True
        self.radius = 1
        """Line (which is drawn as a cylinder) radius"""
        self.radius_edit_range = (0, 2)

        self.spacing_edit_range = (1, 100)
        self.spacing = (self.spacing_edit_range[1] + self.spacing_edit_range[0]) / 2
        """Spacing between created particles."""
        self.rotate = False
        """Whether to rotate particles around the line."""
        self.rotation = 0
        """Degrees to rotate per Angstrom"""
        self.rotation_edit_range = (0, 1)
        self.start_rotation = 0
        """Rotation of first particle."""

        self.update()
        session.logger.info("Created a Curved line through {} particles.".format(len(particle_pos)))

    def update(self):
        """Redraws the line."""
        vertices, normals, triangles, vertex_colors = self.define_curved_line()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full(np.shape(vertex_colors), self.color)

    def recalc_and_update(self):
        """Recalculates the points and derivatives that define the line before redrawing the line."""
        if self.particles is not None:
            for i, particle in enumerate(self.particles):
                self.particle_pos[i] = [particle.coord[0], particle.coord[1], particle.coord[2]]
        self.points, self.der_points = get_points(self.particle_pos, self.smooth, self.degree, self.resolution)
        self.update()

    def define_curved_line(self):
        b = _BildFile(self.session, 'dummy')

        for i in range(0, len(self.points[0]) - 1):
            b.cylinder_command(".cylinder {} {} {} {} {} {} {}".format(self.points[0][i], self.points[1][i],
                                                                       self.points[2][i], self.points[0][i + 1],
                                                                       self.points[1][i + 1],
                                                                       self.points[2][i + 1], self.radius).split())

        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    def change_radius(self, r):
        if self.radius != r:
            self.radius = r
            self.update()

    def create_spheres(self):
        """Creates sphere markers with axes to show how particles would be created."""
        self.has_particles = True
        self.triggers.activate_trigger(GEOMODEL_CHANGED, self)
        # Remove old spheres if any exist
        if len(self.indices):
            self.collection_model.delete_places(self.indices)
        self.spheres_places = []

        # Set first manually to avoid special cases in loop:
        first_pos = np.array([self.points[0][0], self.points[1][0], self.points[2][0]])
        der = [self.der_points[0][0], self.der_points[1][0], self.der_points[2][0]]
        tangent = der / np.linalg.norm(der)
        rotation_to_z = z_align(first_pos, first_pos + tangent)
        rotation_along_line = rotation_to_z.zero_translation().inverse()
        rot = rotation_along_line
        if self.rotate:
            rotation_around_z = rotation(rotation_along_line.z_axis(), self.start_rotation)
            rot = rotation_around_z * rotation_along_line

        place = translation(first_pos) * rot
        self.spheres_places = np.append(self.spheres_places, place)

        n = rot.transform_vector((1, 0, 0))
        n = n / np.linalg.norm(n)
        normals = np.array([n])

        total_dist = 0
        distance_since_last = 0
        for i in range(1, len(self.points[0])):
            curr_pos = np.array([self.points[0][i], self.points[1][i], self.points[2][i]])
            last_pos = np.array([self.points[0][i - 1], self.points[1][i - 1], self.points[2][i - 1]])
            step_dist = np.linalg.norm(curr_pos - last_pos)
            der = [self.der_points[0][i], self.der_points[1][i], self.der_points[2][i]]
            tangent = der / np.linalg.norm(der)
            total_dist += step_dist
            distance_since_last += step_dist

            # calculate normal using projection normal method found in "Normal orientation methods for 3D offset
            # curves, sweep surfaces and skinning" by Pekka  Siltanen  and Charles  Woodward
            n = normals[-1] - (np.dot(normals[-1], tangent)) * tangent
            n = n / np.linalg.norm(n)
            normals = np.append(normals, [n], axis=0)

            # create marker
            if distance_since_last >= self.spacing:
                distance_since_last = 0

                rotation_along_line = z_align(curr_pos, curr_pos + tangent).zero_translation().inverse()
                x_axes = rotation_along_line.transform_vector((1, 0, 0))
                cross = np.cross(n, x_axes)
                theta = math.acos(np.dot(n, x_axes)) * 180 / math.pi
                if np.linalg.norm(cross + tangent) > 1:
                    theta = -theta
                helix_rotate = 0
                if self.rotate:
                    helix_rotate = total_dist * self.rotation
                rotation_around_z = rotation(rotation_along_line.z_axis(), theta + helix_rotate)

                rot = rotation_around_z * rotation_along_line

                place = translation(curr_pos) * rot
                self.spheres_places = np.append(self.spheres_places, place)

        self.indices = [str(i) for i in range(0, len(self.spheres_places))]
        self.collection_model.add_places(self.indices, self.spheres_places)
        self.collection_model.color = self.color

    def change_rotation(self, rot):
        if self.rotation == rot:
            return
        else:
            self.rotation = rot
            self.create_spheres()

    def change_start_rotation(self, rot):
        if self.start_rotation == rot:
            return
        else:
            self.start_rotation = rot
            self.create_spheres()

    def change_degree(self, degree):
        if self.degree == degree:
            return
        else:
            self.degree = degree
            self.recalc_and_update()

    def change_resolution(self, res):
        if self.resolution == res:
            return
        else:
            self.resolution = res
            self.recalc_and_update()

    def change_smoothing(self, s):
        if self.smooth == s:
            return
        else:
            self.smooth = s
            self.recalc_and_update()

    def write_file(self, file_name):
        with open(file_name, 'wb') as file:
            np.savez(file, model_type="CurvedLine", particle_pos=self.particle_pos, degree=self.degree,
                     smooth=self.smooth, resolution=self.resolution, points=self.points, der_points=self.der_points)


def get_points(pos, smooth, degree, resolution):
    """Uses scipy to interpolate a line through the points

    Parameters
    ----------
    pos: (n x 3) list of floats with n coordinates
    smooth: how much to smoothen the line.
    degree: which degree polynomial to fit the line with.
    resolution: how many points to return.

    Returns
    -------
    points: (m x 3) list of floats with m coordinates. n=resolution
    der_points: same as points but the derivatives.
    """
    # Find particles
    x = pos[:,0]
    y = pos[:,1]
    z = pos[:,2]

    # s=0 means it will go through all points, s!=0 means smoother, good value between m+-sqrt(2m) (m=no. points)
    # degree can be 1,3, or 5
    tck, u = interpolate.splprep([x, y, z], s=smooth, k=degree)
    un = np.arange(0, 1 + 1 / resolution, 1 / resolution)
    points = interpolate.splev(un, tck)
    der_points = interpolate.splev(un, tck, der=1)

    return points, der_points
