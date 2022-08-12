# General imports
import numpy as np
import math
from scipy.spatial import Delaunay

# ChimeraX imports
from chimerax.core.models import Surface
from chimerax.geometry import z_align

# Triggers
GEOMODEL_CHANGED = 'geomodel changed'  # Data is the modified geometric model.


class GeoModel(Surface):
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

    def write_file(self, file_name):
        pass

    def read_file(self, file_name):
        pass


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

    from .Sphere import Sphere
    geomodel = Sphere("sphere", session, particles, particle_pos)
    artiax.add_geomodel(geomodel)
    geomodel.selected = True


def fit_curved_line(session):
    artiax = session.ArtiaX

    particle_pos, particles = get_curr_selected_particles(session)

    if len(particles) < 2:
        session.logger.warning("Select at least two points")
        return
    elif len(particles) <= 3:
        degree = 1
    else:
        degree = 3

    smooth = 0
    resolution = 300

    from .CurvedLine import CurvedLine
    if degree == 1:
        name = "line"
    else:
        name = "curved line"
    geomodel = CurvedLine(name, session, particle_pos, particles, degree, smooth, resolution)
    artiax.add_geomodel(geomodel)
    geomodel.selected = True

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


def fit_surface(session):
    particle_pos, particles = get_curr_selected_particles(session)
    if len(particles) < 3:
        session.logger.warning("Select at least three points")
        return
    resolution = 50
    method = 'cubic'  # nearest, cubic, or linear

    from .Surface import Surface
    geomodel = Surface('surface', session, particles, particle_pos, resolution, method)

    session.ArtiaX.add_geomodel(geomodel)
    geomodel.selected = True


def surface_from_links(session):
    from chimerax.markers.markers import selected_markers
    if len(selected_markers(session).bonds.unique().atoms[0]) < 3:
        session.logger.warning("Select at least three particles that are linked in a triangle")
        return
    particle_pairs = np.asarray(selected_markers(session).bonds.unique().atoms)

    from .TrangulationSurface import triangles_from_pairs, TriangulationSurface
    triangles = triangles_from_pairs(particle_pairs)
    if len(triangles) < 1:
        session.logger.warning("Select at least three particles that are linked in a triangle")
        return

    geomodel = TriangulationSurface("triangulated surface", session, particle_pairs, triangles)
    session.ArtiaX.add_geomodel(geomodel)
    geomodel.selected = True


def boundary(session):
    particle_pos, particles = get_curr_selected_particles(session)
    if len(particles) < 5:
        session.logger.warning("Select at least five points")
        return

    from .Boundary import Boundary
    alpha = 0.7
    geomodel = Boundary("boundary", session, particles, particle_pos, alpha)
    session.ArtiaX.add_geomodel(geomodel)
    geomodel.selected = True


def triangulate_selected(session, furthest_site):
    particle_pos, markers = get_curr_selected_particles(session, return_particles=False, return_markers=True)
    if len(markers) < 5:
        session.logger.warning("Select at least five points")
        return

    connections = Delaunay(particle_pos, furthest_site=furthest_site).simplices
    from .TrangulationSurface import make_links
    make_links(markers, connections)


def remove_selected_links(session):
    from chimerax.markers.markers import selected_markers
    bonds = selected_markers(session).bonds.unique()
    bonds.delete()


def remove_triangle(geomodel, triangle):
    triangles = np.append(geomodel.triangles[:triangle], geomodel.triangles[triangle + 1:], axis=0)
    for i, t in enumerate(triangles[triangle:]):
        triangles[i + triangle] = t - [3, 3, 3]
    normals = np.append(geomodel.normals[:triangle*3], geomodel.normals[(triangle+1)*3:], axis=0)
    vertices = np.append(geomodel.vertices[:triangle*3], geomodel.vertices[(triangle+1)*3:], axis=0)
    geomodel.set_geometry(vertices, normals, triangles)
    geomodel.vertex_colors = np.full((len(vertices), 4), geomodel.color)


# def fit_line(session):
#     # NOT USED
#     """Creates a line between two particles"""
#     artiax = session.ArtiaX
#
#     particle_pos, particles = get_curr_selected_particles(session)
#
#     if len(particle_pos) != 2:
#         session.logger.warning("Only select a start and end point")
#         return
#
#     start = particle_pos[0]
#     end = particle_pos[1]
#
#     # Reorient selected particles so that Z-axis along the line
#     rotation_to_z = z_align(start, end)
#     rotation = rotation_to_z.zero_translation().inverse()
#     for particle_list in session.ArtiaX.partlists.child_models():
#         for curr_id in particle_list.particle_ids[particle_list.selected_particles]:
#             if curr_id:
#                 curr_part = particle_list.get_particle(curr_id)
#                 curr_part.rotation = rotation
#         # Updated graphics
#         particle_list.update_places()
#
#     from .Line import Line
#     geomodel = Line("line", session, particles, start, end)
#     artiax.add_geomodel(geomodel)
#     geomodel.selected = True

