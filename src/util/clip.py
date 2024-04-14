# vim: set expandtab shiftwidth=4 softtabstop=4:

# Python
from typing import Union

# ChimeraX
from chimerax.core.commands import run
from chimerax.core.models import Model
from chimerax.core.session import Session

# This package
from ..volume import Tomogram


def clip(session: Session, thickness: Union[float, str], model: Model = None, log: bool = True) -> None:
    """
    Turn on/off slab-dependent clipping planes for a tomogram.

    Parameters
    ----------
    session : chimerax.core.session.Session
        ChimeraX session.
    thickness : Union[float, str]
        Thickness of the visible slab in Angstrom. 'off' to turn off clipping. 'toggle' to toggle the clipping on/off.
    model : Optional[chimerax.core.models.Model]
        Tomogram model to clip. If None, the currently displayed tomogram will be used.
    log : bool
        Log the thickness change.

    """
    # Get the ArtiaX session
    artia = session.ArtiaX

    _toggle = False

    # Turn off clipping
    if isinstance(thickness, str):
        if thickness == 'off':
            for t in artia.tomograms.child_models():
                t.is_clipped = False
            run(session, 'clip off', log=False)
            return
        elif thickness == 'toggle':
            thickness = artia.clip_thickness
            _toggle = True
        else:
            session.logger.warning("Thickness must be a number, 'off' or 'toggle'.")
            return

    # Get the model
    if model is None:
        for t in artia.tomograms.child_models():
            if t.display:
                model = t
                break

    # No tomogram found
    if model is None:
        session.logger.warning("No tomogram currently open.")
        return

    # Check if model is a tomogram
    if not isinstance(model, Tomogram):
        session.logger.warning(f"Model #{model.id_string} is not a tomogram.")
        return

    # Turn off clipping for all tomograms
    prev_state = model.is_clipped

    for t in artia.tomograms.child_models():
        t.is_clipped = False

    # Set the thickness
    if _toggle:
        state = not prev_state
    else:
        state = True

    artia.clip_thickness = thickness

    if state:
        model.is_clipped = True
    else:
        model.is_clipped = False
        run(session, 'clip off', log=False)

    # Make sure tomo is visible
    model.display = True
    # Update the model display.
    model.slab_position = model.slab_position

    # Log the thickness
    if log:
        session.logger.info(f"Clipping thickness set to {thickness} A around slabs of #{model.id_string}.",
                            is_html=False, image=None)


def cap(session, do_cap: bool) -> None:
    """
    Turn on/off surface capping for particle lists.

    Parameters
    ----------
    session : chimerax.core.session.Session
        ChimeraX session.
    do_cap : bool
        True or False to turn on/off surface capping.
    """
    # Get the ArtiaX session
    artia = session.ArtiaX

    # Turn off surface capping
    if do_cap:
        for pl in artia.partlists.child_models():
            for d in pl.collection_model.child_drawings():
                d.clip_cap = True
    else:
        for pl in artia.partlists.child_models():
            for d in pl.collection_model.child_drawings():
                d.clip_cap = False

    # Update view
    artia.clip_thickness = artia.clip_thickness

