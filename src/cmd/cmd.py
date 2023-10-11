# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
import math

# ChimeraX
from chimerax.core import errors
from chimerax.map import Volume
import numpy as np

# This package
from ..util.view import *


def get_singleton(session, create=True):
    if not session.ui.is_gui:
        return None

    from chimerax.core import tools
    from ..tool import ArtiaXUI

    t = tools.get_singleton(session, ArtiaXUI, 'ArtiaX', create=create)
    t.get_root()
    return t

def artiax_start(session):
    """Start ArtiaX UI."""
    if not session.ui.is_gui:
        session.logger.warning("ArtiaX requires Chimerax GUI.")

    get_singleton(session)
    return session.ArtiaX


def artiax_open_tomo(session, path):
    """Open a tomogram."""
    get_singleton(session)
    session.ArtiaX.open_tomogram(path)


def artiax_add_tomo(session, models=None):
    """Add a tomogram already open in ChimeraX."""
    # No Model
    if models is None:
        session.logger.warning("artiax add tomo: No model specified.")
        return

    # Filter by class
    ms = [m for m in models if isinstance(m, Volume)]

    # Make sure it's running
    get_singleton(session)

    # Add
    for model in ms:
        session.ArtiaX.import_tomogram(model)


# def artiax_close_tomo(session, models=None):
#     """Close a tomogram by internal ID."""
#     # No ArtiaX
#     if not hasattr(session, 'ArtiaX'):
#         session.logger.warning("ArtiaX is not currently running, so no tomograms can be closed.")
#         return
#
#     # No Model
#     if models is None:
#         session.logger.warning("artiax close tomo: No model specified.")
#         return
#
#     # Filter by class
#     ms = []
#     for model in models:
#         if not session.ArtiaX.tomograms.has_id(model.id):
#             session.logger.warning(
#                 'artiax close tomo: Model #{} - "{}" is not managed by ArtiaX'.format(model.id_string, model.name))
#             continue
#
#         ms.append(model)
#
#     # Close
#     for model in ms:
#         session.ArtiaX.close_tomogram(model.id)


def artiax_view(session, direction=None):
    """Set the current camera position to one of the perpendicular views."""
    directions = {
        'xy': view_xy,
        'xz': view_xz,
        'yz': view_yz
    }

    if direction is None:
        direction = 'xy'

    if direction not in directions.keys():
        raise errors.UserError(
            "{} is not a viewing direction known to ArtiaX. Expected one of 'xy', 'xz', or 'yz'.".format(direction))

    directions[direction.lower()](session)


# def artiax_open_particlelist(session, path, format):
#     """Open a particle list in ArtiaX"""
#     get_singleton(session)
#     session.ArtiaX.open_partlist(path, format)
#
#
# def artiax_save_particlelist(session, index, path, format):
#     """Save a particle list in specified format."""
#     if not hasattr(session, 'ArtiaX'):
#         session.logger.warning("ArtiaX is not currently running, so no lists can be saved.")
#         return
#
#     if index < 1 or index > session.ArtiaX.partlist_count:
#         raise errors.UserError("artiax save particles: Requested index {} is outside range 1 to {}".format(index, session.ArtiaX.partlist_count))
#
#     session.ArtiaX.save_partlist(index-1, path, format)


def artiax_attach(session, model=None, toParticleList=None):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so nothing can be attached.")
        return

    # No Volume
    if model is None:
        raise errors.UserError("artiax attach: model parameter needs to be set.")

    # No PL
    if toParticleList is None:
        raise errors.UserError("artiax attach: toParticleList parameter needs to be set.")

    # Model not Volume
    if not isinstance(model, Volume):
        raise errors.UserError("artiax attach: model needs to be a Volume, but is {}.".format(type(model)))

    # Model is Tomogram
    if session.ArtiaX.tomograms.has_id(model.id):
        raise errors.UserError(
            "artiax attach: cannot attach a Tomogram as a particle list surface.".format(type(model)))

    # Not a Particle list
    if not session.ArtiaX.partlists.has_id(toParticleList.id):
        session.logger.warning(
            'artiax attach: Model #{} - "{}" is not managed by ArtiaX'.format(toParticleList.id_string,
                                                                              toParticleList.name))
        return

    session.ArtiaX.attach_display_model(toParticleList, model)


def artiax_show(session, models=None, style=None):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so nothing can be shown.")
        return

    from ..util.view import show
    show(session, models, style)


def artiax_hide(session, models=None, style=None):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so nothing can be shown.")
        return

    from ..util.view import show
    show(session, models, style, do_show=False)


def artiax_fit_sphere(session):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so no sphere can be fitted.")
        return

    from ..geometricmodel.GeoModel import fit_sphere
    fit_sphere(session)


def artiax_fit_line(session):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so no line can be fitted.")
        return

    from ..geometricmodel.GeoModel import fit_curved_line
    fit_curved_line(session)


def artiax_fit_surface(session):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so no surface can be fitted.")
        return

    from ..geometricmodel.GeoModel import fit_surface
    fit_surface(session)


def artiax_triangulate(session, furthestSite=None):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, links can be created between particles.")
        return
    if furthestSite is None:
        furthestSite = True
    from ..geometricmodel.GeoModel import triangulate_selected
    triangulate_selected(session, furthestSite)


def artiax_boundary(session):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so no boundary can be made.")
        return

    from ..geometricmodel.GeoModel import boundary
    boundary(session)


def artiax_mask(session):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so no mask can be made.")
        return

    from ..geometricmodel.GeoModel import selected_geomodels
    s_geomodels = selected_geomodels(session)
    if len(s_geomodels) == 0:
        session.logger.warning("Select a geometric model.")
        return
    run(session, "volume onesmask #{}.{}.{}".format(*s_geomodels[0].id))


def artiax_remove_links(session):
    from ..geometricmodel.GeoModel import remove_selected_links
    remove_selected_links(session)


def artiax_triangles_from_links(session):
    from ..geometricmodel.GeoModel import surface_from_links
    surface_from_links(session)


def artiax_flip(session, axis=None):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so no particles can be reoriented.")
        return

    if axis is None:
        axis = [1,0,0]
    else:
        axis = np.asarray(axis.coords)
        axis = axis/np.linalg.norm(axis)

    from ..geometricmodel.GeoModel import get_curr_selected_particles
    particle_pos, particles = get_curr_selected_particles(session)
    from chimerax.geometry import rotation
    for particle in particles:
        external_axis = particle.rotation.transform_vector(axis)
        particle.rotation = rotation(external_axis, 180) * particle.rotation

    for particle_list in session.ArtiaX.partlists.iter():
        particle_list.update_places()


