# General imports
import numpy as np

# ChimeraX imports
from chimerax.geometry import z_align

# ArtiaX imports
from .GeoModel import GeoModel

class Sphere(GeoModel):
    """Sphere"""

    def __init__(self, name, session, particles, pos, r):
        super().__init__(name, session)
        self.change_transparency(100)

        self.particles = particles

        self.center = pos
        self.r = r

        self.update()
        print("Created sphere with center: {} and radius: {}".format(pos, r))

    def define_sphere(self):
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')
        b.sphere_command('.sphere {} {} {} {}'.format(self.center[0], self.center[1], self.center[2], self.r).split())

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    def update(self):
        vertices, normals, triangles, vertex_colors = self.define_sphere()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full(np.shape(vertex_colors), self.color)

    def orient_particles(self):
        # Reorient selected particles so that Z-axis points towards center of sphere
        for particle_list in self.session.ArtiaX.partlists.child_models():
            for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
                if curr_id:
                    curr_part = particle_list.get_particle(curr_id)
                    # Finds the rotation needed to align the vector (from the origin of the sphere to the particle) to
                    # the z-axis. The inverse is then taken to find the rotation needed to make the particle's z-axis
                    # perpendicular to the surface of the sphere.
                    rotation_to_z = z_align(self.center, curr_part.full_transform().translation())
                    rotation = rotation_to_z.zero_translation().inverse()
                    curr_part.rotation = rotation
            # Updated graphics
            particle_list.update_places()

    def change_radius(self, r):
        self.r = r
        self.update()

    def translate(self, pos):
        self.center = pos
        self.update()
