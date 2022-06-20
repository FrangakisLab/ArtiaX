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


def artiax_add_tomo(session, models=None):
    """Add a tomogram already open in ChimeraX."""
    # No Model
    if models is None:
        session.logger.warning("artiax add tomo: No model specified.")
        return

    # Filter by class
    ms = []
    for model in models:
        if not isinstance(model, Volume):
            session.logger.warning("artiax add tomo: Cannot import data of type {} to ArtiaX as a tomogram.".format(type(model)))
            continue

        ms.append(model)

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
        raise errors.UserError("artiax attach: cannot attach a Tomogram as a particle list surface.".format(type(model)))

    # Not a Particle list
    if not session.ArtiaX.partlists.has_id(toParticleList.id):
        session.logger.warning(
            'artiax attach: Model #{} - "{}" is not managed by ArtiaX'.format(toParticleList.id_string, toParticleList.name))
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

    from ..geometricmodel.GeoModel import fit_line
    fit_line(session)


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
        errors.UserError("artiax lock: '{}' is not a valid argument for artiax lock. Possible values are: 'translation', 'rotation', 'movement'".format(type))

    # Filter models
    ms = []
    for model in models:
        if not session.ArtiaX.partlists.has_id(model.id):
            session.logger.warning(
                'artiax lock: Model #{} - "{}" is not managed by ArtiaX'.format(model.id_string, model.name))
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
            "artiax unlock: '{}' is not a valid argument for artiax unlock. Possible values are: 'translation', 'rotation', 'movement'".format(type))

    # Filter models
    ms = []
    for model in models:
        if not session.ArtiaX.partlists.has_id(model.id):
            session.logger.warning(
                'artiax unlock: Model #{} - "{}" is not managed by ArtiaX'.format(model.id_string, model.name))
            continue

        ms.append(model)

    from ..particle.ParticleList import lock_particlelist
    lock_particlelist(ms, False, type)

def artiax_particles(session, models=None, radius=None, axes_size=None, surface_level=None, color=None):
    # No ArtiaX
    if not hasattr(session, 'ArtiaX'):
        session.logger.warning("ArtiaX is not currently running.")
        return

    # No Models
    if models is None:
        models = session.ArtiaX.partlists.child_models()

    set_radius = False
    if radius is not None:
        set_radius = True

    set_axes_size = False
    if axes_size is not None:
        set_axes_size = True

    set_surface_level = False
    if surface_level is not None:
        set_surface_level = True

    set_color = False
    if color is not None:
        set_color = True

    # Filter models and work
    for model in models:
        if not session.ArtiaX.partlists.has_id(model.id):
            session.logger.warning(
                'artiax particles: Model #{} - "{}" is not managed by ArtiaX'.format(model.id_string, model.name))
            continue

        if set_radius:
            model.radius = radius

        if set_axes_size:
            model.axes_size = axes_size

        if set_surface_level:
            model.surface_level = surface_level

        if set_color:
            model.color = color


def register_artiax(logger):
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
        ColorArg
    )

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

    def register_artiax_attach():
        desc = CmdDesc(
            required=[("model", ModelArg),
                      ("toParticleList", ModelArg)],
            synopsis='Set a surface for display at particle positions.',
            url='help:user/commands/artiax_particles_attach.html'
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
            #TODO rewrite and get url right
            synopsis='Create a geometric model sphere to the currently selected particles.',
            url='help:user/commands/artiax_hide.html'
        )
        register('artiax fit sphere', desc, artiax_fit_sphere)

    def register_artiax_fit_line():
        desc = CmdDesc(
            #TODO rewrite and get url right
            synopsis='Create a geometric model line between two selected particles.',
            url='help:user/commands/artiax_hide.html'
        )
        register('artiax fit line', desc, artiax_fit_line)

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
            optional=[("models", Or(ModelsArg, EmptyArg)),
                      ("radius", FloatArg),
                      ("axesSize", FloatArg),
                      ("surfaceLevel", FloatArg),
                      ("color", ColorArg)],
            synopsis='Set particle list properties.',
            url='help:user/commands/artiax_particles.html'
        )
        register('artiax particles', desc, artiax_particles)

    register_artiax_start()
    register_artiax_open_tomo()
    register_artiax_add_tomo()
    # register_artiax_close_tomo()
    register_artiax_view()
    register_artiax_open_particlelist()
    register_artiax_save_particlelist()
    register_artiax_attach()
    register_artiax_show()
    register_artiax_hide()
    register_artiax_lock()
    register_artiax_unlock()
    register_artiax_particles()
    register_artiax_fit_sphere()
    register_artiax_fit_line()

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