def artiax_select_inside_surface(session):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so no particles can be selected.")
        return
    from chimerax.map import VolumeSurface
    from ..geometricmodel import GeoModel
    model = None
    for m in session.selection.models():
        if isinstance(m, (VolumeSurface, GeoModel)):
            model = m
            break
    if model is None:
        session.logger.warning("Select a model with a surface.")
        return

    """looks for intersections from particle to outside bounding box in the z-direction. If theres an intersection,
     a new intersection is looked for from that point to the outside of the bounding box. Continues until there are no
     more intersections. If there was an even number of intersections, the particle is outside the volume, if
     there was an odd number of intersections, it's inside."""
    bounds = model.bounds()
    from chimerax.geometry._geometry import closest_triangle_intercept
    for pl in session.ArtiaX.partlists.iter():
        if pl.visible:
            pl.selected_particles = False
            atoms = pl.markers.atoms
            select_particles = np.array(atoms.selecteds)
            for i, p_id in enumerate(pl.particle_ids[pl.displayed_particles]):
                pos = np.asarray(pl.get_particle(p_id).coord)
                if not(np.any(pos > bounds.xyz_max) or np.any(pos < bounds.xyz_min)): #  inside bounding box
                    intersepts = 0
                    dist_to_end = bounds.xyz_max[2] - pos[2] + 1
                    if isinstance(model, VolumeSurface):
                        vertices = model.parent.position.transform_points(model.vertices)
                    else:
                        vertices = model.vertices
                    dist_to_tri, tnum = closest_triangle_intercept(vertices, model.triangles, pos, pos + [0,0,dist_to_end])
                    start = pos
                    margin = 0.001
                    while dist_to_tri is not None:
                        intersepts += 1
                        if intersepts > 100:
                            session.logger.warning("Too many intersepts, terminating.")
                            break
                        start = [start[0],start[1],start[2] + dist_to_tri*dist_to_end+margin]
                        dist_to_end = bounds.xyz_max[2] - start[2] + 1
                        end = [start[0],start[1],start[2] + dist_to_end]
                        dist_to_tri, tnum = closest_triangle_intercept(vertices, model.triangles, start, end)
                    if intersepts % 2:
                        select_particles[i] = True
            atoms.selecteds = select_particles


def artiax_geomodel_color(session, model, color):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    model.color = color.uint8x4()

def artiax_move_camera_along_line(session, model, numFrames=None, backwards=False, distanceBehind=10000, topRotation=0,
                                  facingRotation=0, cameraRotation=0, monoCamera=True, maxAngle=None):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return
    from ..geometricmodel.CurvedLine import CurvedLine
    if not isinstance(model, CurvedLine):
        errors.UserError("artiax moveCameraAlongLine: '{}' is not a valid argument. Input a 'line' geometric model.".format(model))
    if numFrames is not None and numFrames >= len(model.points[0]):
        session.logger.warning("artiax moveCameraAlongLine: the specified number of frames cannot be higher"
                               " than the resolution of the line. Changing number of frames to {}.".format(len(model.points[0])))
        numFrames = None
    if monoCamera:
        from chimerax.core.commands import run
        run(session, "camera mono")

    model.move_camera_along_line(False, numFrames, backwards, distanceBehind, topRotation, facingRotation, cameraRotation, max_angle=maxAngle)


