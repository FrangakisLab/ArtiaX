# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
from typing import Any, Dict, List, Tuple, Union
import numpy as np
import starfile
import pandas as pd
from scipy.sparse.csgraph import depth_first_order
from scipy.spatial.transform import Rotation as R
import os

# Chimerax
import chimerax
from chimerax.core.commands import StringArg, BoolArg
from chimerax.core.errors import UserError
from chimerax.core.session import Session
from chimerax.core.models import Model
from chimerax.map import Volume

# This package
from ..formats import ArtiaXFormat, ArtiaXOpenerInfo, ArtiaXSaverInfo
from ..ParticleData import ParticleData, EulerRotation
from ..RELION.RELIONParticleData import RELIONEulerRotation

from ...widgets.SaveArgsWidget import SaveArgsWidget

EPSILON = np.finfo(np.float32).eps
EPSILON16 = 16 * EPSILON


class RELION5ParticleData(ParticleData):

    DATA_KEYS = {
        "rlnTomoName": [],
        "rlnCenteredCoordinateXAngst": [],
        "rlnCenteredCoordinateYAngst": [],
        "rlnCenteredCoordinateZAngst": [],
        "rlnOriginXAngst":[],
        "rlnOriginYAngst": [],
        "rlnOriginZAngst": [],
        "rlnTomoSubtomogramRot": [],
        "rlnTomoSubtomogramTilt": [],
        "rlnTomoSubtomogramPsi": [],
        "rlnAngleRot": [],
        "rlnAngleTilt": [],
        "rlnAnglePsi": [],
        "rlnAngleTiltPrior": [],
        "rlnAnglePsiPrior": [],
    }

    DEFAULT_PARAMS = {
        "pos_x": "rlnCenteredCoordinateXAngst",
        "pos_y": "rlnCenteredCoordinateYAngst",
        "pos_z": "rlnCenteredCoordinateZAngst",
        "shift_x": "rlnOriginX",
        "shift_y": "rlnOriginY",
        "shift_z": "rlnOriginZ",
        "ang_1": "rlnTomoSubtomogramRot",
        "ang_2": "rlnTomoSubtomogramTilt",
        "ang_3": "rlnTomoSubtomogramPsi",
    }

    ROT = RELIONEulerRotation

    def __init__(
        self,
        session: Session,
        file_name: str,
        oripix: float = 1,
        trapix: float = 1,
        additional_files: List[str] = None,
        dimensions: List[float] = None,
        voxelsize: float = None,
        prefix: str = None,
        suffix: str = None,
        volume: Model = None,
        prior: bool = True,
    ) -> None:
        self.remaining_loops = {}
        self.remaining_data = {}
        self.loop_name = 0
        self.name_prefix = None
        self.name_leading_zeros = None

        self.dimensions = dimensions
        self.voxelsize = voxelsize
        self.prefix = prefix
        self.suffix = suffix
        self.oripix = oripix
        self.volume = volume
        self.prior = prior

        super().__init__(
            session,
            file_name,
            oripix=oripix,
            trapix=trapix,
            additional_files=additional_files,
        )



    def read_file(self, voxelsize = None, dimensions = None, prefix = None, suffix = None, volume = None) -> None:
        """Reads RELION5 star file."""
        #print("import as relion5")
        ### Collect all necessary information for computation
        #Validate information
        if self.prefix is not None:
            prefix = self.prefix
            #print(f"Using prefix: {prefix}")
            #Save prefix from import to later input as default in saving widget
            model_name = os.path.basename(self.file_name)
            # Add to the dictionary instead of overwriting it
            if not hasattr(self.session, 'rel5_import_prefix'):
                self.session.rel5_import_prefix = {}  # Initialize the dictionary if it doesn't exist

            # Set or update the prefix for the current model
            self.session.rel5_import_prefix[model_name] = prefix
            #print(self.session.rel5_import_prefix[model_name])

        if self.suffix is not None:
            suffix = self.suffix
            #print(f"Using suffix: {suffix}")

        #check for dimensions
        if self.dimensions is not None and len(self.dimensions) == 3 and self.voxelsize is not None:
            x_size, y_size, z_size = self.dimensions
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")
            pixsize = self.voxelsize
            print(f"Using pixelsize: {pixsize}")

        #TODO: can be removed
        #input not through command line but through opening gui, therefore open additional window
        elif self.dimensions is None:
            from ...widgets.Relion5ReadAddInfo import CoordInputDialogRead
            # get information through widget about tomogram size and pixelsize
            dialog = CoordInputDialogRead(self.session)
            x_size, y_size, z_size, pixsize, prefix, suffix = dialog.get_info_read()
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")
            print(f"Using pixelsize: {pixsize}")
            #print(f"Using prefix: {prefix}")
            #print(f"Using suffix: {suffix}")


        ###Now actual reading of file

        content = starfile.read(self.file_name, always_dict=True)

        # Identify the loop that contains the data
        data_loop = None
        for key, val in content.items():
            if "rlnCenteredCoordinateZAngst" in list(val.keys()):
                data_loop = key
                break

        if data_loop is None:
            raise UserError(
                f"rlnCenteredCoordinateZAngst was not found in any loop section of file {self.file_name}."
            )

        # calculate center of corresponding tomogram
        x_center = x_size / 2
        y_center = y_size / 2
        z_center = z_size / 2


        # Take the good loop, store the rest and the loop name so we can write it out again later on
        df = content[data_loop]
        content.pop(data_loop)
        self.loop_name = data_loop
        self.remaining_loops = content

        # What is present
        df_keys = list(df.keys())
        additional_keys = df_keys
        self.remember_keys_order = list(df_keys)
        #print("key order", self.remember_keys_order)

        # Do we have tomo names?
        names_present = False
        if "rlnTomoName" in df_keys:
            names = list(df["rlnTomoName"])

            # Sanity check names
            first_name = names[0]

            # Ensure proper handling of prefix and suffix
            if prefix:  # Only check if prefix is not None or empty
                if first_name.startswith(prefix):
                    if suffix:  # Check if suffix is not empty or None
                        if first_name.endswith(suffix):
                            num = first_name[len(prefix): -len(suffix)]
                        else:
                            raise UserError('Tomogram number cannot be extracted due to unmatched suffix.')
                    else:
                        # If suffix is empty or None, just get the part after the prefix
                        num = first_name[len(prefix):]
                else:
                    raise UserError('Tomogram number cannot be extracted due to unmatched prefix.')
            else:
                # No prefix specified, only handle suffix if present
                if suffix:
                    if first_name.endswith(suffix):
                        num = first_name[:-len(suffix)]  # Get the part before the suffix
                    else:
                        raise UserError('Tomogram number cannot be extracted due to unmatched suffix.')
                else:
                    num = first_name  # No prefix or suffix, just use the whole name

            self.name_prefix = prefix
            if isinstance(num, int):
                self.name_leading_zeros = None
            else:
                self.name_leading_zeros = len(num)

            # Process the rest of the names
            for n in names:
                if prefix and not n.startswith(prefix):
                    raise UserError('Encountered particle without matching prefix in rlnTomoName. Aborting.')

                if suffix:
                    if n.endswith(suffix):
                        num = n[len(prefix): -len(suffix)] if prefix else n[:-len(
                            suffix)]  # Handle with or without prefix
                    else:
                        raise UserError('Encountered particle without matching suffix in rlnTomoName. Aborting.')
                else:
                    num = n[len(prefix):] if prefix else n  # Handle the case where there's no suffix


            names_present = True
            additional_keys.remove("rlnTomoName")
        else:
            self._data_keys.pop("rlnTomoName")

        #check if origin there
        origin_present = False
        origin_angstrom=False

        if "rlnOriginZ" in df_keys:
            origin_present = True

            additional_keys.remove("rlnOriginX")
            additional_keys.remove("rlnOriginY")
            additional_keys.remove("rlnOriginZ")

        elif "rlnOriginZAngst" in df_keys:
            origin_present = True
            origin_angstrom = True

            self._data_keys["rlnOriginXAngst"] = []
            self._data_keys["rlnOriginYAngst"] = []
            self._data_keys["rlnOriginZAngst"] = []

            self._default_params["shift_x"] = "rlnOriginXAngst"
            self._default_params["shift_y"] = "rlnOriginYAngst"
            self._default_params["shift_z"] = "rlnOriginZAngst"

            additional_keys.remove("rlnOriginXAngst")
            additional_keys.remove("rlnOriginYAngst")
            additional_keys.remove("rlnOriginZAngst")




        # If angles are not there, take note
        rot_present = False
        if "rlnAngleRot" in df_keys:
            rot_present = True
            #additional_keys.remove("rlnAngleRot")

        tilt_present = False
        if "rlnAngleTilt" in df_keys:
            tilt_present = True
            #additional_keys.remove("rlnAngleTilt")

        psi_present = False
        if "rlnAnglePsi" in df_keys:
            psi_present = True
            #additional_keys.remove("rlnAnglePsi")

        tomo_rot_present = False
        if 'rlnTomoSubtomogramRot' in df_keys:
            tomo_rot_present = True
            additional_keys.remove('rlnTomoSubtomogramRot')

        tomo_tilt_present = False
        if 'rlnTomoSubtomogramTilt' in df_keys:
            tomo_tilt_present = True
            additional_keys.remove('rlnTomoSubtomogramTilt')

        tomo_psi_present = False
        if 'rlnTomoSubtomogramPsi' in df_keys:
            tomo_psi_present = True
            additional_keys.remove('rlnTomoSubtomogramPsi')

        additional_keys.remove("rlnCenteredCoordinateXAngst")
        additional_keys.remove("rlnCenteredCoordinateYAngst")
        additional_keys.remove("rlnCenteredCoordinateZAngst")

        # Additional data (everything that is a number)
        additional_entries = []
        for key in additional_keys:
            if np.issubdtype(df.dtypes[key], np.number):
                additional_entries.append(key)
                self._data_keys[key] = []
            else:
                self.remaining_data[key] = df[key]
                additional_entries.append(key)
                self._data_keys[key] = []


        # Store everything
        self._register_keys()

        # Now make particles
        df.reset_index()

        for idx, row in df.iterrows():

            p = self.new_particle()

            # Name
            if names_present:
                n = row['rlnTomoName']

                if suffix:  # Check if suffix is provided
                    if n.endswith(suffix):
                        if prefix:  # Check if prefix is provided
                            num = n[len(prefix): -len(suffix)]  # Extract the part between prefix and suffix
                        else:
                            num = n[:-len(suffix)]  # No prefix, extract everything before the suffix
                    else:
                        num = None  # Handle the case where the suffix doesn't match
                else:
                    if prefix:  # Check if prefix is provided
                        num = n[len(prefix):]  # Extract the part after the prefix
                    else:
                        num = n  # No prefix or suffix, use the full name

                # Attempt to convert num to float and raise error if it fails
                try:
                    num = float(num)
                    p['rlnTomoName'] = num
                except ValueError:
                    raise UserError(f"Tomogram number could not be extracted from {n}, failed to convert to float.")


            #Coordinate
            p["pos_x"] = (row["rlnCenteredCoordinateXAngst"] / pixsize) + x_center
            p["pos_y"] = (row["rlnCenteredCoordinateYAngst"] / pixsize) + y_center
            p["pos_z"] = (row["rlnCenteredCoordinateZAngst"] / pixsize) + z_center

            # Shift
            if origin_present:
                if origin_angstrom:
                    #transfer from Angstrom yo pixel
                    # Note negation due to convention
                    p["shift_x"] = -row["rlnOriginXAngst"] / pixsize
                    p["shift_y"] = -row["rlnOriginYAngst"] / pixsize
                    p["shift_z"] = -row["rlnOriginZAngst"] / pixsize
                else:
                    # Note negation due to convention
                    p["shift_x"] = -row["rlnOriginX"]
                    p["shift_y"] = -row["rlnOriginY"]
                    p["shift_z"] = -row["rlnOriginZ"]
            else:
                p["shift_x"] = 0
                p["shift_y"] = 0
                p["shift_z"] = 0



            # Orientation

            self.read_rel5_and_combined=False

            if rot_present and tilt_present and psi_present and tomo_rot_present and tomo_psi_present and tomo_tilt_present:
                self.read_rel5_and_combined=True

                # Box angles in degrees

                box_angle_rot = row['rlnTomoSubtomogramRot']
                box_angle_tilt = row['rlnTomoSubtomogramTilt']
                box_angle_psi = row['rlnTomoSubtomogramPsi']

                # Particle angles in degrees
                self.particle_angle_rot = row['rlnAngleRot']
                self.particle_angle_tilt = row['rlnAngleTilt']
                self.particle_angle_psi = row['rlnAnglePsi']

                # Convert box angles to a rotation matrix (ZYZ convention, lowercase extrinsic)
                box_rotation = R.from_euler('zyz', [box_angle_rot, box_angle_tilt, box_angle_psi],
                                            degrees=True).as_matrix()

                # Convert particle angles to a rotation matrix (ZYZ convention, uppercase intrinsic)
                particle_rotation = R.from_euler('ZYZ',
                                                 [self.particle_angle_rot, self.particle_angle_tilt,
                                                  self.particle_angle_psi],
                                                 degrees=True).as_matrix()

                # Combine rotations by multiplying the matrices (box followed by particle)
                combined_rotation = box_rotation @ particle_rotation

                combined_rotation = R.from_matrix(
                    combined_rotation)  # Convert matrix back to a Rotation object

                # Convert the combined rotation matrix back to Euler angles in 'zyz' convention
                combined_euler_angles = combined_rotation.as_euler('zyz', degrees=True)

                # Store the combined Euler angles in the p dictionary
                p['ang_1'] = combined_euler_angles[0]  # Combined rot
                self.combined_angles_rot = combined_euler_angles[0]
                p['ang_2'] = combined_euler_angles[1]  # Combined tilt
                self.combined_angles_tilt = combined_euler_angles[1]
                p['ang_3'] = combined_euler_angles[2]  # Combined psi
                self.combined_angles_psi = combined_euler_angles[2]

            # if only rlnAngle present
            elif rot_present and tilt_present and psi_present:
                p['ang_1'] = row['rlnAngleRot']
                p['ang_2'] = row['rlnAngleTilt']
                p['ang_3'] = row['rlnAnglePsi']

            # if only rlnTomoSubtomogram present
            elif tomo_rot_present and tilt_present and psi_present:
                p['ang_1'] = row['rlnTomoSubtomogramRot']
                p['ang_2'] = row['rlnTomoSubtomogramTilt']
                p['ang_3'] = row['rlnTomoSubtomogramPsi']

            else:
                print("Angle Information not complete, default set to 0")
                p['ang_1'] = 0
                p['ang_2'] = 0
                p['ang_3'] = 0

            # Storing Everything else
            for attr in additional_entries:
                if attr in self.remaining_data:
                    #all strings
                    p[attr] = str(row[attr])
                else:
                    #all numbers
                    p[attr] = float(row[attr])

        #print(f"last key check:{self.remember_keys_order}")

    def write_file(
        self,
        file_name: str = None,
        additional_files: List[str] = None,
        dimensions: List[float] = None,
        prefix: str = None,
        suffix: str = None,
        tomonumber: int = None,
        pixelsize: float = None,
        prior: bool=True
    ) -> None:

        self.dimensions = dimensions
        self.prefix = prefix
        self.suffix = suffix
        self.tomonumber = tomonumber
        self.pixelsize = pixelsize
        self.prior = prior

        x_size, y_size, z_size, name = 0, 0, 0, ""

        if self.dimensions is not None and len(self.dimensions) == 3:
            x_size, y_size, z_size = self.dimensions
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")

        if x_size is not None and y_size is not None and z_size is not None:
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")
        if self.pixelsize is not None:
            print(f"Using pixelsize: {self.pixelsize}")
            pixsize = self.pixelsize

        if self.tomonumber != 9999:  #None was not possible for placeholder signaling no user input, therefore 9999
            tomogram_name = self.tomonumber
        else:
            tomogram_name = None


        # calculate center in pixel
        x_center = x_size / 2
        y_center = y_size / 2
        z_center = z_size / 2

        if file_name is None:
            file_name = self.file_name

        data = self.as_dictionary()

        # Tomo Name/Number
        if suffix == "None":
            suffix = None  # Convert the string "None" back to actual None
        if prefix == "None":
            prefix = None  # Convert the string "None" back to actual None

        if tomogram_name is not None:  # name/number is being overwritten by what was inputted
            for idx, n in enumerate(data['rlnTomoName']):
                num = int(float(n))

                # Ensure self.name_leading_zeros has a default value if it's None
                leading_zeros = self.name_leading_zeros if self.name_leading_zeros is not None else 0
                # Zero-pad the number based on the leading zeros
                formatted_num = f"{num:0{leading_zeros}d}"
                if suffix is not None and prefix is not None:
                    if int(formatted_num) == 0:
                        data['rlnTomoName'][idx] = f"{prefix}{tomogram_name}{suffix}"
                    else:
                        data['rlnTomoName'][idx] = f"{prefix}{formatted_num}{suffix}"
                elif prefix is not None:
                    if int(formatted_num) == 0:
                        #print("i am here")
                        data['rlnTomoName'][idx] = f"{prefix}{tomogram_name}"
                    else:
                        data['rlnTomoName'][idx] = f"{prefix}{formatted_num}"
                elif suffix is not None:
                    if int(formatted_num) == 0:
                        data['rlnTomoName'][idx] = f"{tomogram_name}{suffix}"
                    else:
                        data['rlnTomoName'][idx] = f"{formatted_num}{suffix}"

        elif tomogram_name is None:  # no overwriting desired
            # get tomo numbers from internal particle list data
            for idx, n in enumerate(data['rlnTomoName']):
                num = int(float(n))

                # Ensure self.name_leading_zeros has a default value if it's None
                leading_zeros = self.name_leading_zeros if self.name_leading_zeros is not None else 0
                # Zero-pad the number based on the leading zeros
                formatted_num = f"{num:0{leading_zeros}d}"
                # Combine the prefix, zero-padded number, and suffix
                if suffix is not None and prefix is not None:
                    data['rlnTomoName'][idx] = f"{prefix}{formatted_num}{suffix}"
                elif prefix is not None:
                    data['rlnTomoName'][idx] = f"{prefix}{formatted_num}"
                elif suffix is not None:
                    data['rlnTomoName'][idx] = f"{formatted_num}{suffix}"


        for idx in range(len(data['rlnTomoSubtomogramRot'])):

            # Angles, set default
            remove_angles = [0, 90, 0]
            prior_tilt=90
            prior_psi=0

            #if particle list was read in as relion5 and angles were combined, remember original rlnAngle values
            if hasattr(self, 'read_rel5_and_combined') and self.read_rel5_and_combined:
                try:
                    saved_rlnAngles_Rot=data['rlnAngleRot'][idx]
                    saved_rlnAngles_Tilt=data['rlnAngleTilt'][idx]
                    saved_rlnAngles_Psi=data['rlnAnglePsi'][idx]
                except KeyError:
                    #adding default if particle list was read in as rel5 but new particles were added to the list
                    saved_rlnAngles_Rot=0
                    saved_rlnAngles_Tilt=90
                    saved_rlnAngles_Psi=0

                try:
                    saved_rlnAnglesPriorTilt=data['rlnAnglesTiltPrior'][idx]
                    saved_rlnAnglesPriorPsi=data['rlnAnglesPsiPrior'][idx]

                except KeyError:
                    # adding default if particle list was read in as rel5 but new particles were added to the list
                    saved_rlnAnglesPriorTilt=90
                    saved_rlnAnglesPriorPsi=0

            if prior == False:
                # move Angle values to rlnAngle columns
                data['rlnAngleRot'][idx] = data['rlnTomoSubtomogramRot'][idx]
                data['rlnAngleTilt'][idx] = data['rlnTomoSubtomogramTilt'][idx]
                data['rlnAnglePsi'][idx] = data['rlnTomoSubtomogramPsi'][idx]

                # delete rlnTomoSubtomo columns and Prior columns
                #del data['rlnTomoSubtomogramRot']
                #del data['rlnTomoSubtomogramTilt']
                #del data['rlnTomoSubtomogramPsi']
                #del data['rlnAngleTiltPrior']
                #del data['rlnAnglePsiPrior']

            elif prior ==  True:
                # Extract the original rlnTomoSubtomogram angles
                tomo_rot = data['rlnTomoSubtomogramRot'][idx]
                tomo_tilt = data['rlnTomoSubtomogramTilt'][idx]
                tomo_psi = data['rlnTomoSubtomogramPsi'][idx]
                #print(f"rot:{tomo_rot}, tilt:{tomo_tilt}, psi:{tomo_psi}")


                # if particle list was already read in as relion5, replace remove_angles with actual rlnAngle values
                if hasattr(self, 'read_rel5_and_combined') and self.read_rel5_and_combined:
                    remove_angles[0]= saved_rlnAngles_Rot
                    remove_angles[1]= saved_rlnAngles_Tilt
                    remove_angles[2]= saved_rlnAngles_Psi
                    #print(f"remove angles{remove_angles}")
                    prior_tilt = saved_rlnAnglesPriorTilt
                    #print(f"prior tilt : {prior_tilt}")
                    prior_psi = saved_rlnAnglesPriorPsi

                # Convert rlnTomoSubtomogram angles to rotation matrix
                rotation_matrix = R.from_euler('zyz', [tomo_rot, tomo_tilt, tomo_psi], degrees=True).as_matrix()

                # Create a new rotation matrix for the angles to remove
                remove_rotation_matrix = R.from_euler('ZYZ', remove_angles, degrees=True).as_matrix()

                # Combine the two rotations: original rotation minus the removal rotation
                # Inverting the remove_rotation to effectively "remove" it
                resulting_rotation_matrix = rotation_matrix @ remove_rotation_matrix.T

                # Convert the resulting rotation matrix back to Euler angles
                combined_euler_angles = R.from_matrix(resulting_rotation_matrix).as_euler('zyz', degrees=True)

                # Update data with new angle sets
                data['rlnTomoSubtomogramRot'][idx] = combined_euler_angles[0]
                data['rlnTomoSubtomogramTilt'][idx] = combined_euler_angles[1]
                data['rlnTomoSubtomogramPsi'][idx] = combined_euler_angles[2]

                data['rlnAngleRot'][idx] = remove_angles[0]
                data['rlnAngleTilt'][idx] = remove_angles[1]
                data['rlnAnglePsi'][idx] = remove_angles[2]

                # Also create rlnAnglePrior with (0, 90, 0)
                data['rlnAngleTiltPrior'] = prior_tilt
                data['rlnAnglePsiPrior'] = prior_psi


        #Coordinates
            # Convert shifts back to their convention (*-1)
        if "rlnOriginXAngst" in self._data_keys.keys():
            for idx, v in enumerate(data["rlnOriginXAngst"]):
                #change internal shift in pixel back to Angstrom
                data["rlnOriginXAngst"][idx] = data["rlnOriginXAngst"][idx] * -1 *pixsize
                data["rlnOriginYAngst"][idx] = data["rlnOriginYAngst"][idx] * -1 *pixsize
                data["rlnOriginZAngst"][idx] = data["rlnOriginZAngst"][idx] * -1 *pixsize
        else:
            #combine pos with shift since rlnOrigin no longer in relion5
            for idx, v in enumerate(data["rlnOriginX"]):
                data["rlnOriginX"][idx] *= -1
                data["rlnOriginY"][idx] *= -1
                data["rlnOriginZ"][idx] *= -1
                data["rlnCenteredCoordinateXAngst"][idx] = (data["rlnOriginX"][idx] + data["rlnCenteredCoordinateXAngst"][idx])
                data["rlnCenteredCoordinateYAngst"][idx] = (data["rlnOriginY"][idx] + data["rlnCenteredCoordinateYAngst"][idx])
                data["rlnCenteredCoordinateZAngst"][idx] = (data["rlnOriginZ"][idx] + data["rlnCenteredCoordinateZAngst"][idx])
            #removing rlnOrigin column
            del data['rlnOriginX']
            del data['rlnOriginY']
            del data['rlnOriginZ']


        for idx, v in enumerate(data["rlnCenteredCoordinateXAngst"]):
                # changes unit from pixel to Angstrom and makes coordinate centered
                # center coordinate
                data["rlnCenteredCoordinateXAngst"][idx] = (
                    data["rlnCenteredCoordinateXAngst"][idx]
                ) - x_center
                data["rlnCenteredCoordinateYAngst"][idx] = (
                    data["rlnCenteredCoordinateYAngst"][idx]
                ) - y_center
                data["rlnCenteredCoordinateZAngst"][idx] = (
                    data["rlnCenteredCoordinateZAngst"][idx]
                ) - z_center

                # convert coordinate unit from pixel to angstrom
                data["rlnCenteredCoordinateXAngst"][idx] *= pixsize
                data["rlnCenteredCoordinateYAngst"][idx] *= pixsize
                data["rlnCenteredCoordinateZAngst"][idx] *= pixsize

        #if splitting was not desired, delete unecessary columns
        if prior == False:
            # delete rlnTomoSubtomo columns and Prior columns
            del data['rlnTomoSubtomogramRot']
            del data['rlnTomoSubtomogramTilt']
            del data['rlnTomoSubtomogramPsi']
            del data['rlnAngleTiltPrior']
            del data['rlnAnglePsiPrior']


        #Change coordinates column names
        # Define the old-to-new key mapping
        #rename_keys = {
            #'rlnCoordinateZ': 'rlnCenteredCoordinateZAngst',
            #'rlnCoordinateX': 'rlnCenteredCoordinateXAngst',
            #'rlnCoordinateY': 'rlnCenteredCoordinateYAngst'
        #}

        # Create a new dictionary to store the updated key order
        #new_data = {}

        # Iterate over the original dictionary and rename the keys
        #for key, value in data.items():
            # If the key needs to be renamed, use the new key
        #    new_data[rename_keys.get(key, key)] = value

        # Replace the old dictionary with the new one
        #data = new_data

        #reorder columns
        #remember column order if imported as relion5
        if self.remember_keys_order:
            #print("old keys", self.remember_keys_order)
            # Step 1: Check column names
            #print(f"order vorher{self.remember_keys_order}")
            #print(f"order after{data.keys()}")
            data_columns = set(data.keys())
            list_columns = set(self.remember_keys_order)
            columns_match=False

            if data_columns != list_columns:
                missing_in_data = list(list_columns - data_columns)
                extra_in_data = list(data_columns - list_columns)
                #print(f"Missing columns in DataFrame: {missing_in_data}")
                #print(f"Extra columns in DataFrame: {extra_in_data}")
            else:
                #print("Column names match.")
                columns_match=True

            # Step 2: Reorder columns
            #if data_columns == list_columns:
            #    data = data[self.remember_keys_order]
            #    print("Reordered DataFrame:")
            #    print(data)

            # Step 2: Reorder columns
            if columns_match==True:
                if isinstance(data, dict):  # Check if data is a dictionary
                    data = {key: data[key] for key in self.remember_keys_order if key in data}
                    #print("reordered columns")
                #else:
                    #raise TypeError("Expected 'data' to be a dictionary.")

        df = pd.DataFrame(data=data)

        full_dict = self.remaining_loops
        full_dict[self.loop_name] = df

        starfile.write(full_dict, file_name, overwrite=True)

        # Change data_0 to data_particles in star file
        with open(file_name, "r") as file:
            lines = file.readlines()

        search_string = "data_0"
        new_content = "data_particles\n"

        # Iterate over the lines and replace the one containing the specific content
        for i, line in enumerate(lines):
            if search_string in line:
                lines[i] = new_content
                break

        # Write the modified content back to the same file
        with open(file_name, "w") as file:
            file.writelines(lines)




