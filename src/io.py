# vim: set expandtab shiftwidth=4 softtabstop=4:

from chimerax.core.commands import run
from chimerax.map.volume import volume_from_grid_data
from chimerax.map_data import ArrayGridData

def open_em(session, stream):
    """ Read an EM file from a file-line object.

    Returns the 2-tuple return value expected by the "open command" manager's
    :py:meth:'run_provider' method.
    """
    structures = []
    line_number = 0

    # Get the data from the file
    data = read_em(stream)
    # Get the dimensions
    rows, cols, stacks = len(data), len(data[0]), len(data[0][0])

    # Store as GridData
    grid_data = ArrayGridData(data)

    # Store as a volume which can be displayed by ChimeraX
    volume = volume_from_grid_data(grid_data, session)

    # Now prepare a status message
    status = ("Opened EM file with dimensions X: {} Y: {} Z: {}".format(rows, cols, stacks))
    print("Yes, we use this method!")
    return volume, status


def read_em(stream):
    from .emread import emread
    em_data = emread(stream)

    return em_data
