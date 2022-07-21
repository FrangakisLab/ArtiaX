# General imports
import numpy as np
import math

# ChimeraX imports
from chimerax.core.models import Model
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


def get_curr_selected_particles(session, return_particles=True, return_pos=True, return_markers=False):
    artiax = session.ArtiaX

    # Find selected particles
    particles = np.array([])
    markers = np.array([])
    particle_pos = np.zeros((0, 3))  # each row is one currently selected particle, with columns being x,y,z
    for particle_list in artiax.partlists.child_models():
        for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
            if curr_id:
                curr_part = particle_list.get_particle(curr_id)
                if return_particles:
                    particles = np.append(particles, curr_part)
                if return_pos:
                    x_pos = curr_part.coord[0]
                    y_pos = curr_part.coord[1]
                    z_pos = curr_part.coord[2]
                    particle_pos = np.append(particle_pos, [[x_pos, y_pos, z_pos]], axis=0)
                if return_markers:
                    curr_marker = particle_list.get_marker(curr_id)
                    markers = np.append(markers, curr_marker)

    if return_pos and return_particles and return_markers:
        return particle_pos, particles, markers
    elif return_pos and return_particles:
        return particle_pos, particles
    elif return_pos and return_markers:
        return particle_pos, markers
    elif return_particles and return_markers:
        return particles, markers
    elif return_pos:
        return particle_pos
    elif return_particles:
        return particles
    else:
        return markers


def fit_sphere(session):
    """Fits a sphere to the currently selected particles"""
    artiax = session.ArtiaX

    particle_pos, particles = get_curr_selected_particles(session)

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

    particle_pos, particles = get_curr_selected_particles(session)

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

    particles = get_curr_selected_particles(session, return_pos=False)

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

    # Reorient selected particles so that Z-axis points towards next particle NOW ITS OWN COMMAND
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


def fit_surface(session):
    particle_pos, particles = get_curr_selected_particles(session)
    if len(particles) < 3:
        session.logger.warning("Select at least three points")
        return
    resolution = 50
    method = 'cubic'  # nearest, cubic, or linear

    from .Surface import get_normal_and_pos, get_grid, Surface
    normal = get_normal_and_pos(particles, particle_pos)
    points = get_grid(particle_pos, normal, resolution, method)
    geomodel = Surface('surface', session, particles, particle_pos, normal, points, resolution, method)

    session.ArtiaX.add_geomodel(geomodel)


def triangulate_selected(session):
    particle_pos, markers = get_curr_selected_particles(session, return_particles=False, return_markers=True)
    if len(markers) < 5:
        session.logger.warning("Select at least five points")
        return

    from scipy.spatial import Delaunay
    connections = Delaunay(particle_pos, furthest_site=True).simplices #  TODO make this an optional argument
    from .TrangulationSurface import make_links
    make_links(markers, connections)


def remove_selected_links(session):
    from chimerax.markers.markers import selected_markers
    bonds = selected_markers(session).bonds.unique()
    bonds.delete()


def surface_from_links(session):
    from chimerax.markers.markers import selected_markers
    particle_pairs = np.asarray(selected_markers(session).bonds.unique().atoms)
    triangles = np.zeros((0,3,3))
    triangle_made = False
    while len(particle_pairs[0]) > 1:
        first_corner = particle_pairs[0][0]
        second_corner = particle_pairs[1][0]
        bonds_that_contain_first = find_bonds_containing_corner(particle_pairs, first_corner)
        bonds_that_contain_second = find_bonds_containing_corner(particle_pairs, second_corner)
        for second_side in bonds_that_contain_second:
            if second_corner == particle_pairs[0][second_side]:
                third_corner = particle_pairs[1][second_side]
            else:
                third_corner = particle_pairs[0][second_side]
            for third_side in bonds_that_contain_first:
                if third_corner == particle_pairs[0][third_side] or third_corner == particle_pairs[1][third_side]:
                    triangle_made = True
                    triangles = np.append(triangles, [[first_corner.coord, second_corner.coord, third_corner.coord]], axis=0)
        particle_pairs = np.delete(particle_pairs, 0, 1)

    if not triangle_made:
        session.logger.warning("Select particles that form at least one triangle.")
        return

    from .TrangulationSurface import TriangulationSurface
    geomodel = TriangulationSurface("triangulated surface", session, triangles)
    session.ArtiaX.add_geomodel(geomodel)


def find_bonds_containing_corner(particle_pairs, corner):
    bonds_containing_corner = np.array([])
    for bond in range(0, len(particle_pairs[0])):
        if particle_pairs[0][bond] == corner or particle_pairs[1][bond] == corner:
            bonds_containing_corner = np.append(bonds_containing_corner, bond)
    return bonds_containing_corner.astype(np.int)


def boundry(session):
    particle_pos, markers = get_curr_selected_particles(session, return_particles=False, return_markers=True)
    if len(markers) < 5:
        session.logger.warning("Select at least five points")
        return

    # TODO: calculate stuff here and create the model