class RELION5OpenerInfo(ArtiaXOpenerInfo):

    def open(self, session, data, file_name, **kwargs):
        # Make sure plugin runs
        from ...cmd import get_singleton

        get_singleton(session)

        #rlnTomoName
        prefix_input = kwargs.get("prefix", None)
        suffix_input = kwargs.get("suffix", None)

        if prefix_input is not None:
            prefix = prefix_input
        else:
            prefix = None
        if suffix_input is not None:
            suffix = suffix_input
        else:
            suffix = None

        #Dimensions
        # Users can either:
        # Provide the dimensions explictely (voxel size and binning from the star file)
        dimensions = kwargs.get("voldim", None)

        # Provide the voxel size explicitely also (overriding the star file)
        voxelsize = kwargs.get("voxelsize", None)

        # Or provide a volume model to get the dimensions from (voxel size from the volume model)
        volume = kwargs.get("volume", None)

        #Check for conflicting input options
        if dimensions is not None and volume is not None:
            raise UserError(
                "Both dimensions and volume model are provided. Please provide only one (explicit dimensions or volume"
                "to get dimensions from)."
            )
        if voxelsize is not None and volume is not None:
            raise UserError(
                "Both voxelsize and volume model are provided. Please provide only one (explicit voxelsize or volume"
                "to get voxelsize from)."
            )
        if dimensions is not None and voxelsize is not None and volume is not None:
            raise UserError(
                "Dimensions, voxelsize and volume model are provided. Please provide only either explicit voxelsize and dimensions or volume"
                "to get voxelsize and dimensions from)."
            )

        # Get the dimensions if provided
        if dimensions is not None:
            x, y, z = dimensions

        # Get the dimensions from the volume model if provided
        if volume is not None:
            if not isinstance(volume, Volume):
                raise UserError(
                    f"Provided model #{Volume.id_string} is not a Volume model."
                )
            x, y, z = volume.data.size
            dim = [x, y, z]
            dimensions = dim
            vs = volume.data.step[0]
            voxelsize = vs

        # If neither are present, open the dialog!
        elif (dimensions is None and volume is None) or (voxelsize is None and volume is None):
            from ...widgets.Relion5ReadAddInfo import CoordInputDialogRead
            print("Information is missing, opening input window")
            #print("Example for expected Syntax: open /your/path/relion5_file.star format relion5 voldim 896,696,250 voxelsize 11.52 prefix TS_ ")
            #print("Example for expected Syntax: open /your/path/relion5_file.star format relion5 volume #1.1.1 prefix tomo ")
            #print("Please provide either a volume or the volume dimensions and pixelsize of your tomogram. To correctly read the column 'rlnTomoName' in the star file, the desired prefix that preceeds the tomogram number can be specified")
            dialog = CoordInputDialogRead(session)
            x, y, z, voxelsize, prefix, suffix = dialog.get_info_read()
            dimensions = x,y,z


        # Open list
        from ..io import open_particle_list

        return open_particle_list(
            session,
            data,
            file_name,
            format_name=self.name,
            from_chimx=True,
            additional_files=None,
            dimensions=(x, y, z),
            voxelsize=voxelsize,
            volume=volume,
            prefix=prefix,
            suffix=suffix,
        )

    @property
    def open_args(self):
        from chimerax.core.commands import FloatArg, Float3Arg, ModelArg, StringArg

        return {"voldim": Float3Arg, "voxelsize": FloatArg, "volume": ModelArg, "prefix": StringArg, "suffix": StringArg}