def artiax_remove_overlap(session, models=None, manifold=None, boundary=None, freeze=None, method='distance', iterations=None, thoroughness=None, precision=None, maxSearchDistance=None):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    from ..particle import ParticleList
    particles = []
    pls = []
    scms = dict()
    bounds = dict()
    if models is not None:
        for model in models:
            if isinstance(model, ParticleList):
                pl = model
                if pl.has_display_model():
                    pls.append(pl)
                    scm = pl.collection_model.collections['surfaces']
                    bound = pl.display_model.get(0).surfaces[0].geometry_bounds()
                    ps = [pl.get_particle(cid) for cid in pl.particle_ids]
                    particles.extend(ps)
                    for p in ps:
                        scms[p] = scm
                        bounds[p] = bound
                else:
                    raise errors.UserError(
                        'artiax remove overlap: Model #{} - "{}" does not have an attached surface.'.format(model.id_string,
                                                                                                       model.name))
            else:
                raise errors.UserError(
                    'artiax remove overlap: Model #{} - "{}" is not a particle list.'.format(model.id_string,
                                                                                       model.name))
    elif boundary is None and manifold is None:  # No particle list given, use selected particles instead
        for pl in session.ArtiaX.partlists.child_models():
            if not pl.has_display_model():
                continue
            scm = pl.collection_model.collections['surfaces']
            bound = pl.display_model.get(0).surfaces[0].geometry_bounds()
            particle_list_used = False
            for curr_id in pl.particle_ids[pl.selected_particles]:
                if curr_id:
                    particle_list_used = True
                    p = pl.get_particle(curr_id)
                    particles.append(p)
                    scms[p] = scm
                    bounds[p] = bound
            if particle_list_used:
                pls.append(pl)

    from chimerax.core.models import Drawing
    on_surface_particles = None
    if manifold is not None:
        on_surface_particles = []
        for pair in manifold:
            if len(pair) != 2:
                raise errors.UserError(
                    'artiax remove overlap manifold: Please select exactly one particle list and one drawing per'
                    ' manifold.')
            elif not isinstance(pair[0], ParticleList):
                raise errors.UserError(
                    'artiax remove overlap manifold: Model #{} - "{}" is not a particle list.'.format(
                        pair[0].id_string, pair[0].name))
            elif not isinstance(pair[1], Drawing) or isinstance(pair[1], ParticleList):
                raise errors.UserError(
                    'artiax remove overlap manifold: Model #{} - "{}" is not a drawing.'.format(
                        pair[1].id_string, pair[1].name))

            pl = pair[0]
            if not pl.has_display_model():
                raise errors.UserError(
                    'artiax remove overlap: Model #{} - "{}" does not have an attached surface.'.format(
                        pl.id_string, pl.name))
            pls.append(pl)
            scm = pl.collection_model.collections['surfaces']
            bound = pl.display_model.get(0).surfaces[0].geometry_bounds()
            ps = [pl.get_particle(cid) for cid in pl.particle_ids]
            for p in ps:
                scms[p] = scm
                bounds[p] = bound
            particles.extend(ps)
            on_surface_particles.append([ps, pair[1]])

    in_surface_particles = None
    if boundary is not None:
        from chimerax.surface import vertex_areas
        in_surface_particles = []
        for pair in boundary:
            if len(pair) != 2:
                raise errors.UserError(
                    'artiax remove overlap boundary: Please select exactly one particle list and one drawing per'
                    ' boundary.')
            elif not isinstance(pair[0], ParticleList):
                raise errors.UserError(
                    'artiax remove overlap boundary: Model #{} - "{}" is not a particle list.'.format(
                        pair[0].id_string, pair[0].name))
            elif not isinstance(pair[1], Drawing) or isinstance(pair[1], ParticleList):
                raise errors.UserError(
                    'artiax remove overlap boundary: Model #{} - "{}" is not a drawing.'.format(
                        pair[1].id_string, pair[1].name))

            pl = pair[0]
            if not pl.has_display_model():
                raise errors.UserError(
                    'artiax remove overlap: Model #{} - "{}" does not have an attached surface.'.format(
                        pl.id_string, pl.name))
            pls.append(pl)
            scm = pl.collection_model.collections['surfaces']
            bound = pl.display_model.get(0).surfaces[0].geometry_bounds()
            ps = [pl.get_particle(cid) for cid in pl.particle_ids]
            for p in ps:
                scms[p] = scm
                bounds[p] = bound
            particles.extend(ps)

            surface = pair[1]

            # Get an estimate of the distance between the surface vertices
            max_search_distance = maxSearchDistance
            if max_search_distance is None:
                max_search_distance = 100
            elif max_search_distance <= 0:
                raise errors.UserError(
                    'artiax remove overlap: Select a positive max search distance.'.format(
                        pl.id_string, pl.name))

            search_distance = np.sqrt(vertex_areas(surface.vertices, surface.triangles).mean())
            if search_distance > max_search_distance:
                search_distance = max_search_distance

            in_surface_particles.append([ps, surface, search_distance])

    if len(pls) != len(set(pls)):
        raise errors.UserError(
            "artiax remove overlap: Please don't select a particle list more than once.")

    if not particles:
        raise errors.UserError(
            'artiax remove overlap: No particles with an attached surface selected')

    if method == 'distance':
        if thoroughness is not None or precision is not None:
            raise errors.UserError(
                'artiax remove overlap: Method "distance" does not accept keywords "thoroughness" or "precision".'
                ' To use these settings, use "method volume".')
    else:
        if thoroughness is None:
            thoroughness = 100
        if precision is None:
            precision = 0.33

    if iterations is None:
        max_iterations = 100
    elif iterations < 1:
        raise errors.UserError(
            'artiax remove overlap: iterations must be set to at least 1.')
    else:
        max_iterations = iterations

    if freeze is not None:
        particles_to_keep_still = {p: False for p in particles}
        for pl in freeze:
            if not isinstance(pl, ParticleList) or not pl.has_display_model():
                raise errors.UserError(
                    'artiax remove overlap: model {} is not a particles list, or has no display model.'.format(pl))
            if pl in pls:
                raise errors.UserError(
                    'artiax remove overlap: model {} is included both as a particle list to move and to keep still'.format(pl))
            pls.append(pl)
            scm = pl.collection_model.collections['surfaces']
            bound = pl.display_model.get(0).surfaces[0].geometry_bounds()
            ps = [pl.get_particle(cid) for cid in pl.particle_ids]
            particles.extend(ps)
            for p in ps:
                scms[p] = scm
                bounds[p] = bound
                particles_to_keep_still[p] = True
    else:
        particles_to_keep_still = None


    from ..util.remove_overlap import remove_overlap
    remove_overlap(session, particles, pls, scms, bounds, method, on_surface_particles, in_surface_particles, particles_to_keep_still, max_iterations, thoroughness, precision)


def artiax_gen_in_surface(session, model, method, num_pts=None, radius=None, exactNum=False):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    from chimerax.core.models import Surface
    if not isinstance(model, Surface):
        session.logger.warning("{} is not a Surface.".format(model))
        return

    if method not in ['poisson', 'regular grid', 'uniform']:
        session.logger.warning(
            "{} is not a valid method of generating points in a surface. Please use one of 'poisson'"
            ", 'regular grid', or 'uniform'.".format(method))
        return
    elif method in ['uniform', 'regular grid'] and (num_pts is None or num_pts<0):
        session.logger.warning("Please input a number of points larger than 0 using the 'num_points' keyword when"
                               " generating points in a surface using uniform sampling or on a regular grid.")
        return
    elif method == 'poisson' and (radius is None or radius<0):
        session.logger.warning("Please input a radius larger than 0 using the 'radius' keyword when"
                               " generating points in a surface using poisson disk sampling.")
        return
    if method in ['poisson', 'regular grid'] and exactNum:
        session.logger.warning("Cannot create an exact number of particles when using 'poisson' or 'regular grid' method.")
        return

    from ..util.generate_points import generate_points_in_surface
    generate_points_in_surface(session, model, radius, num_pts, method, exact_num=exactNum)


def artiax_gen_on_surface(session, model, method, num_pts, radius=None, exactNum=True):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    from chimerax.core.models import Surface
    if not isinstance(model, Surface):
        session.logger.warning("{} is not a Surface.".format(model))
        return

    if method not in ['poisson', 'uniform']:
        session.logger.warning(
            "{} is not a valid method of generating points on a surface. Please use one of 'poisson'"
            " or 'uniform'.".format(method))
        return
    elif num_pts < 1:
        session.logger.warning("Please input a number of points larger than 0 using the 'num_points' keyword when"
                               " generating points on a surface.")
        return
    elif method == 'poisson' and (radius is None or radius < 0):
        session.logger.warning("Please input a radius larger than 0 using the 'radius' keyword when"
                               " generating points on a surface using poisson disk sampling.")
        return

    from ..util.generate_points import generate_points_on_surface
    generate_points_on_surface(session, model, num_pts, radius, method, exact_num=exactNum)


