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
from chimerax.geometry import z_align
from chimerax.bild.bild import _BildFile


class CurvedLine(GeoModel):
    """Line between two points"""

    def __init__(self, name, session, points, particles, degree, smooth, resolution):
        super().__init__(name, session)

        self.points = points  # points[0] contains all the x values, points[1] all y values etc
        self.particles = particles

        self.degree = degree
        self.smooth = smooth
        self.resolution = resolution
        self.resolution_edit_range = (50, 500)

        self.has_particles = False
        self.spacing_edit_range = (1, 100)
        self.spacing = (self.spacing_edit_range[1] + self.spacing_edit_range[0]) / 2
        self.spheres = Model("spheres", session)
        self.add([self.spheres])

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

        rotation, direction, nr_particles = self._calculate_particle_pos()

        if nr_particles == 0:
            print("too large spacing")
            return

        b = _BildFile(self.session, 'dummy')
        d = AtomicShapeDrawing('shapes')
        for i in range(1, int(nr_particles) + 1):
            pos = self.start + direction * self.spacing * i
            b.sphere_command('.sphere {} {} {} {}'.format(*pos, 4).split())
            d.add_shapes(b.shapes)
        self.spheres.set_geometry(d.vertices, d.normals, d.triangles)
        if d.vertex_colors is not None:
            self.spheres.vertex_colors = np.full(np.shape(d.vertex_colors), self.color)

    def remove_spheres(self):
        self.spheres.delete()
        self.spheres = Model("spheres", self.session)
        self.add([self.spheres])
        self.has_particles = False
        self.triggers.activate_trigger(GEOMODEL_CHANGED, self)

    def create_particle_list(self):
        artia = self.session.ArtiaX
        artia.create_partlist(name=self.name + " particles")
        partlist = artia.partlists.child_models()[-1]
        artia.ui.ow._show_tab("geomodel")
        self.create_particles(partlist)

    def create_particles(self, partlist):
        rotation, direction, nr_particles = self._calculate_particle_pos()

        if nr_particles == 0:
            print("too large spacing")
            return
        for i in range(1, int(nr_particles) + 1):
            pos = self.start + direction * self.spacing * i
            partlist.new_particle(pos, [0, 0, 0], rotation)

    def _calculate_particle_pos(self):
        rotation_to_z = z_align(self.start, self.end)
        rotation = rotation_to_z.zero_translation().inverse()

        direction = self.end - self.start
        line_length = np.linalg.norm(self.end - self.start)
        direction = direction / np.linalg.norm(direction)
        nr_particles = line_length / self.spacing
        return rotation, direction, nr_particles

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
