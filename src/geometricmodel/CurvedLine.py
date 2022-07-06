# General imports
import numpy as np
import math
from scipy import interpolate

# ChimeraX imports
from chimerax.core.commands import run
from chimerax.core.errors import UserError
from chimerax.core.models import Model
from chimerax.map import Volume
from chimerax.atomic import Atom
from chimerax.graphics import Drawing
from .GeoModel import GeoModel, GEOMODEL_CHANGED
from chimerax.atomic import AtomicShapeDrawing
from chimerax.geometry import z_align, rotation, Place
from chimerax.bild.bild import _BildFile


class CurvedLine(GeoModel):
    """Line between two points"""

    def __init__(self, name, session, particles, points, der_points, degree, smooth, resolution):
        super().__init__(name, session)

        self.points = points  # points[0] contains all the x values, points[1] all y values etc
        self.der_points = der_points
        self.particles = particles

        self.fitting_options = True
        self.degree = degree
        self.smooth = smooth
        self.smooth_edit_range = [math.floor(len(particles) - math.sqrt(2 * len(particles))),
                                  math.ceil(len(particles) + math.sqrt(2 * len(particles)))]
        self.resolution = resolution
        self.resolution_edit_range = (50, 500)

        self.display_options = True
        self.radius = 1
        self.radius_edit_range = (0, 2)
        self.has_particles = False
        self.marker_axis_display_options = True
        self.marker_size = 4
        self.marker_size_edit_range = (1, 7)
        self.axes_size = 15
        self.axes_size_edit_range = (10, 20)
        self.spacing_edit_range = (1, 100)
        self.spacing = (self.spacing_edit_range[1] + self.spacing_edit_range[0]) / 2
        self.spheres = Model("spheres", session)
        self.add([self.spheres])
        self.spheres_position = np.zeros((0, 3))
        self.spheres_rotation = np.array([])
        self.rotate = False
        self.rotation = 0
        self.rotation_edit_range = (0, 1)
        self.start_rotation = 0

        self.update()

    def update(self):
        vertices, normals, triangles, vertex_colors = self.define_curved_line()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full(np.shape(vertex_colors), self.color)

    def define_curved_line(self):
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')

        for i in range(0, len(self.points[0]) - 1):
            b.cylinder_command(".cylinder {} {} {} {} {} {} {}".format(self.points[0][i], self.points[1][i],
                                                                       self.points[2][i], self.points[0][i + 1],
                                                                       self.points[1][i + 1],
                                                                       self.points[2][i + 1], self.radius).split())

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    @GeoModel.color.setter
    def color(self, color):
        if len(color) == 3:  # transparency was not given
            color = np.append(color, self._color[3])
        self._color = color
        self.vertex_colors = np.full(np.shape(self.vertex_colors), color)
        if self.spheres.vertex_colors is not None:
            self.spheres.vertex_colors = np.full(np.shape(self.spheres.vertex_colors), color)

    def change_radius(self, r):
        if self.radius != r:
            self.radius = r
            self.update()

    def change_marker_size(self, r):
        if self.marker_size != r:
            self.marker_size = r
            self.create_spheres()

    def change_axes_size(self, s):
        if self.axes_size != s:
            self.axes_size = s
            self.create_spheres()

    def create_spheres(self):
        self.has_particles = True
        self.triggers.activate_trigger(GEOMODEL_CHANGED, self)
        self.spheres_position = np.zeros((0, 3))
        self.spheres_rotation = np.array([])

        b = _BildFile(self.session, 'dummy')
        d = AtomicShapeDrawing('shapes')

        # Set first manually to avoid special cases in loop:
        first_pos = np.array([self.points[0][0], self.points[1][0], self.points[2][0]])
        self.spheres_position = np.append(self.spheres_position, [first_pos], axis=0)
        der = [self.der_points[0][0], self.der_points[1][0], self.der_points[2][0]]
        tangent = der / np.linalg.norm(der)
        rotation_to_z = z_align(first_pos, first_pos + tangent)
        rotation_along_line = rotation_to_z.zero_translation().inverse()
        rot = rotation_along_line
        if self.rotate:
            rotation_around_z = rotation(rotation_along_line.z_axis(), self.start_rotation)
            rot = rotation_around_z * rotation_along_line
        self.spheres_rotation = np.append(self.spheres_rotation, rot)
        n = rot.transform_vector((1, 0, 0))
        n = n / np.linalg.norm(n)
        normals = np.array([n])

        b.sphere_command('.sphere {} {} {} {}'.format(*first_pos, self.marker_size).split())
        axis_end_point = first_pos + tangent * self.axes_size
        b.arrow_command(".arrow {} {} {} {} {} {} {} {}".format(*first_pos, *axis_end_point, self.axes_size / 15,
                                                                self.axes_size / 15 * 4).split())
        normal_end_point = first_pos + n * self.axes_size
        b.arrow_command(".arrow {} {} {} {} {} {} {} {}".format(*first_pos, *normal_end_point, self.axes_size / 15,
                                                                self.axes_size / 15 * 4).split())
        d.add_shapes(b.shapes)

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

            # create marker
            if distance_since_last >= self.spacing:
                distance_since_last = 0
                self.spheres_position = np.append(self.spheres_position, [curr_pos], axis=0)

                # calculate normal using projection normal method found in "Normal orientation methods for 3D offset
                # curves, sweep surfaces and skinning" by Pekka  Siltanen  and Charles  Woodward
                n = normals[-1] - (np.dot(normals[-1], tangent)) * tangent
                n = n / np.linalg.norm(n)
                normals = np.append(normals, [n], axis=0)

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

                self.spheres_rotation = np.append(self.spheres_rotation, rot)

                b.sphere_command('.sphere {} {} {} {}'.format(*curr_pos, self.marker_size).split())
                axis_end_point = curr_pos + tangent * self.axes_size
                b.arrow_command(".arrow {} {} {} {} {} {} {} {}".format(*curr_pos, *axis_end_point, self.axes_size / 15,
                                                                        self.axes_size / 15 * 4).split())
                normal_end_point = curr_pos + rot.transform_vector((1, 0, 0)) * self.axes_size
                b.arrow_command(
                    ".arrow {} {} {} {} {} {} {} {}".format(*curr_pos, *normal_end_point, self.axes_size / 15,
                                                            self.axes_size / 15 * 4).split())
                d.add_shapes(b.shapes)

        self.spheres.set_geometry(d.vertices, d.normals, d.triangles)
        if d.vertex_colors is not None:
            self.spheres.vertex_colors = np.full(np.shape(d.vertex_colors), self.color)

    def remove_spheres(self):
        self.spheres.delete()
        self.spheres = Model("spheres", self.session)
        self.add([self.spheres])
        self.has_particles = False
        self.spheres_position = np.array([])
        self.triggers.activate_trigger(GEOMODEL_CHANGED, self)

    def create_particle_list(self):
        artia = self.session.ArtiaX
        artia.create_partlist(name=self.name + " particles")
        partlist = artia.partlists.child_models()[-1]
        artia.ui.ow._show_tab("geomodel")
        self.create_particles(partlist)

    def create_particles(self, partlist):
        for i in range(0, len(self.spheres_position)):
            partlist.new_particle(self.spheres_position[i], [0, 0, 0], self.spheres_rotation[i])

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
            self.points, self.der_points = get_points(self.session, self.particles, self.smooth, self.degree,
                                                      self.resolution)
            self.update()

    def change_resolution(self, res):
        if self.resolution == res:
            return
        else:
            self.resolution = res
            self.points, self.der_points = get_points(self.session, self.particles, self.smooth, self.degree,
                                                      self.resolution)
            self.update()

    def change_smoothing(self, s):
        if self.smooth == s:
            return
        else:
            self.smooth = s
            self.points, self.der_points = get_points(self.session, self.particles, self.smooth, self.degree,
                                                      self.resolution)
            self.update()


def get_points(session, particles, smooth, degree, resolution):
    # Find particles
    x, y, z = np.zeros(0), np.zeros(0), np.zeros(0)
    for particle in particles:
        x = np.append(x, particle.coord[0])
        y = np.append(y, particle.coord[1])
        z = np.append(z, particle.coord[2])

    # s=0 means it will go through all points, s!=0 means smoother, good value between m+-sqrt(2m) (m=no. points)
    # degree can be 1,3, or 5
    tck, u = interpolate.splprep([x, y, z], s=smooth, k=degree)
    un = np.arange(0, 1 + 1 / resolution, 1 / resolution)
    points = interpolate.splev(un, tck)
    der_points = interpolate.splev(un, tck, der=1)

    return points, der_points