def artiax_geomodel_to_volume(session, model=None, geomodels=None, subdivide_length=None):
    from ..volume.Tomogram import Tomogram
    from chimerax.surface._surface import subdivide_mesh
    from chimerax.map_data import ArrayGridData

    new_model = False
    if model is None:
        new_model = True
        ps = [1, 1, 1]
        name = 'segmented surfaces'
    elif not isinstance(model, Tomogram):
        session.logger.warning("{} is not a tomogram loaded into ArtiaX".format(model))
        return
    else:
        tomo = model
        name = tomo.name
        ps = tomo.pixelsize
        mat = tomo.data.matrix().copy()

    if geomodels is None:
        geomodels = [g for g in session.ArtiaX.geomodels.child_models() if g.visible]

    if subdivide_length is None:
        subdivide_length = min(ps)

    if new_model:
        from chimerax.geometry.bounds import union_bounds
        union = union_bounds([gm.geometry_bounds() for gm in geomodels])
        xyz_max = union.xyz_max
        xyz_min = union.xyz_min
        matsize = np.flip(np.ceil(xyz_max - xyz_min).astype(int))
        mat = np.zeros(matsize, dtype=np.float32)

    # For each geomodel
    for geomodel in geomodels:  # Get verts and subdiv
        if geomodel.triangle_mask is None:
            vs, ts, ns = geomodel.vertices, geomodel.triangles, geomodel.normals
        else:
            vs, ts, ns = geomodel.vertices, geomodel.triangles[geomodel.triangle_mask,:], geomodel.normals

        vs, ts, ns = subdivide_mesh(vs, ts, ns, subdivide_length)

        vs_index = np.unique(ts[:])
        vs = vs[vs_index, :]

        # Set voxels
        for i, v in enumerate(vs):

            if new_model:
                index = v
                index = index - xyz_min
            else:
                index = tomo.data.xyz_to_ijk(v)
            index = np.flip(np.array(np.floor(index), dtype=int))  # flipped to make it [zi, yi, xi]
            if (index<[0,0,0]).any() or (index >= mat.shape).any():
                session.logger.warning("Model {} is outside of volume.".format(geomodel))
                break
            mat[index[0], index[1], index[2]] = 1

    agd = ArrayGridData(mat, step=ps, name=name)

    if new_model:
        new_tomo = Tomogram(session, agd)
        new_tomo.set_parameters(surface_levels=[0.999])
        session.ArtiaX.add_tomogram(new_tomo)
    else:
        tomo.replace_data(agd)

        from chimerax.map.volume import VolumeImage
        for drawing in tomo._child_drawings:
            if isinstance(drawing, VolumeImage):
                drawing.close_model()
                tomo.integer_slab_position = tomo.integer_slab_position


def artiax_masked_triangles_to_geomodel(session, models=None, name='arbitrary model'):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    from chimerax.map.volume import VolumeSurface
    surfaces = []

    if models is not None:
        for model in models:
            if not isinstance(model, Volume):
                session.logger.warning("{} is not a volume".format(model))
                return
            if model.empty_drawing():
                surface = None
                for d in model.child_drawings():
                    if not d.empty_drawing():
                        surface = d
                        break
                if surface is None:
                    session.logger.warning("{} does not contain a drawing with a surface".format(model))
                    return
            else:
                surface = model
            surfaces.append(surface)
    else:
        for model in session.selection.models():
            if isinstance(model, Volume):
                childs = [x for x in model.child_drawings() if isinstance(x, VolumeSurface)]
                if not len(childs):
                    break
                else:
                    surfaces.extend(childs)
        if not len(surfaces):
            session.logger.warning("No drawing with a surface is currently selected")
            return

    surfaces = np.unique(surfaces)

    verts, normals, tris = [], [], []
    for surface in surfaces:
        t = surface.triangles if surface.triangle_mask is None else surface.triangles[surface.triangle_mask]
        t = t + len(verts)
        tris.extend(t)
        verts.extend(surface.vertices)
        normals.extend(surface.normals)
    verts, normals, tris = np.array(verts), np.array(normals), np.array(tris)

    from ..geometricmodel.ArbitraryModel import ArbitraryModel
    a = ArbitraryModel(name, session, verts, normals, tris)

    session.ArtiaX.add_geomodel(a)

def artiax_mask_triangles_radius(session, radius=None):
    if radius is not None and radius<=0:
        session.logger.warning("Select a positive radius.")
        return
    from ..mouse import MaskConnectedTrianglesMode
    mct = session.ArtiaX.mask_connected_triangles
    session.ui.mouse_modes.remove_mode(mct)
    mct = session.ArtiaX.mask_connected_triangles = MaskConnectedTrianglesMode(session, radius)
    session.ui.mouse_modes.add_mode(mct)
    run(session, 'ui mousemode right "mask connected triangles"')

def artiax_filter_tomo(session, tomo, lp, hp, lpd=None, hpd=None, unit='pixels', lp_cutoff='gaussian', hp_cutoff='gaussian', threshold=0.001):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    from ..volume import Tomogram
    if not isinstance(tomo, Tomogram):
        session.logger.warning("Model {} is not a tomogram.".format(tomo))
        return

    if lp < 0 or hp < 0:
        session.logger.warning("Select non-negative pass-frequencies.")
        return

    if (lpd is not None and lpd<0) or (hpd is not None and hpd<0):
        session.logger.warning("Select non-negative decay-frequencies.")
        return

    if threshold<0:
        session.logger.warning("Select a non-negative threshold.")
        return

    unit = unit.lower()
    if unit not in ['pixels', 'angstrom']:
        session.logger.warning("'{}' is not an implemented unit. 'pixels' and 'angstrom' are available.".format(unit))
        return
    if unit == 'angstrom':
        if lpd is not None or hpd is not None:
            session.logger.warning('Cannot set low-pass or high-pass decay when using "angstrom" as a unit. Decay is'
                                   'always set to 0.25/pass-lenght.')
            return

    lp_cutoff = lp_cutoff.lower()
    hp_cutoff = hp_cutoff.lower()
    available = ['gaussian', 'cosine']
    if lp_cutoff not in available or hp_cutoff not in available:
        session.logger.warning(
            "Only 'gaussian' and 'cosine' are available as cutoff methods.".format(lp_cutoff))
        return

    tomo.create_filtered_tomogram(lp, hp, lpd, hpd, threshold, unit, lp_cutoff, hp_cutoff)


def artiax_lock(session, models=None, type=None):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    # No Models
    if models is None:
        models = session.ArtiaX.partlists.child_models()

    # No Type
    if type is None:
        type = 'movement'

    # Type unknown
    if type not in ['translation', 'rotation', 'movement']:
        errors.UserError(
            "artiax lock: '{}' is not a valid argument for artiax lock. Possible values are: 'translation', 'rotation', 'movement'".format(
                type))

    # Filter models
    ms = []
    for model in models:
        # Is it a particle list?
        from ..particle import ParticleList
        if not isinstance(model, ParticleList):
            # Is it a model that likely belongs to a particle list?
            from chimerax.core.models import ancestor_models
            if session.ArtiaX in ancestor_models([model]):
                continue
            else:
                session.logger.warning(
                    'artiax lock: Model #{} - "{}" is not a particle list'.format(model.id_string, model.name))
                continue

        ms.append(model)

    from ..particle.ParticleList import lock_particlelist
    lock_particlelist(models, True, type)


