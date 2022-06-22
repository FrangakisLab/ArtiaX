# General imports
import numpy as np
import math

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

class Line(GeoModel):
    """Line between two points"""

    def __init__(self, name, session, start, end):
        super().__init__(name, session)

        self.start = start
        self.end = end

        self.has_particles = False
        self.spacing_edit_range = (1, 100)
        self.spacing = (self.spacing_edit_range[1] + self.spacing_edit_range[0])/2
        self.spheres = Model("spheres", session)
        self.add([self.spheres])

        self.update()
        print("Created line starting at: {} and edning at: {}".format(start, end))

    def define_line(self):
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')
        b.transparency_command('.transparency {}'.format(self._color[3] / 255).split())
        bild_color = np.multiply(self.color, 1 / 255)
        b.color_command('.color {} {} {}'.format(*bild_color).split())
        b.cylinder_command(".vector {} {} {} {} {} {} 1".format(*self.start, *self.end).split())

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    def update(self):
        vertices, normals, triangles, vertex_colors = self.define_line()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = vertex_colors

    def create_spheres(self):
        self.has_particles = True
        self.triggers.activate_trigger(GEOMODEL_CHANGED, self)

        rotation, direction, nr_particles = self._calculate_particle_pos()

        if nr_particles == 0:
            print("too large spacing")
            return

        b = _BildFile(self.session, 'dummy')
        b.transparency_command('.transparency 0'.split())
        bild_color = np.multiply(self.color, 1 / 255)
        b.color_command('.color {} {} {}'.format(*bild_color).split())
        d = AtomicShapeDrawing('shapes')
        for i in range(1, int(nr_particles) + 1):
            pos = self.start + direction * self.spacing * i
            b.sphere_command('.sphere {} {} {} {}'.format(*pos, 4).split())
            d.add_shapes(b.shapes)
        self.spheres.set_geometry(d.vertices, d.normals, d.triangles)
        self.spheres.vertex_colors = d.vertex_colors

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

    def curve_line(self, third_point, step_length):
        # Project points onto their plane
        ts = self.start - third_point
        u = ts / np.linalg.norm(ts)
        w = np.cross(ts, self.end - third_point)
        w = w / np.linalg.norm(w)
        v = np.cross(w, u)

        p1 = np.array([np.dot(self.start, u), np.dot(self.start, v)])
        p2 = np.array([np.dot(self.end, u), np.dot(self.end, v)])
        p3 = np.array([np.dot(third_point, u), np.dot(third_point, v)])

        # Find center and radius by solving Ac = b with A = [[x1,y1,1], [x2,y2,1], [x3,y3,1]] and
        # b = [x1² + y1², x2² + y2², x3² + y3²]. This gives c = [2x0,2y0,r² - x0² - y0²]
        A = np.array([np.append(p1, 1), np.append(p2, 1), np.append(p3, 1)])
        b = np.array([np.sum(np.multiply(p1,p1)), np.sum(np.multiply(p2,p2)), np.sum(np.multiply(p3,p3))])
        c = np.linalg.solve(A, b)
        center = [c[0] / 2, c[1] / 2]
        #radius = c[2] + np.sum(np.multiply(center))

        # Translate center back to euclidean
        center = center[0]*u + center[1]*v


        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')
        b.transparency_command('.transparency {}'.format(self._color[3] / 255).split())
        bild_color = np.multiply(self.color, 1 / 255)
        b.color_command('.color {} {} {}'.format(*bild_color).split())
        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')

        curr_point = self.start
        reached_end = False
        print(self.start)
        print(self.end)
        while not reached_end:
            along_circle_vector = np.cross(curr_point - center, w)
            along_circle_vector = along_circle_vector / np.linalg.norm(along_circle_vector)
            next_point = self.start + along_circle_vector * step_length
            print(curr_point)
            print(next_point)
            if np.linalg.norm(next_point - self.end) < step_length:
                next_point = self.end
                reached_end = True

            b.cylinder_command(".vector {} {} {} {} {} {} 1".format(*curr_point, *next_point).split())
            curr_point = next_point

        d.add_shapes(b.shapes)
        self.set_geometry(d.vertices, d.normals, d.triangles)
        self.vertex_colors = d.vertex_colors

