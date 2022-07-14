# General imports
import numpy as np
from scipy import interpolate
import math

# ChimeraX imports
from chimerax.core.commands import run
from chimerax.core.errors import UserError
from chimerax.core.models import Model
from chimerax.map import Volume
from chimerax.atomic import Atom
from chimerax.graphics import Drawing
from chimerax.geometry import z_align

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


def selected_geomodels(session, model=None):
    s_geomodels = np.array([])
    if model is None:  # Return all selected geomodels
        for geomodel in session.ArtiaX.geomodels.child_models():
            if geomodel.selected:
                s_geomodels = np.append(s_geomodels, geomodel)
    else:
        for geomodel in session.ArtiaX.geomodels.child_models():
            if geomodel.selected and type(geomodel).__name__ == model:
                s_geomodels = np.append(s_geomodels, geomodel)

    return s_geomodels


def get_curr_selected_particles_pos(session):
    artiax = session.ArtiaX

    # Find selected particles
    particles = np.array([])
    particle_pos = np.zeros((0, 3))  # each row is one currently selected particle, with columns being x,y,z
    for particle_list in artiax.partlists.child_models():
        for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
            if curr_id:
                curr_part = particle_list.get_particle(curr_id)
                particles = np.append(particles, curr_part)
                x_pos = curr_part.coord[0]
                y_pos = curr_part.coord[1]
                z_pos = curr_part.coord[2]
                particle_pos = np.append(particle_pos, [[x_pos, y_pos, z_pos]], axis=0)

    return particle_pos, particles


def fit_sphere(session):
    """Fits a sphere to the currently selected particles"""
    artiax = session.ArtiaX

    particle_pos, particles = get_curr_selected_particles_pos(session)

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

    from .Sphere import Sphere
    geomodel = Sphere("sphere", session, particles, b[:3], r)
    artiax.add_geomodel(geomodel)


def fit_line(session):
    # NOT USED
    """Creates a line between two particles"""
    artiax = session.ArtiaX

    particle_pos, particles = get_curr_selected_particles_pos(session)

    if len(particle_pos) != 2:
        session.logger.warning("Only select a start and end point")
        return

    start = particle_pos[0]
    end = particle_pos[1]

    # Reorient selected particles so that Z-axis along the line
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
    geomodel = Line("line", session, particles, start, end)
    artiax.add_geomodel(geomodel)


def fit_curved_line(session):
    # TODO: set particles along line, rotate particles with spacing, merge with line, select particles, order from lines
    artiax = session.ArtiaX

    particles = np.array([])
    for particle_list in session.ArtiaX.partlists.child_models():
        for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
            if curr_id:
                part = particle_list.get_particle(curr_id)
                particles = np.append(particles, part)

    if len(particles) < 2:
        session.logger.warning("Select at least two points")
        return
    elif len(particles) <= 3:
        degree = 1
    else:
        degree = 3

    smooth = 0
    resolution = 300
    from .CurvedLine import get_points
    points, der = get_points(session, particles, smooth, degree, resolution)

    # Reorient selected particles so that Z-axis points towards next particle
    # particle_index = 0
    # last_part = None
    # for particle_list in session.ArtiaX.partlists.child_models():
    #     for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
    #         if curr_id:
    #             curr_part = particle_list.get_particle(curr_id)
    #             if particle_index != 0:
    #                 rotation_to_z = z_align(np.asarray(last_part.coord), np.asarray(curr_part.coord))
    #                 rotation = rotation_to_z.zero_translation().inverse()
    #                 last_part.rotation = rotation
    #                 if particle_index + 1 == len(particles):  # last selected particle
    #                     curr_part.rotation = rotation
    #             last_part = curr_part
    #             particle_index += 1
    #     # Updated graphics
    #     particle_list.update_places()

    from .CurvedLine import CurvedLine
    if degree == 1:
        name = "line"
    else:
        name = "curved line"
    geomodel = CurvedLine(name, session, particles, points, der, degree, smooth, resolution)
    artiax.add_geomodel(geomodel)


def fit_plane(session):
    particle_pos, particles = get_curr_selected_particles_pos(session)
    if len(particles) < 3:
        session.logger.warning("Select at least three points")
        return
    resolution = 50
    method = 'cubic'  # nearest, cubic, or linear

    from .Plane import get_normal_and_pos, get_grid, Plane
    normal = get_normal_and_pos(particles, particle_pos)
    points = get_grid(particle_pos, normal, resolution, method)
    geomodel = Plane('plane', session, particles, particle_pos, normal, points, resolution, method)

    session.ArtiaX.add_geomodel(geomodel)