def artiax_unlock(session, models=None, type=None):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    # No Models
    if models is None:
        models = session.ArtiaX.partlists.child_models()

    # No type
    if type is None:
        type = 'movement'

    # Type unknown
    if type not in ['translation', 'rotation', 'movement']:
        errors.UserError(
            "artiax unlock: '{}' is not a valid argument for artiax unlock. Possible values are: 'translation', 'rotation', 'movement'".format(
                type))

    # Filter models
    ms = []
    for model in models:
        # Is it a particle list?
        from ..particle import ParticleList
        if not isinstance(model, ParticleList):
            # Is it a model that likely belongs to a particle list?
            from chimerax.core.models import ancestor_models
            if session.ArtiaX in ancestor_models([model]):
                continue
            else:
                session.logger.warning(
                    'artiax unlock: Model #{} - "{}" is not a particle list'.format(model.id_string, model.name))
                continue

        ms.append(model)

    from ..particle.ParticleList import lock_particlelist
    lock_particlelist(ms, False, type)


def artiax_particles(session,
                     models=None,
                     radius=None,
                     axesSize=None,
                     surfaceLevel=None,
                     color=None,
                     originScaleFactor=None,
                     transScaleFactor=None):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    # No Models
    if models is None:
        models = session.ArtiaX.partlists.child_models()

    set_radius = False
    if radius is not None:
        if radius >= 0.1:
            set_radius = True
        else:
            raise errors.UserError("artiax particles: radius required to be larger than 0.1")

    set_axes_size = False
    if axesSize is not None:
        if axesSize >= 0.1:
            set_axes_size = True
        else:
            raise errors.UserError("artiax particles: axesSize required to be larger than 0.1")

    set_surface_level = False
    if surfaceLevel is not None:
        set_surface_level = True

    set_color = False
    if color is not None:
        set_color = True

    set_ori_scale = False
    if originScaleFactor is not None:
        if originScaleFactor > 0:
            set_ori_scale = True
        else:
            raise errors.UserError("artiax particles: originScaleFactor required to be a positive, non-zero number.")

    set_trans_scale = False
    if transScaleFactor is not None:
        if transScaleFactor > 0:
            set_trans_scale = True
        else:
            raise errors.UserError("artiax particles: transScaleFactor required to be a positive, non-zero number.")

    # Filter models and work
    for model in models:
        # Is it a particle list?
        from ..particle import ParticleList
        if not isinstance(model, ParticleList):  # session.ArtiaX.partlists.has_id(model.id):
            # Is it a model that likely belongs to a particle list?
            from chimerax.core.models import ancestor_models
            if session.ArtiaX in ancestor_models([model]):
                continue
            else:
                session.logger.warning(
                    'artiax particles: Model #{} - "{}" is not a particle list'.format(model.id_string, model.name))
                continue

        if set_radius:
            model.radius = radius

        if set_axes_size:
            model.axes_size = axesSize

        if set_surface_level:
            if model.has_display_model():
                # Clamp by range
                surfaceLevel = min(model.surface_range[1], surfaceLevel)
                surfaceLevel = max(model.surface_range[0], surfaceLevel)

                model.surface_level = surfaceLevel
            else:
                raise errors.UserError('artiax particles: Model #{} - "{}" does not have a surface attached to '
                                       'it.'.format(model.id_string, model.name))

        if set_color:
            model.color = color.uint8x4()

        if set_ori_scale:
            model.origin_pixelsize = originScaleFactor

        if set_trans_scale:
            model.translation_pixelsize = transScaleFactor


def artiax_tomo(session,
                model,
                contrastCenter=None,
                contrastWidth=None,
                slice=None,
                endSlice=None,
                slicePerFrame=None,
                sliceDirection=None,
                pixelSize=None):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    # No Models
    if model is None:
        raise errors.UserError('artiax tomo: A model needs to be specified.')

    # Model not Tomo
    from ..volume import Tomogram
    if not isinstance(model, Tomogram):
        raise errors.UserError('artiax tomo: Specified model needs to be of type Tomogram, not {}.'.format(type(model)))

    if contrastCenter is not None:
        # Clamp to range
        contrastCenter = min(contrastCenter, model.max)
        contrastCenter = max(contrastCenter, model.min)
        model.contrast_center = contrastCenter

    if contrastWidth is not None:
        # Clamp to range
        contrastWidth = min(contrastWidth, model.range)
        contrastWidth = max(contrastWidth, 0)
        model.contrast_width = contrastWidth

    if sliceDirection is not None:
        model.normal = sliceDirection
        if slice is None:
            slice = model.slab_count / 2 + 1

    if slice is not None:
        # Clamp to range
        slice = min(slice, model.slab_count - 1)
        slice = max(slice, 0)
        model.integer_slab_position = round(slice)

        spf = 1
        if slicePerFrame is not None:
            spf = slicePerFrame

        if endSlice is not None:
            endSlice = min(endSlice, model.slab_count - 1)
            endSlice = max(endSlice, 0)
            endSlice = round(endSlice)

            for i in range(slice, endSlice+1, spf):
                model.integer_slab_position = round(i)
                session.update_loop.draw_new_frame()

    if pixelSize is not None:
        if pixelSize <= 0:
            raise errors.UserError('artiax tomo: pixelSize needs to be positive and non-zero.')
        model.pixelsize = pixelSize
        model.integer_slab_position = model.slab_count / 2 + 1
        run(session, 'artiax view xy')


def artiax_colormap(session, model, attribute, palette=None, minValue=None, maxValue=None, transparency=None):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    # No Model
    if model is None:
        raise errors.UserError('artiax colormap: A model needs to be specified.')

    # Model not partlist
    from ..particle import ParticleList
    if not isinstance(model, ParticleList):
        raise errors.UserError('artiax colormap: Model #{} - "{}" is not a particle list model.'.format(model.id_string,
                                                                                                        model.name))
    # No Attribute
    if attribute is None:
        raise errors.UserError('artiax colormap: An attribute needs to be specified.')

    # Attribute unknown
    if attribute not in model.get_all_attributes():
        raise errors.UserError('artiax colormap: Attribute {} unknown for particle list #{} - {}.'.format(attribute,
                                                                                                          model.id_string,
                                                                                                          model.name))

    # No palette
    if palette is None:
        palette = 'redgreen'

    # Palette unknown
    # from chimerax.core.colors import BuiltinColormaps
    custom_palettes = list(session.user_colormaps.keys())
    # builtin_palettes = list(BuiltinColormaps.keys())
    if palette not in custom_palettes:  # and palette not in builtin_palettes:
        raise errors.UserError('artiax colormap: Palette {} is not a known custom palette. Check available palettes '
                               'using "palette list".'.format(palette))

    # Clamp min max
    if minValue is None:
        minValue = model.get_attribute_min([attribute])[0]
    else:
        minValue = max(minValue, model.get_attribute_min([attribute]))

    if maxValue is None:
        maxValue = model.get_attribute_max([attribute])[0]
    else:
        maxValue = min(maxValue, model.get_attribute_max([attribute]))

    # Transparency
    if transparency is None:
        transparency = 0

    if transparency < 0 or transparency > 100:
        raise errors.UserError('artiax colormap: transparency needs to be within range 0-100')

    session.ArtiaX.color_particles_byattribute(model.id,
                                               palette,
                                               attribute,
                                               minValue,
                                               maxValue,
                                               transparency,
                                               log=False)


