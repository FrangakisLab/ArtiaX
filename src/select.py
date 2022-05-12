import numpy as np
from chimerax.core.commands import run

def selection_cmd(session, list_id, attributes, minima, maxima):
    markerset = session.ArtiaX.partlists.get(list_id).markers
    markers = markerset.get_all_markers()

    # Attributes not empty, select
    if len(attributes) > 0:
        # Mask for fast execution
        mask = np.full((len(markers),), True)
        # mask[0] = False

        # Build mask
        for idx, m in enumerate(markers):
            for a, mini, maxi in zip(attributes, minima, maxima):
                mask[idx] = mask[idx] and (mini <= getattr(m, a) <= maxi)

        markerset.atoms.selecteds = mask

    # Nothing to select, just clear selection
    else:
        mask = np.full((len(markers),), False)
        markerset.atoms.selecteds = mask


def display_cmd(session, list_id, attributes, minima, maxima):
    markerset = session.ArtiaX.partlists.get(list_id).markers
    markers = markerset.get_all_markers()

    # Attributes not empty, select
    if len(attributes) > 0:
        # Mask for fast execution
        mask = np.full((len(markers),), True)
        # mask[0] = False

        for idx, m in enumerate(markers):
            for a, mini, maxi in zip(attributes, minima, maxima):
                mask[idx] = mask[idx] and (mini <= getattr(m, a) <= maxi)

        markerset.atoms.displays = mask

    # Nothing to select, just show all
    else:
        mask = np.full((len(markers),), True)
        # mask[0] = False
        markerset.atoms.displays = mask

def color_cmd(session, list_id, color):
    pl = session.ArtiaX.partlists.get(list_id)

    # Just one color
    pl.color = color


def colormap_cmd(session, list_id, palette, attribute, minimum, maximum):
    markers = session.ArtiaX.partlists.get(list_id).markers

    run(session,
        'color byattribute a:{} #{} palette {} range {},{}'.format(attribute, markers.id_string, palette, minimum,
                                                                   maximum), log=False)

def _full_spec(id_string, attributes, minima, maxima):
    neg = []
    pos = []

    for a, mini, maxi in zip(attributes, minima, maxima):
        neg.append(_negative_selection(id_string, a, mini, maxi))
        pos.append(_positive_selection(id_string, a, mini, maxi))

    neg_spec = " | ".join(neg)
    pos_spec = " & ".join(pos)

    return neg_spec, pos_spec

def _positive_selection(id_string, attribute, minimum, maximum):
    return "( #{}@@{}>={} & #{}@@{}<={} )".format(id_string, attribute, minimum, id_string, attribute, maximum)

def _negative_selection(id_string, attribute, minimum, maximum):
    return "( #{}@@{}<{} | #{}@@{}>{} )".format(id_string, attribute, minimum, id_string, attribute, maximum)