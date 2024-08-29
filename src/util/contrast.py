from typing import List

from chimerax.core.session import Session
from chimerax.core.models import Model
from chimerax.core.commands import log_equivalent_command

from ..volume.Tomogram import Tomogram


def invert_contrast(session: Session, models: List[Model], log: bool = False):
    """Invert the contrast of a list of tomograms."""
    for model in models:
        if isinstance(model, Tomogram):
            if model.contrast_mode == "DARK_ON_LIGHT":
                model.contrast_mode = "LIGHT_ON_DARK"
            elif model.contrast_mode == "LIGHT_ON_DARK":
                model.contrast_mode = "DARK_ON_LIGHT"
        else:
            session.logger.warning(f"Cannot invert contrast of {model.name}. Not a Tomogram.")

    if log:
        mnums = ','.join(m.id_string for m in models)
        com = f"artiax invert #{mnums}"
        log_equivalent_command(session, com)