def artiax_label(session, model, attribute, height=None, offset=None):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    # No Model
    if model is None:
        raise errors.UserError('artiax label: A model needs to be specified.')

    # Model not partlist
    from ..particle import ParticleList
    if not isinstance(model, ParticleList):
        raise errors.UserError(
            'artiax label: Model #{} - "{}" is not a particle list model.'.format(model.id_string,
                                                                                  model.name))
    # No Attribute
    if attribute is None:
        raise errors.UserError('artiax label: An attribute needs to be specified.')

    # Attribute unknown
    if attribute not in model.get_all_attributes():
        raise errors.UserError('artiax label: Attribute {} unknown for particle list #{} - {}.'.format(attribute,
                                                                                                       model.id_string,
                                                                                                       model.name))
    if height is None:
        height = model.radius * 2

    if offset is None:
        offset = [model.radius, model.radius, model.radius]

    run(session, 'label #{} atoms attribute {} height {} offset {},{},{}'.format(model.id_string,
                                                                                 attribute,
                                                                                 height,
                                                                                 offset[0], offset[1], offset[2]),
        log=False)


def artiax_info(session, model):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    # No Model
    if model is None:
        raise errors.UserError('artiax info: A model needs to be specified.')

    # Model type
    from ..particle import ParticleList
    if isinstance(model, ParticleList):
        _id = model.id_string
        plist = model.name
        ty = str(type(model.data)).split('.')[-1].strip('>').strip("'")
        num = model.size
        attrs = model.get_main_attributes()
        info = model.get_attribute_info(attrs)

        pso = model.origin_pixelsize
        pst = model.translation_pixelsize

        text = 'Particle List <b>#{} - {}</b><br>' \
               'containing <b>{}</b> particles<br>' \
               'of data type: <b>{}</b><br>' \
               'Displayed particle coordinates scaled by factor: <b>{}</b><br>' \
               'Displayed particle offsets scaled by factor: <b>{}</b>' \
               '<br>' \
               'Particles have <b>{}</b> unique attributes:<br>' \
               '<ol>'.format(_id, plist, num, ty, pso, pst, len(attrs))

        for a in info.keys():
            alias_text = ', '.join(info[a]['alias'])

            if info[a]['pos_attr'] is not None:
                default_text = info[a]['pos_attr']
            else:
                default_text = ''

            attr_text = u'<li> <b>{}</b> ' \
                        u'<ul>' \
                        u'<li> Aliases: <b>{}</b></li>' \
                        u'<li> Is position parameter: <b>{}</b></li>' \
                        u'<li> min: <b>{:.2f}</b> | max <b>{:.2f}</b>  | mean <b>{:.2f}</b>' \
                        u'  | std <b>{:.2f}</b>  | var <b>{:.2f}</b></li>' \
                        u'</ul>'.format(a,
                                        alias_text,
                                        default_text,
                                        info[a]['min'],
                                        info[a]['max'],
                                        info[a]['mean'],
                                        info[a]['std'],
                                        info[a]['var'])

            text += attr_text

        text += '</ol>'
        session.logger.info(text, image=None, is_html=True)

    else:
        raise errors.UserError(
            'artiax info: Model #{} - "{}" is not a particle list or tomogram.'.format(model.id_string,
                                                                                       model.name))


