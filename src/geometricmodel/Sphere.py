# General imports
import numpy as np

# ChimeraX imports
from chimerax.geometry import z_align

# ArtiaX imports
from .GeoModel import GeoModel


class Sphere(GeoModel):
    """
    A Sphere model that is fitted to particles. Can be used to reorient particles.
    """

    def __init__(self, name, session, particle_pos, particles=None, center=None, r=None):
        """ Creates the Sphere. Calculates the center and radius if not supplied.

        Parameters
        ----------
        particle_pos: (n x 3) list containing all xyz positions of the particles.
        particles: n-long list containing all particles used to define the sphere.
        center: 3-long of floats
            contains the center coordinates for the sphere.
        r: float
            sphere radius.
        """
        super().__init__(name, session)
        # Spheres just kinda looks nicer when a bit transparent.
        self.change_transparency(100)

        self.particles = particles
        """n-long list containing all particles used to define the sphere."""
        self.particle_pos = particle_pos
        """(n x 3) list containing all xyz positions of the particles."""

        if center is None or r is None:
            center, r = lstsq_sphere(particle_pos)
        self.center = center
        """coordinates for center of sphere"""
        self.r = r
        """sphere radius"""

        self.update()
        session.logger.info("Created sphere with center: ({:.2f}, {:.2f}, {:.2f}) and radius: {:.2f}.".format(*center, r))

    def define_sphere(self):
        """ Gets the triangles, normals, and vertices needed to draw the sphere.

        Returns
        -------
        The vertices normals, triangles and colors used to draw the sphere.
        """
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')
        b.sphere_command('.sphere {} {} {} {}'.format(self.center[0], self.center[1], self.center[2], self.r).split())

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    def update(self):
        """Redraws the sphere."""
        vertices, normals, triangles, vertex_colors = self.define_sphere()
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full(np.shape(vertex_colors), self.color)

    def recalc_and_update(self):
        """Recalculates the center and radius of the sphere using the particles that define the sphere."""
        if self.particles is not None:
            for i, particle in enumerate(self.particles):
                self.particle_pos[i] = [particle.coord[0], particle.coord[1], particle.coord[2]]
        self.center, self.r = lstsq_sphere(self.particle_pos)
        self.update()

    def orient_particles(self):
        """Reorient selected particles so that Z-axis points towards center of sphere"""
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
        """Not used"""
        self.r = r
        self.update()

    def translate(self, pos):
        """Not used"""
        self.center = pos
        self.update()

    def write_file(self, file_name):
        """Save sphere to the specified location."""
        with open(file_name, 'wb') as file:
            np.savez(file, model_type="Sphere", particle_pos=self.particle_pos,
                     center=self.center, r=self.r)


def lstsq_sphere(pos):
    """
    Create a (overdetermined) system Ax = b, where A = [[2xi, 2yi, 2zi, 1], ...], x = [xi² + yi² + zi², ...],
    and b = [x, y, z, r²-x²-y²-z²], where xi,yi,zi are the positions of the particles, and x,y,z is the center of
    the fitted sphere with radius r.
    """

    import math
    A = np.append(2 * pos, np.ones((len(pos), 1)), axis=1)
    x = np.sum(pos ** 2, axis=1)
    b, residules, rank, singval = np.linalg.lstsq(A, x, rcond=None)
    r = math.sqrt(b[3] + b[0] ** 2 + b[1] ** 2 + b[2] ** 2)
    center = b[:3]

    return center, r
