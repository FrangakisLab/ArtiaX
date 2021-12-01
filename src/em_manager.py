""" A simple short script that manages loading and saving .em files """

from .emread import emread
from .emwrite import emwrite
from chimerax.core.commands import run
from chimerax.map.volume import volume_from_grid_data
from chimerax.map_data import ArrayGridData
from  chimerax.core.models import Model
import os as os
import .map_class as mc

def load_em(session, path, tomo):
    # Load an EM file and show in ChimeraX
    if tomo:
        em_data = -read_em(path)
    else:
        em_data = read_em(path)
    # Get the dimensions
    rows, cols, stacks = len(em_data), len(em_data[0]), len(em_data[0][0])

    # Get the filename
    filename = os.path.basename(path)

    # Store the 3D matrix as a GridData from chimeraX
    grid_data = ArrayGridData(em_data,name=filename)

    # Create a new model
    # em_model = Model(filename, session)
    # em_model.add(volume_from_grid_data(grid_data, session))

    # Now transform to a volume that can be opened in ChimeraX
    volume = volume_from_grid_data(grid_data, session)

    # Print a status message
    status = ("Opened EM file with dimensions X: {} Y: {} Z: {}".format(rows, cols, stacks))
    print(status)

    # run(session, "open ")

# Read the EM data and returns as 3D matrix
def read_em(path):

    em_data = emread(path)

    return em_data

def load_motl(session, path):
    # Load the data of the motl
    motl_data = read_em(path)
    # Get the dimensions
    rows, cols = len(motl_data), len(motl_data[0])

    # Place an object at every position given in the motive list
    for i in range(cols):
