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
