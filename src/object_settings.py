"""
This script defines classes that either include the settings of
a tomogram or a motivelist
"""

import sys
import numpy as np
import mrcfile
import math as ma

from .emwrite import emwrite
from .emread import emread
from .euler_rotation import detRotMat, detInvRotMat, mulMatMat, mulVecMat, getEulerAngles, updateCoordinateSystem, rotateArray

from chimerax.core.commands import run, Command
from chimerax.map.volume import volume_from_grid_data
from chimerax.map_data import ArrayGridData
from chimerax.map import Volume
from chimerax.markers import MarkerSet, selected_markers

class TomoInstance:
    def __init__(self, name, row, index, id):
        # Whenever a new tomo instance is created set the name, and the
        # corresponding row of the table
        self.name = name
        self.table_row = row
        self.list_index = index
        self.id_string = id                # ID is stored as a string for convenience

        # The ChimeraX Volume instance
        self.volume = None

        # Set the default filepath
        self.filepath = None

        # Set the QCheckBox states for reference
        self.shown = True       # Shown by default
        self.options = False   # options selected by default

        # Set some default dimensions
        self.x_dim = 0
        self.y_dim = 0
        self.z_dim = 0

        # Set minimum and maximum of data
        self.data_min = 0
        self.data_max = 0

        # Define a couple of values that are the settings of the options window
        # In order to recreate the latest settings in case this window gets closed
        # And then opened again
        self.use_save_settings = False  # Switches to True as soon as options window for this tomogram has been built once
        self.center_position = 0
        self.width_position = 0
        self.slice_position = 0

    def set_tomo(self, tomo_instance):
        self.volume = tomo_instance

    def set_filepath(self, filepath):
        self.filepath = filepath

    def set_dimensions(self, dimensions):
        self.x_dim = dimensions[0]
        self.y_dim = dimensions[1]
        self.z_dim = dimensions[2]

    def set_min_max(self, values):
        self.data_min = values[0]
        self.data_max = values[1]

    def set_default_positions(self, values):
        self.center_position = values[0]    # As default use surface level
        self.width_position = values[1]     # Use 20% of range as default
        self.slice_position = values[2]     # Use middle of stack as default