class RELION5SaveArgsWidget(SaveArgsWidget):

    def __init__(self, session, category="particle list", parent=None):
        super().__init__(session, category, parent)

        # Add the combo box and connect the signal for changing of particle list selection so that prefix default is adjusted
        self.model_combo.currentIndexChanged.connect(self.update_prefix)


    def additional_content(
        self,
    ):
        from Qt.QtWidgets import QLineEdit, QLabel, QHBoxLayout, QVBoxLayout, QGroupBox, QCheckBox, QToolButton
        from ...widgets.NLabelValue import NLabelValue
        from ...widgets.IgnorantComboBox import IgnorantComboBox


        #Prefix and suffix for rlnTomoName, suffix part is commented
        # Layout for the prefix input
        self._keep_name_prefix_layout = QHBoxLayout()  # Horizontal layout for prefix
        self._keep_name_prefix_label = QLabel("Prefix:")  # Label for prefix
        self._keep_name_prefix_edit = QLineEdit("")  # Text input for prefix

        # Add the tooltip button for Prefix input
        self._help_button_prefix = QToolButton()
        self._help_button_prefix.setText("?")
        self._help_button_prefix.setToolTip(
            "Enter the prefix that will precede the tomogram number in 'rlnTomoName'. Example: 'Tomo_' will result in 'Tomo_001', 'Tomo_002', etc.")
        self._keep_name_prefix_layout.addWidget(self._help_button_prefix)  # Add the button next to the prefix input
        self._keep_name_prefix_layout.addWidget(self._keep_name_prefix_label)
        self._keep_name_prefix_layout.addWidget(self._keep_name_prefix_edit)
        # Set the initial prefix value when the widget is first loaded
        self.update_prefix()

        # Layout for the suffix input
        #self._keep_name_suffix_layout = QHBoxLayout()  # Horizontal layout for suffix
        #self._keep_name_suffix_label = QLabel("Suffix:")  # Label for suffix
        #self._keep_name_suffix_edit = QLineEdit("")  # Text input for suffix
        #self._keep_name_suffix_layout.addWidget(self._keep_name_suffix_label)
        #self._keep_name_suffix_layout.addWidget(self._keep_name_suffix_edit)

        # Create a vertical layout to hold both prefix and suffix fields
        self._keep_combined_layout = QVBoxLayout()
        self._keep_combined_layout.addLayout(self._keep_name_prefix_layout)  # Add prefix layout
        #self._keep_combined_layout.addLayout(self._keep_name_suffix_layout)  # Add suffix layout

        # Create a group box to hold both prefix and suffix inputs
        self._keep_tomoname_group = QGroupBox("Prefix:")
        self._keep_tomoname_group.setLayout(self._keep_combined_layout)  # Set combined layout to group box
        #self._keep_tomoname_group.setCheckable(True)  # Make group box checkable
        #self._keep_tomoname_group.setChecked(False)  # Initially unchecked (disabled)

        #New tomogram number, to be used for newly created particles
        # Choose single tomogram number
        self._name_layout = QHBoxLayout()
        self._name_label = QLabel("TomoNumber:")
        self._name_edit = QLineEdit("")

        # Add the tooltip button for TomoNumber input
        self._help_button_tomo_number = QToolButton()
        self._help_button_tomo_number.setText("?")
        self._help_button_tomo_number.setToolTip(
            "Enter the tomogram number for the new particle list.\nThis is required if a tomogram number is not yet assigned to the particles,\ne.g. if the particles were newly created or if the input particle list did not include this information.")
        self._name_layout.addWidget(self._help_button_tomo_number)  # Add the button next to the tomo number input

        self._name_layout.addWidget(self._name_label)
        self._name_layout.addWidget(self._name_edit)

        # Create a vertical layout
        self._combined_layout = QVBoxLayout()
        self._combined_layout.addLayout(self._name_layout)  # Add tomo number layout

        self._tomoname_group = QGroupBox("Set new TomoNumber:")
        self._tomoname_group.setLayout(self._combined_layout)



        # Choose dimensions / voxel size
        # Get from Volume
        self._vol_layout = QHBoxLayout()
        self._vol_label = QLabel("From tomogram:")
        self._vol_combobox = IgnorantComboBox()

        at = self.session.ArtiaX.selected_tomogram
        selected = None

        for idx, vol in enumerate(self.session.ArtiaX.tomograms.iter()):
            if at == vol:
                selected = idx
            self._vol_combobox.addItem(f"#{vol.id_string} - {vol.name}", vol)

        self._vol_combobox.addItem("Custom", None)

        self._vol_layout.addWidget(self._vol_label)
        self._vol_layout.addWidget(self._vol_combobox)

        # Voxelsize
        self._vs_layout = QHBoxLayout()
        self._vs_label = QLabel("Voxel size (angstrom):")
        self._vs_edit = QLineEdit("")
        self._vs_layout.addWidget(self._vs_label)
        self._vs_layout.addWidget(self._vs_edit)

        # Dimensions
        self._dim_widget = NLabelValue(["X", "Y", "Z"])
        self._dim_layout = QVBoxLayout()
        self._dim_layout.addLayout(self._vol_layout)
        self._dim_layout.addWidget(self._dim_widget)
        self._dim_layout.addLayout(self._vs_layout)



        # Group
        self._dim_group = QGroupBox("Set Volume Dimensions:")
        self._dim_group.setLayout(self._dim_layout)

        # Set values from selected volume
        if selected:
            self._vol_combobox.setCurrentIndex(selected)
            self._on_vol_combobox(selected)
            self._name_edit.setText(self.session.ArtiaX.selected_tomogram.name)
        else:
            if self.session.ArtiaX.tomograms.count > 0:
                self._vol_combobox.setCurrentIndex(0)
                self._on_vol_combobox(0)

        self._vol_combobox.currentIndexChanged.connect(self._on_vol_combobox)

        # Split / No Split Section
        self._split_layout = QHBoxLayout()

        # Checkboxes
        self._split_checkbox = QCheckBox("Create File with Prior")
        self._nosplit_checkbox = QCheckBox("Create File without Prior")

        # Question mark icon with tooltip
        self._help_button_prior_true = QToolButton()
        self._help_button_prior_true.setText("?")
        self._help_button_prior_true.setToolTip(
            "Create a particle list with rlnAngleRot/Tilt/Prior, rlnTomoSubtomogramRot/Tilt/Psi and rlnAnglePriorTilt/Psi columns. \nThis can be useful for particles with a relevant geometric context, e.g. membrane proteins or filaments. \nThe orientation of the geometric context will be written out in the rlnTomoSubtomogramRot/Tilt/Psi columns \nand the particle is then positioned in relation to this structure using the columns rlnAngleRot/Tilt/Psi. \nThe RELION-5 processing pipeline can then restrain the rotation around the angles specified in rlnAnglePriorTilt/Psi. \nFurther information can be found in the RELION-5 documentation. ")

        # Question mark icon with tooltip
        self._help_button_prior_false = QToolButton()
        self._help_button_prior_false.setText("?")
        self._help_button_prior_false.setToolTip(
            "Create a particle list with rlnAngleRot/Tilt/Psi columns. \nUseful for particles without geometric context, like e.g. cytosolic particles ")

        # Add checkboxes and help button to layout
        self._split_layout.addWidget(self._help_button_prior_true)
        self._split_layout.addWidget(self._split_checkbox)
        self._split_layout.addWidget(self._help_button_prior_false)
        self._split_layout.addWidget(self._nosplit_checkbox)



        # Group box for Split options
        self._split_group = QGroupBox("Output Options:")
        self._split_group.setLayout(self._split_layout)

        self._main = QVBoxLayout()
        self._main.addWidget(self._tomoname_group)
        self._main.addWidget(self._keep_tomoname_group)
        self._main.addWidget(self._dim_group)
        self._main.addWidget(self._split_group)

        from Qt.QtCore import Qt

        return [self._main], []

    def update_prefix(self):
        # Get the selected model name from the combo box
        selected_model_text = self.model_combo.currentText()  # Get the current text from the combo box
        model_name = selected_model_text.split(" - ")[1] if selected_model_text else ""  # Extract the model name

        if not hasattr(self.session, 'rel5_import_prefix'):
            self.session.rel5_import_prefix = {}  # Initialize the dictionary if it doesn't exist, e.g. when read as relion or em
        default_prefix = self.session.rel5_import_prefix.get(model_name, "")  # Get prefix or empty string

        # Update the QLineEdit with the new prefix
        self._keep_name_prefix_edit.setText(default_prefix)

    def _on_vol_combobox(self, idx) -> None:
        vol = self._vol_combobox.itemData(idx)
        if vol is None:
            self._dim_widget.set_value(0, 0)
            self._dim_widget.set_value(1, 0)
            self._dim_widget.set_value(2, 0)
            self._vs_edit.setText("")
            return

        x, y, z = vol.data.size
        vs = vol.data.step[0]

        self._dim_widget.set_value(0, x)
        self._dim_widget.set_value(1, y)
        self._dim_widget.set_value(2, z)
        self._vs_edit.setText(str(vs))

    def additional_argument_string(self) -> str:

        #Dimensions
        values = self._dim_widget.values
        # Convert the X, Y, Z values to float and format the string
        x = float(values[0])  # X dimension
        y = float(values[1])  # Y dimension
        z = float(values[2])  # Z dimension

        #Voxelsize
        v = float(self._vs_edit.text())

        # Prefix (get text from the QLineEdit)
        if self._keep_name_prefix_edit.text():
            prefix = self._keep_name_prefix_edit.text()
        else:
            prefix = None  # Default empty prefix if field has no input

        # Suffix (corrected to get from the edit field, not label)
        #if self._keep_name_suffix_edit.text():
        #    name_suffix = self._keep_name_suffix_edit.text()
        #else:
        #    name_suffix = None  # Default empty suffix if field has no input
        name_suffix = None

        if self._name_edit.text():
            name_number = self._name_edit.text()
        else:
            name_number = 9999   #if name_number was not supplied during input, set as integer placeholder because None doesnt work

        prior=False
        #Prior
        if self._split_checkbox.isChecked() and self._nosplit_checkbox.isChecked():
            raise UserError("Please select either 'Create File with Prior' or 'Create File without Prior'")
        if self._split_checkbox.isChecked():
            prior=True
        elif self._nosplit_checkbox.isChecked():
            prior=False
        else:
            raise UserError("Please select either ...or ....")


        #print(f"Name_number:{name_number}")
        txt = f"voldim {x:.3f},{y:.3f},{z:.3f} voxelsize {v:.3f} prefix {prefix} suffix {name_suffix} tomonumber {name_number} prior {prior}"

        return txt

