# General imports
import numpy as np
import math
from scipy.spatial import Delaunay

# ChimeraX imports
from chimerax.core.models import Surface

# Triggers
GEOMODEL_CHANGED = 'geomodel changed'  # Data is the modified geometric model.


class GeoModel(Surface):
    """
    Parent class for all geometric models. Also handles static methods for creating models from particles,
    helping functions, and opening saved geomodels.
    """

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
    """ Returns selected geomodels, either all models or only the ones matching the name provided.

    Parameters
    ----------
    model: str
        name of a geomodel class.

    Returns
    -------
    s_geomodels: A list with all selected geomodels that matches the criteria.
    """
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
    """ Returns selected particles, particle position, or markers.

    Parameters
    ----------
    session
    return_particles: Bool
        Decides whether to return the list of all selected particles.
    return_pos: Bool
        Decides whether to return the list particle positions.
    return_markers: Bool
        Decides whether to return the list of markers belonging to all selected particles.

    Returns
    -------
    particle_pos: (n x 3) numpy array containing the xyz positions of the n selected particles.
    particles: A list with all currently selected particles.
    marksers: A list with all markers belonging to all selected particles.
    """
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
    geomodel = Sphere("sphere", session, particle_pos, particles=particles)
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
    geomodel = CurvedLine(name, session, particle_pos, degree, smooth, resolution, particles=particles)
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
    geomodel = Surface('surface', session, particle_pos, resolution, method, particles=particles)

    session.ArtiaX.add_geomodel(geomodel)
    geomodel.selected = True


def surface_from_links(session):
    from chimerax.markers.markers import selected_markers
    if len(selected_markers(session).bonds.unique().atoms[0]) < 3:
        session.logger.warning("Select at least three particles that are linked in a triangle")
        return
    particle_pairs = np.asarray(selected_markers(session).bonds.unique().atoms)
    particles = get_curr_selected_particles(session, return_particles=True, return_pos=False)

    from .TrangulationSurface import triangles_from_pairs, TriangulationSurface
    triangles = triangles_from_pairs(particle_pairs)
    if len(triangles) < 1:
        session.logger.warning("Select at least three particles that are linked in a triangle")
        return

    geomodel = TriangulationSurface("triangulated surface", session, particle_pairs, particles, triangles)
    session.ArtiaX.add_geomodel(geomodel)
    geomodel.selected = True


def boundary(session):
    particle_pos, particles = get_curr_selected_particles(session)
    if len(particles) < 5:
        session.logger.warning("Select at least five points")
        return

    from .Boundary import Boundary
    alpha = 0.7
    geomodel = Boundary("boundary", session, particle_pos, alpha, particles=particles)
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
    """ Not used, but can be used to delete individual triangles from surface, triangulated surface or boundary models.

    Parameters
    ----------
    geomodel: GeoModel
        Geomodel to remove the triangle from.
    triangle: int
        index of the triangle to remove.
    """
    # Have to reshuffle the other triangles to make sure the order of the vertices stays the same,
    # otherwise the model looks wierd.
    triangles = np.append(geomodel.triangles[:triangle], geomodel.triangles[triangle + 1:], axis=0)
    for i, t in enumerate(triangles[triangle:]):
        triangles[i + triangle] = t - [3, 3, 3]
    normals = np.append(geomodel.normals[:triangle*3], geomodel.normals[(triangle+1)*3:], axis=0)
    vertices = np.append(geomodel.vertices[:triangle*3], geomodel.vertices[(triangle+1)*3:], axis=0)
    geomodel.set_geometry(vertices, normals, triangles)
    geomodel.vertex_colors = np.full((len(vertices), 4), geomodel.color)


def open_model(session, modelname, model_type, data):
    """ Used to create models from saved data.

    Parameters
    ----------
    modelname: str
        name of the model.
    model_type: str
        name of model class.
    data: dict
        contains all saved data from the model.
    Returns
    -------
    model: GeoModel
        The model created from the file.
    """
    model = None
    if model_type == "Sphere":
        from .Sphere import Sphere
        model = Sphere(modelname, session, data['particle_pos'], center=data['center'], r=data['r'])
    elif model_type == "CurvedLine":
        from .CurvedLine import CurvedLine
        model = CurvedLine(modelname, session, data['particle_pos'], int(data['degree']), float(data['smooth']),
                           float(data['resolution']), points=data['points'], der_points=data['der_points'])
    elif model_type == "Surface":
        from .Surface import Surface
        model = Surface(modelname, session, data['particle_pos'], float(data['resolution']), str(data['method']),
                        normal=data['normal'], points=data['points'])
    elif model_type == "TriangulationSurface":
        from .TrangulationSurface import TriangulationSurface
        model = TriangulationSurface(modelname, session, triangles=data['triangles'])
    elif model_type == "Boundary":
        from .Boundary import Boundary
        model = Boundary(modelname, session, data['particle_pos'], float(data['alpha']), triangles=data['triangles'],
                         delete_tri_list=data['delete_tri_list'])

    return model

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