def register_artiax(logger):
    """Register all commands with ChimeraX, and specify expected arguments."""
    from chimerax.core.commands import (
        register,
        CmdDesc,
        StringArg,
        ModelsArg,
        ModelArg,
        IntArg,
        Or,
        EmptyArg,
        FileNameArg,
        FloatArg,
        ColorArg,
        Float3Arg,
        BoolArg,
        AxisArg,
        RepeatOf,
        EnumOf,
        ListOf,
        NoneArg
    )

    def register_artiax_start():
        desc = CmdDesc(
            synopsis='Start the ArtiaX GUI.',
            url='help:user/commands/artiax_start.html'
        )
        register('artiax start', desc, artiax_start)

    def register_artiax_open_tomo():
        desc = CmdDesc(
            required=[("path", FileNameArg)],
            synopsis='Open a tomogram in ArtiaX.',
            url='help:user/commands/artiax_open_tomo.html'
        )
        register('artiax open tomo', desc, artiax_open_tomo)

    def register_artiax_add_tomo():
        desc = CmdDesc(
            required=[("models", ModelsArg)],
            synopsis='Add volumes loaded by ChimeraX to ArtiaX.',
            url='help:user/commands/artiax_add_tomo.html'
        )
        register('artiax add tomo', desc, artiax_add_tomo)

    # def register_artiax_close_tomo():
    #     desc = CmdDesc(
    #         required=[("models", ModelsArg)],
    #         synopsis='Close a tomogram currently loaded in ArtiaX.',
    #         url='help:user/commands/artiax_close_tomo.html'
    #     )
    #     register('artiax close tomo', desc, artiax_close_tomo)

    def register_artiax_view():
        desc = CmdDesc(
            optional=[("direction", StringArg)],
            synopsis='Set standard viewing directions.',
            url='help:user/commands/artiax_view.html'
        )
        register('artiax view', desc, artiax_view)

    # def register_artiax_open_particlelist():
    #     desc = CmdDesc(
    #         required=[("path", FileNameArg),
    #                   ("format", StringArg)],
    #         synopsis='Open a particle list in ArtiaX.',
    #         url='help:user/commands/artiax_open_particles.html'
    #     )
    #     register('artiax open particles', desc, artiax_open_particlelist)
    #
    # def register_artiax_save_particlelist():
    #     desc = CmdDesc(
    #         required=[("index", IntArg),
    #                   ("path", FileNameArg),
    #                   ("format", StringArg)],
    #         synopsis='Open a particle list in ArtiaX.',
    #         url='help:user/commands/artiax_save_particles.html'
    #     )
    #     register('artiax save particles', desc, artiax_save_particlelist)

    def register_artiax_attach():
        desc = CmdDesc(
            required=[("model", ModelArg)],
            keyword=[("toParticleList", ModelArg)],
            synopsis='Set a surface for display at particle positions.',
            url='help:user/commands/artiax_attach.html'
        )
        register('artiax attach', desc, artiax_attach)

    def register_artiax_show():
        desc = CmdDesc(
            optional=[("models", Or(ModelsArg, EmptyArg)),
                      ("style", StringArg)],
            synopsis='Render particles of the specified lists with this style.',
            url='help:user/commands/artiax_show.html'
        )
        register('artiax show', desc, artiax_show)

    def register_artiax_hide():
        desc = CmdDesc(
            optional=[("models", Or(ModelsArg, EmptyArg)),
                      ("style", StringArg)],
            synopsis='Hide particles of the specified lists with this style.',
            url='help:user/commands/artiax_show.html'
        )
        register('artiax hide', desc, artiax_hide)

    def register_artiax_fit_sphere():
        desc = CmdDesc(
            synopsis='Create a geometric model sphere to the currently selected particles.',
            url='help:user/commands/artiax_fit_sphere.html'
        )
        register('artiax fit sphere', desc, artiax_fit_sphere)

    def register_artiax_fit_line():
        desc = CmdDesc(
            synopsis='Create a geometric model line that goes through the selected particles.',
            url='help:user/commands/artiax_fit_line.html'
        )
        register('artiax fit line', desc, artiax_fit_line)

    def register_artiax_fit_surface():
        desc = CmdDesc(
            synopsis='Create a geometric model surface that goes through the selected particles.',
            url='help:user/commands/artiax_fit_surface.html'
        )
        register('artiax fit surface', desc, artiax_fit_surface)

    def register_artiax_triangulate():
        desc = CmdDesc(
            keyword=[("furthestSite", BoolArg)],
            synopsis='Triangulates all selected particles using links.',
            url='help:user/commands/artiax_triangulate.html'
        )
        register('artiax triangulate', desc, artiax_triangulate)

    def register_artiax_boundary():
        desc = CmdDesc(
            synopsis='Creates a boundary around the selected particles.',
            url='help:user/commands/artiax_boundary.html'
        )
        register('artiax boundary', desc, artiax_boundary)

    def register_artiax_mask():
        desc = CmdDesc(
            synopsis='Creates a mask from the selected geometric model.',
            url='help:user/commands/artiax_mask.html'
        )
        register('artiax mask', desc, artiax_mask)

    def register_artiax_remove_links():
        desc = CmdDesc(
            synopsis='Removes links from selected particles',
            url='help:user/commands/artiax_remove_links.html'
        )
        register('artiax remove links', desc, artiax_remove_links)

    def register_artiax_triangles_from_links():
        desc = CmdDesc(
            synopsis='Creates a triangle surface between all particles marked by links. Useful together with artiax '
                     'triangulate.',
            url='help:user/commands/artiax_triangles_from_links.html'
        )
        register('artiax triangles from links', desc, artiax_triangles_from_links)

    def register_artiax_flip():
        desc = CmdDesc(
            optional=[('axis', AxisArg)],
            synopsis='Rotates the selected particles 180 degrees around their y-axis.',
            url='help:user/commands/artiax_flip.html'
        )
        register('artiax flip', desc, artiax_flip)

    def register_select_inside_surface():
        desc = CmdDesc(
            synopsis='Selects all shown particles inside the selected surface.',
            url='help:user/commands/artiax_select_inside_surface.html'
        )
        register('artiax select inside surface', desc, artiax_select_inside_surface)

    def register_artiax_geomodel_color():
        desc = CmdDesc(
            required=[("model", ModelArg), ("color", ColorArg)],
            synopsis='Set geomodel color.',
            url='help:user/commands/artiax_geomodel_color.html'
        )
        register('artiax geomodel color', desc, artiax_geomodel_color)

    def register_artiax_move_camera_along_line():
        desc = CmdDesc(
            required=[("model", ModelArg)],
            keyword=[("numFrames", IntArg),
                     ("backwards", BoolArg),
                     ("distanceBehind", FloatArg),
                     ("topRotation", FloatArg),
                     ("facingRotation", FloatArg),
                     ('cameraRotation', FloatArg),
                     ('monoCamera', BoolArg),
                     ('maxAngle', Or(FloatArg, NoneArg))],
            synopsis='Moves the camera along the specified line.'
        )
        register('artiax moveCameraAlongLine', desc, artiax_move_camera_along_line)

    def register_artiax_remove_overlap():
        desc = CmdDesc(
            optional=[("models", ListOf(ModelArg))],
            keyword=[("manifold", RepeatOf(ListOf(ModelArg, 2, 2))),
                     ("boundary", RepeatOf(ListOf(ModelArg, 2, 2))),
                     ("freeze", ListOf(ModelArg)),
                     ("method", EnumOf(("volume", "distance"))),
                     ("iterations", IntArg),
                     ("thoroughness", IntArg),
                     ("precision", FloatArg),
                     ("maxSearchDistance", FloatArg)],
            synopsis='Moves selected particles to remove overlap. Can be made to move particles along surface or inside'
                     ' surface.'
        )
        register('artiax remove overlap', desc, artiax_remove_overlap)

    def register_artiax_gen_in_surface():
        desc = CmdDesc(
            required=[("model", ModelArg),
                      ("method", EnumOf(("poisson", "uniform", "regular grid")))],
            keyword=[("num_pts", IntArg),
                     ("radius", FloatArg),
                     ('exactNum', BoolArg)],
            synopsis='Generates points in the specified surface. Can generate points using uniform sampling, '
                     'a poisson disk sampling method, or on a regular grid.'
        )
        register('artiax gen in surface', desc, artiax_gen_in_surface)

    def register_artiax_gen_on_surface():
        desc = CmdDesc(
            required=[("model", ModelArg),
                      ("method", EnumOf(("poisson", "uniform"))),
                      ("num_pts", IntArg)],
            keyword=[("radius", FloatArg),
                     ('exactNum', BoolArg)],
            synopsis='Generates points on the specified surface. Can generate points using uniform sampling, '
                     'a poisson disk sampling method.'
        )
        register('artiax gen on surface', desc, artiax_gen_on_surface)

    def register_artiax_geomodel_to_volume():
        desc = CmdDesc(
            optional=[("model", ModelArg)],
            keyword=[("geomodels", ListOf(ModelArg)),
                     ("subdivide_length", FloatArg)],
            synopsis='Adds the specified geomodels to the specified volume. If no model is specified, a new one is'
                     ' created. If no geomodels are specified, all shown are used. The subdivide_length keyword sets'
                     ' the largest allowed triangle length, and defaults to the tomograms smallest pixelsize.'
        )
        register('artiax geo2vol', desc, artiax_geomodel_to_volume)

    def register_artiax_masked_triangles_to_geomodel():
        desc = CmdDesc(
            optional=[("models", ListOf(ModelArg))],
            keyword=[("name", StringArg)],
            synopsis='Creates a new geomodel from the specified models. Only uses the masked triangles. If no model is'
                     'specified, the currently selected models are used.'
        )
        register('artiax vol2geo', desc, artiax_masked_triangles_to_geomodel)

    def register_artiax_mask_triangles_radius():
        desc = CmdDesc(
            optional=[("radius", FloatArg)],
            synopsis='Enables the "mask connected triangles" mouse mode with a specified radius, such that pressing a '
                     'triangle only masks connected triangles within the radius of the pressed one.'
        )
        register('artiax mask triangle radius', desc, artiax_mask_triangles_radius)

    def register_artiax_filter_tomo():
        desc = CmdDesc(
            required=[("tomo", ModelArg),
                      ('lp', FloatArg),
                      ('hp', FloatArg)],
            keyword=[("lpd", Or(FloatArg, NoneArg)),
                     ('hpd', Or(FloatArg, NoneArg)),
                     ('unit', StringArg),
                     ('lp_cutoff', EnumOf(('gaussian', 'cosine'))),
                     ('hp_cutoff', EnumOf(('gaussian', 'cosine'))),
                     ('threshold', FloatArg)],
            synopsis='Creates a filtered tomogram using lp and hp as lowpass and highpass frequencies, respectively.'
                     'Input 0 as pass-frequency for no low/high-pass.'
                     'lpd and hpd represents the decays, which default to a a fourth of the respective pass-frequencies'
                     'if left empty. Input 0 for a box filter. '
                     'Available units are "hz" and "pixels". The threshold keywords selects how far the '
                     'gaussian curve extends in the filter.'
        )
        register('artiax filter', desc, artiax_filter_tomo)

    def register_artiax_lock():
        desc = CmdDesc(
            optional=[("models", Or(ModelsArg, EmptyArg)),
                      ("type", StringArg)],
            synopsis='Prevent types of movement for these particle lists.',
            url='help:user/commands/artiax_lock.html'
        )
        register('artiax lock', desc, artiax_lock)

    def register_artiax_unlock():
        desc = CmdDesc(
            optional=[("models", Or(ModelsArg, EmptyArg)),
                      ("type", StringArg)],
            synopsis='Allow types of movement for these particle lists.',
            url='help:user/commands/artiax_lock.html'
        )
        register('artiax unlock', desc, artiax_unlock)

    def register_artiax_particles():
        desc = CmdDesc(
            optional=[("models", Or(ModelsArg, EmptyArg))],
            keyword=[("radius", FloatArg),
                     ("axesSize", FloatArg),
                     ("surfaceLevel", FloatArg),
                     ("color", ColorArg),
                     ("originScaleFactor", FloatArg),
                     ("transScaleFactor", FloatArg)],
            synopsis='Set particle list properties.',
            url='help:user/commands/artiax_particles.html'
        )
        register('artiax particles', desc, artiax_particles)

    def register_artiax_tomo():
        desc = CmdDesc(
            required=[("model", ModelArg)],
            keyword=[("contrastCenter", FloatArg),
                     ("contrastWidth", FloatArg),
                     ("slice", IntArg),
                     ("endSlice", IntArg),
                     ("slicePerFrame", IntArg),
                     ('sliceDirection', Float3Arg),
                     ('pixelSize', FloatArg)],
            synopsis='Set tomogram properties.',
            url='help:user/commands/artiax_tomo.html'
        )
        register('artiax tomo', desc, artiax_tomo)

    def register_artiax_colormap():
        desc = CmdDesc(
            required=[("model", ModelArg),
                      ("attribute", StringArg)],
            keyword=[("palette", StringArg),
                     ("minValue", FloatArg),
                     ('maxValue', FloatArg),
                     ('transparency', FloatArg)],
            synopsis='Color particles by attribute.',
            url='help:user/commands/artiax_colormap.html'
        )
        register('artiax colormap', desc, artiax_colormap)

    def register_artiax_label():
        desc = CmdDesc(
            required=[("model", ModelArg),
                      ("attribute", StringArg)],
            keyword=[("height", FloatArg),
                     ("offset", Float3Arg)],
            synopsis='Label particles with attribute.',
            url='help:user/commands/artiax_label.html'
        )
        register('artiax label', desc, artiax_label)

    def register_artiax_info():
        desc = CmdDesc(
            required=[("model", ModelArg)],
            synopsis='Print information about tomograms or particle lists.',
            url='help:user/commands/artiax_info.html'
        )
        register('artiax info', desc, artiax_info)

    register_artiax_start()
    register_artiax_open_tomo()
    register_artiax_add_tomo()
    # register_artiax_close_tomo()
    register_artiax_view()
    # register_artiax_open_particlelist()
    # register_artiax_save_particlelist()
    register_artiax_attach()
    register_artiax_show()
    register_artiax_hide()
    register_artiax_lock()
    register_artiax_unlock()
    register_artiax_particles()
    register_artiax_fit_sphere()
    register_artiax_fit_line()
    register_artiax_fit_surface()
    register_artiax_triangulate()
    register_artiax_boundary()
    register_artiax_mask()
    register_select_inside_surface()
    register_artiax_remove_links()
    register_artiax_triangles_from_links()
    register_artiax_flip()
    register_artiax_geomodel_color()
    register_artiax_move_camera_along_line()
    register_artiax_remove_overlap()
    register_artiax_gen_in_surface()
    register_artiax_gen_on_surface()
    register_artiax_geomodel_to_volume()
    register_artiax_masked_triangles_to_geomodel()
    register_artiax_mask_triangles_radius()
    register_artiax_filter_tomo()
    register_artiax_tomo()
    register_artiax_colormap()
    register_artiax_label()
    register_artiax_info()


# Possible styles
# for pl in models:
#     if style.lower() in ['m', 'mark', 'marker', 'markers']:
#         pl.show_markers(do_show)
#
#     if style.lower() in ['s', 'surf', 'surface', 'surfaces']:
#         pl.show_surfaces(do_show)
#
#     if style.lower() in ['ax', 'axis', 'axes']:
#         pl.show_axes(do_show)