class MotlInstance:
    def __init__(self, name, row, index):
        # Whenever a new motl instance is created set the name and the
        # Corresponding row of the table
        self.name = name
        self.table_row = row
        self.list_index = index
        self.obj_name = None    # Is set with a function

        # Initialize the motivelist as an empty list
        self.motivelist = []

        # Define an empty row which is included when a new object/marker is added
        self.empty_row = [0]*22         # empty row with 22 entries -> Last two entries won't be saved
                                        # 21st entry is the ChimeraX marker/volume instance
                                        # 22nd entry is the ChimeraX ID which needs to be a string

        # Set the selection status which is False by default
        self.selected = False       # Not selected by default
        self.shown = True           # Shown by default
        self.view = False        # No options selected by default
        self.edit = False        # No options selected by default

        # Initialize the surface levels - are set by a function
        self.surface_min = None
        self.surface_max = None
        self.surface_current = None

        # It is also useful to save the filepath of motivelist and object
        self.motl_filepath = None
        self.obj_filepath = None

        # Define a couple of values that are the settings of the options window
        # In order to recreate the latest settings in case this window gets closed
        # And then opened again
        self.selection_position = 0
        self.row1_position = 0
        self.row2_position = 0
        self.radius_position = 4        # Default radius
        self.surface_position = 0

        # When adding a new marker set, the new name plays an important role
        # A New marker set is named as a 4 digit number which represents the
        # Number of marker sets that have been added
        self.marker_set_number = 0

    def set_paths(self, motl_path, obj_path):
        self.motl_filepath = motl_path
        self.obj_filepath = obj_path

    def set_obj_name(self, obj_name):
        self.obj_name = obj_name

    def set_surface_level(self, min, max, current):
        self.surface_min = min
        self.surface_max = max
        self.surface_current = current

    def set_slider_positions(self, positions):
        # self.selection_position = positions[0]
        self.row1_position = positions[1]
        self.row2_position = positions[1]
        self.radius_position = positions[2]
        # The surface position is set as soon as an object is loaded to the
        # Motivelist, which, by this time, should not have happened yet.

    def add_marker(self, marker_instance, id, motl_data=None):
        # Get the number of the marker (not ID)
        marker_number = len(self.motivelist) + 1
        # Create the nametag used to select the marker
        self.marker_set_number += 1

        # Build the marker list to check if a marker is already part of the motivelist
        marker_list = []
        marker_list = [s[20] for s in self.motivelist]

        # Expand the motivelist and also store the positions in it
        for i in range(len(marker_instance)):
            new_row = []
            new_row.extend(self.empty_row)

            # Get the coordinates
            coords = marker_instance[i].coord
            x_coord = coords[0]
            y_coord = coords[1]
            z_coord = coords[2]
            # And store them in the motivelist
            new_row[7] = x_coord
            new_row[8] = y_coord
            new_row[9] = z_coord
            # Fill the other entries with data from loaded motivelist
            if motl_data != None:
                new_row[0] = motl_data[i][0]
                new_row[1] = motl_data[i][1]
                new_row[2] = motl_data[i][2]
                new_row[3] = motl_data[i][3]
                new_row[4] = motl_data[i][4]
                new_row[5] = motl_data[i][5]
                new_row[6] = motl_data[i][6]

                new_row[10] = motl_data[i][10]
                new_row[11] = motl_data[i][11]
                new_row[12] = motl_data[i][12]
                new_row[13] = motl_data[i][13]
                new_row[14] = motl_data[i][14]
                new_row[15] = motl_data[i][15]
                new_row[16] = motl_data[i][16]
                new_row[17] = motl_data[i][17]
                new_row[18] = motl_data[i][18]
                new_row[19] = motl_data[i][19]


            # By default a clicked marker is called M
            # Hence, M is the last element of the marker's name by default
            if str(marker_instance[i])[-1] == "M":
                marker_number = str(marker_instance[i])[8:-2]
            else:   # Else there should be the 4-digit number
                marker_number = str(marker_instance[i])[8:-5]
            if self.marker_set_number < 10:
                marker_name = "000" + str(self.marker_set_number)
            elif self.marker_set_number < 100:
                marker_name = "00" + str(self.marker_set_number)
            elif self.marker_set_number < 1000:
                marker_name = "0" + str(self.marker_set_number)
            elif self.marker_set_number < 10000:
                marker_name = str(self.marker_set_number)
            name = "{}/M:{}@{}".format(id, marker_number, marker_name)
            # Only add the marker if its unique name is not part of the motivelist
            if marker_instance[i] in marker_list:
                print("Skipped because already in motivelist")
            else:
                marker_instance[i].name = marker_name
                new_row[20] = marker_instance[i]
                new_row[21] = name  # Needs to be a string (also for volumes)
                # Add the row to the motivelist
                self.motivelist.append(new_row)

    def add_marker_as_volume(self, session, marker_instance):
        # If this function is executed, the obj filepath should be set
        # So just a quick checkup if that really is the case
        if self.obj_filepath == None:
            print("Error: No path for object set.")
        else:
            # Load the data
            if ".em" in self.obj_filepath:
                # Get the shape of the data
                vol_data = emread(self.obj_filepath)
                dimensions = np.asarray(vol_data.shape)
                voxel_size = [1, 1, 1]  # Which is default by EM file

                # Use the dimensions and the voxel size to determine the origin
                origin = [-ma.floor(dimensions[0]*voxel_size[0]/2)+1,-ma.floor(dimensions[1]*voxel_size[1]/2)+1,-ma.floor(dimensions[2]*voxel_size[2]/2)+1]

                # Change data to a ChimeraX GridData
                data_grid = ArrayGridData(vol_data, origin=origin, step=voxel_size, name=self.obj_name)

            elif ".mrc" in self.obj_filepath:
                # Get the shape and the voxel size of the data and the data itself
                with mrcfile.open(self.obj_filepath) as mrc:
                    dimensions = np.asarray([mrc.header.nx, mrc.header.ny, mrc.header.nz])
                    voxel_size = mrc.voxel_size.copy()
                    vol_data = mrc.data
                # with the dimensions determine the origin, which is the center of the object
                origin = [-ma.floor(dimensions[0]*voxel_size.x/2)+1,-ma.floor(dimensions[1]*voxel_size.y/2)+1,-ma.floor(dimensions[2]*voxel_size.z/2)+1]
                step = np.asarray([voxel_size.x, voxel_size.y, voxel_size.z])

                # Change data to a ChimeraX GridData
                data_grid = ArrayGridData(vol_data, origin=origin, step=step, name=self.obj_name)

            # Go through all markers and add the volume at this position
            for i in range(len(marker_instance)):
                # Create a new particle entry for the motivelist
                new_row = []
                new_row.extend(self.empty_row)

                # Get the coordinates
                coords = marker_instance[i].coord
                x_coord = coords[0]
                y_coord = coords[1]
                z_coord = coords[2]
                # And store them in the motivelist
                new_row[7] = x_coord
                new_row[8] = y_coord
                new_row[9] = z_coord

                # Create the volume from the array grid
                volume_from_grid_data(data_grid, session)

                # Add new volume to the object list in the motl instance
                current_volume = [v for v in session.models.list() if isinstance(v, Volume)][-1]
                # Add surface to the volume with default selected colors
                current_volume.add_surface(self.surface_current, rgba=(0, 1, 1, 1), display=True)


                # Add volume and id to the particle entry
                new_row[20] = current_volume
                new_row[21] = current_volume.id_string

                # Use ChimeraX's view matrix method to rotate and translate
                # For this we need the rotation matrix appanded by the translation vector
                rot_mat = []
                rot_mat.extend(detRotMat(0, 0, 0))
                # Append the translation vector
                rot_mat[0].append(x_coord)
                rot_mat[1].append(y_coord)
                rot_mat[2].append(z_coord)

                # Prepare the string for the command
                command = "view matrix models #{}".format(current_volume.id_string)
                for i in range(3):
                    for j in range(4):
                        command += ",{}".format(rot_mat[i][j])

                run(session, command)
                # Also fix the problem EM files being displayed the wrong way
                run(session, "volume #{} capFaces false".format(current_volume.id_string))

                # Add the row to the motivelist
                self.motivelist.append(new_row)


            # Delete the marker
            marker_set = [set for set in session.models.list() if isinstance(set, MarkerSet)]
            run(session, "close #{}".format(marker_set[0].id_string))
