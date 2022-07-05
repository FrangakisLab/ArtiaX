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
from chimerax.geometry import z_align, rotation
from chimerax.bild.bild import _BildFile


class CurvedLine(GeoModel):
    """Line between two points"""

    def __init__(self, name, session, particles, points, degree, smooth, resolution):
        super().__init__(name, session)

        self.points = points  # points[0] contains all the x values, points[1] all y values etc
        self.particles = particles

        self.fitting_options = True
        self.degree = degree
        self.smooth = smooth
        self.smooth_edit_range = [math.floor(len(particles) - math.sqrt(2 * len(particles))),
                                  math.ceil(len(particles) + math.sqrt(2 * len(particles)))]
        self.resolution = resolution
        self.resolution_edit_range = (50, 500)

        self.has_particles = False
        self.spacing_edit_range = (1, 100)
        self.spacing = (self.spacing_edit_range[1] + self.spacing_edit_range[0]) / 2
        self.spheres = Model("spheres", session)
        self.add([self.spheres])
        self.spheres_position = np.zeros((0, 3))
        self.spheres_rotation = np.array([])

        self.update()

    def update(self):
        vertices, normals, triangles, vertex_colors = self.define_curved_line()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full(np.shape(vertex_colors), self.color)

    def define_curved_line(self):
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')

        for i in range(0, len(self.points[0]) - 1):
            b.cylinder_command(".cylinder {} {} {} {} {} {} 1".format(self.points[0][i], self.points[1][i],
                                                                      self.points[2][i], self.points[0][i + 1],
                                                                      self.points[1][i + 1],
                                                                      self.points[2][i + 1]).split())

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

    def create_spheres(self):
        self.has_particles = True
        self.triggers.activate_trigger(GEOMODEL_CHANGED, self)
        self.spheres_position = np.zeros((0, 3))
        self.spheres_rotation = np.array([])

        b = _BildFile(self.session, 'dummy')
        d = AtomicShapeDrawing('shapes')

        # Set first manually to avoid special cases in loop:
        first_pos = np.array([self.points[0][0], self.points[1][0], self.points[2][0]])
        second_pos = np.array([self.points[0][1], self.points[1][1], self.points[2][1]])
        self.spheres_position = np.append(self.spheres_position, [first_pos], axis=0)
        rotation_to_z = z_align(first_pos, second_pos)
        rotation_along_line = rotation_to_z.zero_translation().inverse()
        self.spheres_rotation = np.append(self.spheres_rotation, rotation_along_line)
        b.sphere_command('.sphere {} {} {} {}'.format(*first_pos, 4).split())
        # b.cylinder_command()
        d.add_shapes(b.shapes)

        total_dist = 0
        distance_since_last = 0
        for i in range(1, len(self.points[0])):
            curr_pos = np.array([self.points[0][i], self.points[1][i], self.points[2][i]])
            last_pos = np.array([self.points[0][i - 1], self.points[1][i - 1], self.points[2][i - 1]])
            step_dist = np.linalg.norm(curr_pos - last_pos)
            total_dist += step_dist
            distance_since_last += step_dist
            if distance_since_last >= self.spacing:
                distance_since_last = 0
                self.spheres_position = np.append(self.spheres_position, [curr_pos], axis=0)

                rotation_to_z = z_align(last_pos, curr_pos)
                rotation_along_line = rotation_to_z.zero_translation().inverse()
                rotation_around_z = rotation(rotation_along_line.z_axis(), total_dist)
                rot = rotation_around_z * rotation_along_line
                self.spheres_rotation = np.append(self.spheres_rotation, rot)

                b.sphere_command('.sphere {} {} {} {}'.format(*curr_pos, 4).split())
                #direction = curr_pos - last_pos / step_dist
                #axis_end_point = curr_pos + direction * 1
                #b.arrow_command(".arrow {} {} {} {} {} {} 1".format(*curr_pos, *axis_end_point).split())
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

    def change_degree(self, degree):
        if self.degree == degree:
            return
        else:
            self.degree = degree
            self.points = get_points(self.session, self.particles, self.smooth, self.degree, self.resolution)
            self.update()

    def change_resolution(self, res):
        if self.resolution == res:
            return
        else:
            self.resolution = res
            self.points = get_points(self.session, self.particles, self.smooth, self.degree, self.resolution)
            self.update()

    def change_smoothing(self, s):
        if self.smooth == s:
            return
        else:
            self.smooth = s
            self.points = get_points(self.session, self.particles, self.smooth, self.degree, self.resolution)
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

    return points
