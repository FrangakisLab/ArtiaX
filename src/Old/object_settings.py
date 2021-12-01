"""
This script defines classes that either include the settings of
a tomogram or a motivelist
"""

import sys
import numpy as np

class TomoSettings:
    def __init__(self, name, row):
        self.name = name

        self.tomo_list = []

        # Define the table entries
        self.table_name = name          # Global name of the motivelist
        self.table_show = u""          # Are objects shown (Yes by default)
        self.table_select = u""        # Are objects selected (No by default)
        self.table_row = row

        # For quick access store all IDs in a list
        self.tomo_ids = []

        # Store the file path
        self.filepath = None

        # Dimensions
        self.x_dim = 0
        self.y_dim = 0
        self.z_dim = 0


    def set_tomo_filepath(self, filepath):
        self.filepath = filepath


    def add_tomo(self, volume):
        self.tomo_list.append(volume)

        # Add the ID to the id list for quick access
        self.tomo_ids.append(int(volume.id_string))


    def add_to_table(self, table_row):
        self.table_row = table_row


    def return_tomo_list(self, table_row):
        if table_row == self.table_row:
            return self.tomo_list
        else:
            print("Error: Given row does not match table row.")


    def set_dimensions(self, dimensions):
        self.x_dim = dimensions[0]
        self.y_dim = dimensions[1]
        self.z_dim = dimensions[2]


class MotlSettings:
    def __init__(self, name, row):
        self.name = name
        self.obj_name = None
        self.motivelist = []            # The motivelist in raw and easy accessible form

        # Define an empty row which is included when a new object/marker is added
        self.empty_row = [0]*22         # empty row with 22 entries -> Last two entries won't be saved
                                        # 21st entry is the ChimeraX marker/volume instance
                                        # 22nd entry is the ChimeraX ID which needs to be a string

        # Define the table entries
        self.table_name = name          # Global name of the motivelist
        self.table_object_name = None   # Global name of the objects
        self.table_show = u""          # Are objects shown (Yes by default)
        self.table_select = u""        # Are objects selected (No by default)
        self.table_row = row            # The corresponding row of the table

        # It is also useful to save the filepath of motivelist and object
        self.motl_filepath = None
        self.obj_filepath = None

        # Minimal and maximal value of the object
        self.surface_obj_min = None
        self.surface_obj_max = None
        self.surface_obj_current = None

        # When adding a new marker set, the new name plays an important role
        # A New marker set is named as a 4 digit number which represents the
        # Number of marker sets that have been added
        self.marker_set_number = 0


    def set_min_max(self, min, max, current):
        self.surface_obj_min = min
        self.surface_obj_max = max
        self.surface_obj_current = current


    def add_obj(self, obj_name, dimension, resolution, new_row): # Volume should be a ChimeraX volume/map
        self.obj_name = obj_name

        # Add a new row to the motivelist/Id list
        if new_row:
            self.motivelist.append(self.empty_row)

        # Get dimensions and resolution
        self.dimension = dimension
        self.resolution = resolution


    def add_marker(self, marker_instance, id):
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
            name = "#{}/M:{}@{}".format(id, marker_number, marker_name)
            # Only add the marker if its unique name is not part of the motivelist
            if marker_instance[i] in marker_list:
                print("Skipped because already in motivelist")
            else:
                marker_instance[i].name = marker_name
                new_row[20] = marker_instance[i]
                new_row[21] = name  # Needs to be a string (also for volumes)
                # Add the row to the motivelist
                self.motivelist.append(new_row)


    def add_to_table(self, table_row):
        self.table_row = table_row


    def return_both_lists(self, table_row):
        if table_row == self.table_row:
            return self.obj_list, self.marker_list


    def update_object(self, id, position_matrix): # ID should be the ChimeraX ID
        list_counter = 0
        while obj_list[list_counter][1] != id and list_counter < len(obj_list):
            list_counter += 1

        if list_counter >= len(obj_list):
            print("Error: Cannot update object list: ID does not exist")
        else:
            # Get Euler angles from position matrix
            from chimerax.geometry.matrix import euler_angles
            psi, theta, phi = euler_angles(position_matrix)

            # Give update information to motivelist
            self.motivelist[list_counter][7] = position_matrix[0][3]    # X position
            self.motivelist[list_counter][8] = position_matrix[1][3]    # Y position
            self.motivelist[list_counter][9] = position_matrix[2][3]    # Z position
            self.motivelist[list_counter][16] = phi                     # Phi angle
            self.motivelist[list_counter][17] = psi                     # Psi angle
            self.motivelist[list_counter][18] = theta                   # Theta angle
