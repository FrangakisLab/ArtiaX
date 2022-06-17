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

#Triggers
GEOMODEL_CHANGED = 'geomodel changed'  # Data is the modified geometric model.

class GeoModel(Model):
    """Handles geometric models"""

    def __init__(self, name, session, pos, r):
        super().__init__(name, session)

        vertices, normals, triangles, vertex_colors = self.define_sphere(pos, r)
        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = vertex_colors

        # Change trigger for UI
        self.triggers.add_trigger(GEOMODEL_CHANGED)

    def define_sphere(self, pos, r):
        from chimerax.bild.bild import _BildFile
        b = _BildFile(self.session, 'dummy')
        b.transparency_command('.transparency 0.7'.split())
        b.color_command('.color 1 0 0'.split())
        b.sphere_command('.sphere {} {} {} {}'.format(pos[0], pos[1], pos[2], r).split())

        from chimerax.atomic import AtomicShapeDrawing
        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

def fit_sphere(session):
    """Fits a sphere to the currently selected particles"""
    artiax = session.ArtiaX

    # Find selected particles
    particle_pos = np.zeros((0, 3))  # each row is one currently selected particle, with columns being x,y,z
    for particlelist in artiax.partlists.child_models():
        for curr_id in particlelist.particle_ids[particlelist.selected_particles]:
            if curr_id:
                x_pos = particlelist.get_particle(curr_id)['pos_x'] \
                        + particlelist.get_particle(curr_id)['shift_x']
                y_pos = particlelist.get_particle(curr_id)['pos_y'] \
                        + particlelist.get_particle(curr_id)['shift_y']
                z_pos = particlelist.get_particle(curr_id)['pos_z'] \
                        + particlelist.get_particle(curr_id)['shift_z']
                particle_pos = np.append(particle_pos, [[x_pos, y_pos, z_pos]], axis=0)

    if len(particle_pos) < 4:
        session.logger.warning("At least four points are needed to fit a sphere")
        return

    # Create a (overdetermined) system Ax = b, where A = [[2xi, 2yi, 2zi, 1], ...], x = [xi² + yi² + zi², ...],
    # and b = [x, y, z, r²-x²-y²-z²], where xi,yi,zi are the positions of the particles, and x,y,z is the center of
    # the fitted sphere with radius r.

    A = np.append(2 * particle_pos, np.ones((len(particle_pos), 1)), axis=1)
    x = np.sum(particle_pos ** 2, axis=1)
    b, residules, rank, singval = np.linalg.lstsq(A, x)
    r = math.sqrt(b[3] + b[0] ** 2 + b[1] ** 2 + b[2] ** 2)

    # Reorient selected particles so that Z-axis points towards center of sphere
    for particlelist in session.ArtiaX.partlists.child_models():
        for curr_id in particlelist.particle_ids[particlelist.selected_particles]:
            if curr_id:
                particlelist.get_particle(curr_id).

    # TODO remove
    print(b[0], b[1], b[2], r)

    geomodel = GeoModel("sphere", session, b[:3], r)
    artiax.add_geomodel(geomodel)