class RELION5SaverInfo(ArtiaXSaverInfo):

    def save(
        self,
        session: Session,
        path: str,
        *,
        partlist: Model = None,
        voldim: List[float] = None,
        voxelsize: float = None,
        volume: Model = None,
        prefix: str = None,
        suffix: str = None,
        tomonumber: int = None,
        prior: bool = True,
    ) -> None:

        # UserErrors for input through command line
        if voldim is None and volume is None:
            #print("Example for expected Syntax: save /your/path/desired_relion5_file.star format relion5 partlist #1.2.1 volume #1.1.1 prefix tomo_ tomonumber 17")
            #print("Example for expected Syntax: open /your/path/desired_relion5_file.star format relion5 partlist #1.2.1 voldim 896,696,250 voxelsize 11.52 prefix tomo_ tomonumber 17 ")
            print("Please provide either a volume or the volume dimensions and pixelsize of your tomogram. To correctly populate the column 'rlnTomoName' in the star file, the desired prefix that preceeds the tomogram number can be specified, as well as a fixed tomogram number.")
            raise UserError("No volume dimensions provided.")
        if voxelsize is None and volume is None:
            #print("Example for expected Syntax: save /your/path/desired_relion5_file.star format relion5 partlist #1.2.1 volume #1.1.1 prefix tomo_ tomonumber 17")
            #print("Example for expected Syntax: open /your/path/desired_relion5_file.star format relion5 partlist #1.2.1 voldim 896,696,250 voxelsize 11.52 prefix tomo_ tomonumber 17 ")
            print("Please provide either a volume or the volume dimensions and pixelsize of your tomogram. To correctly populate the column 'rlnTomoName' in the star file, the desired prefix that preceeds the tomogram number can be specified, as well as a fixed tomogram number.")
            raise UserError("No voxelsize provided.")
        if volume is not None and voldim is not None:
            #print("Example for expected Syntax: save /your/path/desired_relion5_file.star format relion5 partlist #1.2.1 volume #1.1.1 prefix tomo_ tomonumber 17")
            #print("Example for expected Syntax: open /your/path/desired_relion5_file.star format relion5 partlist #1.2.1 voldim 896,696,250 voxelsize 11.52 prefix tomo_ tomonumber 17 ")
            print("Please provide either a volume or the volume dimensions and pixelsize of your tomogram. To correctly populate the column 'rlnTomoName' in the star file, the desired prefix that preceeds the tomogram number can be specified, as well as a fixed tomogram number.")
            raise UserError("Please only provide either the dimensions or a volume.")


        # Get the dimensions from the volume model if provided
        if volume is not None:
            if not isinstance(volume, Volume):
                raise UserError(
                    f"Provided model #{Volume.id_string} is not a Volume model."
                )
            x, y, z = volume.data.size
            dim = [x, y, z]
            voldim = dim
            vs = volume.data.step[0]
            voxelsize = vs



        from ..io import save_particle_list

        save_particle_list(
            session,
            path,
            partlist,
            format_name=self.name,
            additional_files=[],
            dimensions=voldim,
            pixelsize = voxelsize,
            prefix=prefix,
            suffix=suffix,
            tomonumber=tomonumber,
            prior=prior

        )

    @property
    def save_args(self) -> Dict[str, Any]:
        from chimerax.core.commands import ModelArg, Float3Arg, FloatArg, StringArg, IntArg

        return {
            "partlist": ModelArg,
            "voldim": Float3Arg,
            "voxelsize": FloatArg,
            "volume": ModelArg,
            "prefix": StringArg,
            "suffix": StringArg,
            "tomonumber": IntArg,
            "prior": BoolArg,
        }


RELION5_FORMAT = ArtiaXFormat(
    name="RELION5 STAR file",
    nicks=["star", "relion5"],
    particle_data=RELION5ParticleData,
    opener_info=RELION5OpenerInfo("RELION5 STAR file"),
    saver_info=RELION5SaverInfo("RELION5 STAR file", widget=RELION5SaveArgsWidget),
)
