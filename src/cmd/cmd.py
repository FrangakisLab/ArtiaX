# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
import math

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
    return tools.get_singleton(session, ArtiaXUI, 'ArtiaX', create=create)

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

def artiax_add_tomo(session, model=None):
    """Add a tomogram already open in ChimeraX."""
    if model is None:
        raise errors.UserError("artiax add tomo: No model specified.")

    if not isinstance(model, Volume):
        raise errors.UserError("artiax add tomo: Cannot import data of type {} to ArtiaX as a tomogram.".format(type(model)))

    get_singleton(session)
    session.ArtiaX.import_tomogram(model)

def artiax_close_tomo(session, index):
    """Close a tomogram by internal ID."""
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so no tomograms can be closed.")
        return

    #if index < 1 or index > session.ArtiaX.tomo_count:
    #    raise errors.UserError("artiax close tomo: Requested index {} is outside range 1 to {}".format(index, session.ArtiaX.tomo_count))

    get_singleton(session)
    session.ArtiaX.close_tomogram(index-1)

def artiax_view(session, direction):
    """Set the current camera position to one of the perpendicular views."""
    directions = {
        'xy': view_xy,
        'zx': view_zx,
        'yz': view_yz
    }

    if direction not in directions.keys():
        raise errors.UserError("{} is not a viewing direction known to ArtiaX.".format(direction))

    directions[direction.lower()](session)

def artiax_open_particlelist(session, path, format):
    """Open a particle list in ArtiaX"""
    get_singleton(session)
    session.ArtiaX.open_partlist(path, format)

def artiax_save_particlelist(session, index, path, format):
    """Save a particle list in specified format."""
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so no lists can be saved.")
        return

    if index < 1 or index > session.ArtiaX.partlist_count:
        raise errors.UserError("artiax save particles: Requested index {} is outside range 1 to {}".format(index, session.ArtiaX.partlist_count))

    session.ArtiaX.save_partlist(index-1, path, format)

def artiax_particles_attach(session, index, model):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so nothing can be attached.")
        return

    if index < 1 or index > session.ArtiaX.partlist_count:
        raise errors.UserError("artiax particles attach: Requested index {} is outside range 1 to {}".format(index, session.ArtiaX.partlist_count))

    session.ArtiaX.attach_display_model(index-1, model)

def artiax_show(session, models=None, style=None):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so nothing can be shown.")
        return

    from ..util.view import show
    show(session, models, style)


def artiax_hide(session, models=None, style=None):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so nothing can be shown.")
        return

    from ..util.view import show
    show(session, models, style, do_show=False)

def artiax_fit_sphere(session):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running, so no sphere can be fitted.")
        return

    # TODO Move this stuff to appropriate places

    # Find selected particles
    particle_pos = np.zeros((0, 3))  # each row is one currently selected particle, with columns being x,y,z
    for particlelist in session.ArtiaX.partlists.child_models():
        for curr_id in particlelist.particle_ids[particlelist.selected_particles]:
            if curr_id:
                x_pos = particlelist.get_particle(curr_id)['pos_x']\
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

    A = np.append(2 * particle_pos, np.ones((len(particle_pos),1)), axis=1)
    x = np.sum(particle_pos**2, axis=1)
    b, residules, rank, singval = np.linalg.lstsq(A, x)
    r = math.sqrt(b[3] + b[0]**2 + b[1]**2 + b[2]**2)

    # Reorient selected particles so that Z-axis points towards center of sphere
    # for particlelist in session.ArtiaX.partlists.child_models():
    #     for curr_id in particlelist.particle_ids[particlelist.selected_particles]:
    #         if curr_id:
    #             particlelist.get_particle(curr_id).

    # TODO remove
    print(b[0],b[1],b[2],r)

    from ..geometricmodel import GeoModel
    geomodel = GeoModel("sphere", session, b[:3], r)
    session.ArtiaX.geomodels.add([geomodel])

def artiax_lock(session, models=None, type=None):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    if models is None:
        models = session.ArtiaX.partlists.child_models()

    if type is None:
        type = 'movement'

    if type not in ['translation', 'rotation', 'movement']:
        errors.UserError("'{}' is not a valid argument for artiax lock. Possible values are: 'translation', 'rotation', 'movement'".format(type))

    from ..particle.ParticleList import lock_particlelist
    lock_particlelist(models, True, type)


def artiax_unlock(session, models=None, type=None):
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    if models is None:
        models = session.ArtiaX.partlists.child_models()

    if type is None:
        type = 'movement'

    if type not in ['translation', 'rotation', 'movement']:
        errors.UserError(
            "'{}' is not a valid argument for artiax unlock. Possible values are: 'translation', 'rotation', 'movement'".format(type))

    from ..particle.ParticleList import lock_particlelist
    lock_particlelist(models, False, type)


def register_artiax(logger):
    from chimerax.core.commands import (
        register, CmdDesc, StringArg, ModelsArg, ModelArg, IntArg, Or, EmptyArg, FileNameArg)

    def register_artiax_start():
        desc = CmdDesc(
            synopsis= 'Start the ArtiaX GUI.',
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
            required=[("model", ModelArg)],
            synopsis='Add a volume loaded by ChimeraX to ArtiaX.',
            url='help:user/commands/artiax_add_tomo.html'
        )
        register('artiax add tomo', desc, artiax_add_tomo)

    def register_artiax_close_tomo():
        desc = CmdDesc(
            required=[("index", IntArg)],
            synopsis='Close a tomogram currently loaded in ArtiaX.',
            url='help:user/commands/artiax_close_tomo.html'
        )
        register('artiax close tomo', desc, artiax_close_tomo)

    def register_artiax_view():
        desc = CmdDesc(
            required=[("direction", StringArg)],
            synopsis='Set standard viewing directions.',
            url='help:user/commands/artiax_view.html'
        )
        register('artiax view', desc, artiax_view)

    def register_artiax_open_particlelist():
        desc = CmdDesc(
            required=[("path", FileNameArg),
                      ("format", StringArg)],
            synopsis='Open a particle list in ArtiaX.',
            url='help:user/commands/artiax_open_particles.html'
        )
        register('artiax open particles', desc, artiax_open_particlelist)

    def register_artiax_save_particlelist():
        desc = CmdDesc(
            required=[("index", IntArg),
                      ("path", FileNameArg),
                      ("format", StringArg)],
            synopsis='Open a particle list in ArtiaX.',
            url='help:user/commands/artiax_save_particles.html'
        )
        register('artiax save particles', desc, artiax_save_particlelist)

    def register_artiax_particles_attach():
        desc = CmdDesc(
            required=[("index", IntArg),
                      ("model", ModelArg)],
            synopsis='Open a particle list in ArtiaX.',
            url='help:user/commands/artiax_particles_attach.html'
        )
        register('artiax particles attach', desc, artiax_particles_attach)

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
            #TODO rewrite and get url right
            synopsis='Create a geometric model sphere to the currently selected particles.',
            url='help:user/commands/artiax_hide.html'
        )
        register('artiax fit sphere', desc, artiax_fit_sphere)

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

    register_artiax_start()
    register_artiax_open_tomo()
    register_artiax_add_tomo()
    register_artiax_close_tomo()
    register_artiax_view()
    register_artiax_open_particlelist()
    register_artiax_save_particlelist()
    register_artiax_particles_attach()
    register_artiax_show()
    register_artiax_hide()
    register_artiax_lock()
    register_artiax_unlock()
    register_artiax_fit_sphere()

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

