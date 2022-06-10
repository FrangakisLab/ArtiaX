# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
from chimerax.core import errors
from chimerax.map import Volume

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

    if index < 1 or index > session.ArtiaX.tomo_count:
        raise errors.UserError("artiax close tomo: Requested index {} is outside range 1 to {}".format(index, session.ArtiaX.tomo_count))

    get_singleton(session)
    session.ArtiaX.close_tomogram(index-1)

def artiax_view(session, direction):
    """Set the current camera position to one of the perpendicular views."""
    directions = {
        'xy': view_xy,
        'xz': view_xz,
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
            synopsis='Show particles with this style.',
            url='help:user/commands/artiax_show.html'
        )
        register('artiax show', desc, artiax_show)

    def register_artiax_hide():
        desc = CmdDesc(
            optional=[("models", Or(ModelsArg, EmptyArg)),
                      ("style", StringArg)],
            synopsis='Hide this style.',
            url='help:user/commands/artiax_hide.html'
        )
        register('artiax hide', desc, artiax_hide)

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

