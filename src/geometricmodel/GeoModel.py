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

# Triggers
GEOMODEL_CHANGED = 'geomodel changed'  # Data is the modified geometric model.


class GeoModel(Model):
    """Handles geometric models"""

    def __init__(self, name, session):
        super().__init__(name, session)

        self._color = self._get_unused_color()
        self.change_transparency(255)

        # Change trigger for UI
        self.triggers.add_trigger(GEOMODEL_CHANGED)

    def _get_unused_color(self):
        artia = self.session.ArtiaX

        std_col = np.array(artia.standard_colors)
        for gm in artia.geomodels.iter():
            gmcol = np.array([np.append(gm.color[:3], 255)])
            mask = np.logical_not(np.all(gmcol == std_col, axis=1))
            std_col = std_col[mask, :]

        # Change both -1 to 0 to go from the start of the list and not the end
        if std_col.shape[0] > 0:
            col = std_col[-1, :]
        else:
            col = artia.standard_colors[-1]
        return col

    def change_transparency(self, t):
        self._color[3] = t

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        if len(color) == 3:  # transparency was not given
            color = np.append(color, self._color[3])
        self._color = color
        self.vertex_colors = np.full(np.shape(self.vertex_colors), color)


def get_curr_selected_particles_pos(session, XYZ=False):
    artiax = session.ArtiaX

    if not XYZ:
        # Find selected particles
        particle_pos = np.zeros((0, 3))  # each row is one currently selected particle, with columns being x,y,z
        for particle_list in artiax.partlists.child_models():
            for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
                if curr_id:
                    curr_part = particle_list.get_particle(curr_id)
                    x_pos = curr_part.coord[0]
                    y_pos = curr_part.coord[1]
                    z_pos = curr_part.coord[2]
                    particle_pos = np.append(particle_pos, [[x_pos, y_pos, z_pos]], axis=0)

        return particle_pos
    else:
        # Find selected particles
        x, y, z = np.zeros(0), np.zeros(0), np.zeros(0)
        for particle_list in artiax.partlists.child_models():
            for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
                if curr_id:
                    curr_part = particle_list.get_particle(curr_id)
                    x = np.append(x, curr_part.coord[0])
                    y = np.append(y, curr_part.coord[1])
                    z = np.append(z, curr_part.coord[2])

        return x, y, z


def fit_sphere(session):
    """Fits a sphere to the currently selected particles"""
    artiax = session.ArtiaX

    particle_pos = get_curr_selected_particles_pos(session, XYZ=False)

    if len(particle_pos) < 4:
        session.logger.warning("At least four points are needed to fit a sphere")
        return

    # Create a (overdetermined) system Ax = b, where A = [[2xi, 2yi, 2zi, 1], ...], x = [xi² + yi² + zi², ...],
    # and b = [x, y, z, r²-x²-y²-z²], where xi,yi,zi are the positions of the particles, and x,y,z is the center of
    # the fitted sphere with radius r.

    A = np.append(2 * particle_pos, np.ones((len(particle_pos), 1)), axis=1)
    x = np.sum(particle_pos ** 2, axis=1)
    b, residules, rank, singval = np.linalg.lstsq(A, x, rcond=None)
    r = math.sqrt(b[3] + b[0] ** 2 + b[1] ** 2 + b[2] ** 2)

    # Reorient selected particles so that Z-axis points towards center of sphere
    from chimerax.geometry import z_align
    for particle_list in session.ArtiaX.partlists.child_models():
        for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
            if curr_id:
                curr_part = particle_list.get_particle(curr_id)
                # Finds the rotation needed to align the vector (from the origin of the sphere to the particle) to
                # the z-axis. The inverse is then taken to find the rotation needed to make the particle's z-axis
                # perpendicular to the surface of the sphere.
                rotation_to_z = z_align(b[:3], curr_part.full_transform().translation())
                rotation = rotation_to_z.zero_translation().inverse()
                curr_part.rotation = rotation
        # Updated graphics
        particle_list.update_places()

    from .Sphere import Sphere
    geomodel = Sphere("sphere", session, b[:3], r)
    artiax.add_geomodel(geomodel)


def fit_line(session):
    """Creates a line between two particles"""
    artiax = session.ArtiaX

    particle_pos = get_curr_selected_particles_pos(session, XYZ=False)

    if len(particle_pos) != 2:
        session.logger.warning("Only select a start and end point")
        return

    start = particle_pos[0]
    end = particle_pos[1]

    # Reorient selected particles so that Z-axis along the line
    from chimerax.geometry import z_align
    rotation_to_z = z_align(start, end)
    rotation = rotation_to_z.zero_translation().inverse()
    for particle_list in session.ArtiaX.partlists.child_models():
        for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
            if curr_id:
                curr_part = particle_list.get_particle(curr_id)
                curr_part.rotation = rotation
        # Updated graphics
        particle_list.update_places()

    from .Line import Line
    geomodel = Line("line", session, start, end)
    artiax.add_geomodel(geomodel)


def fit_curved_line(session):
    artiax = session.ArtiaX

    x, y, z = get_curr_selected_particles_pos(session, XYZ=True)

    if len(x) < 2:
        session.logger.warning("Please select multiple points")
        return

    smooth = 0  # s=0 means it will go through all points, s!=0 means smoother, good value between m+-sqrt(2m) (m=no. points)
    degree = 3  # can be 0,3, or 5
    tck, u = interpolate.splprep([x, y, z], s=smooth, k=degree)
    resolution = 1000
    un = np.arange(0, 1 + 1 / resolution, 1 / resolution)
    out = interpolate.splev(un, tck)

    # TODO rotate particles along line. Then add: options for smoothness and dimensions, add particles along line,
    #  add particles in specific order.

    from .CurvedLine import CurvedLine
    geomodel = CurvedLine("curved line", session, out)
    artiax.add_geomodel(geomodel)
