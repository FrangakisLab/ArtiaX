# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
from typing import Any, Dict, List, Tuple, Union
import numpy as np
import starfile
import pandas as pd
from scipy.spatial.transform import Rotation as R

# Chimerax
import chimerax
from chimerax.core.commands import StringArg
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
        "rlnCoordinateX": [],
        "rlnCoordinateY": [],
        "rlnCoordinateZ": [],
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
        "pos_x": "rlnCoordinateX",
        "pos_y": "rlnCoordinateY",
        "pos_z": "rlnCoordinateZ",
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

        super().__init__(
            session,
            file_name,
            oripix=oripix,
            trapix=trapix,
            additional_files=additional_files,
        )



    # reading of Relion5 files is included in Relion.RelionParticleData
    def read_file(self, voxelsize = None, dimensions = None, prefix = None, suffix = None, volume = None) -> None:
        """Reads RELION5 star file."""
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

        #check if necessary info already inputted through command line
        if self.dimensions is not None and len(self.dimensions) == 3 and self.voxelsize is not None:
            x_size, y_size, z_size = self.dimensions
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")

            pixsize = self.voxelsize
            print(f"Using pixelsize: {pixsize}")

        elif self.dimensions is None:
            print("open pop up")
            from ...widgets.Relion5ReadAddInfo import CoordInputDialogRead
            # get information through widget about tomogram size and pixelsize
            dialog = CoordInputDialogRead(self.session)
            x_size, y_size, z_size, pixsize, prefix, suffix = dialog.get_info_read()
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")
            print(f"Using pixelsize: {pixsize}")


        if self.prefix is not None:
            prefix = self.prefix
            print(f"Using prefix: {prefix}")

        if self.suffix is not None:
            suffix = self.suffix
            print(f"Using suffix: {suffix}")


        # calculate center of corresponding tomogram
        x_center = x_size / 2
        y_center = y_size / 2
        z_center = z_size / 2
        #print(x_center)


        # Take the good loop, store the rest and the loop name so we can write it out again later on
        df = content[data_loop]
        content.pop(data_loop)
        self.loop_name = data_loop
        self.remaining_loops = content

        # What is present
        df_keys = list(df.keys())
        additional_keys = df_keys

        # Do we have tomo names?
        names_present = False
        if "rlnTomoName" in df_keys:
            names = list(df["rlnTomoName"])

            # Sanity check names
            first_name = names[0]
            #print(first_name)

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
                    print(first_name)
                    num = first_name  # No prefix or suffix, just use the whole name
                    print(num)

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

        # TODO: what about rlnTomoSubtomogramRot/Tilt/Psi? Disregard it for now.

        # If angles are not there, take note
        rot_present = False
        if "rlnAngleRot" in df_keys:
            rot_present = True
            additional_keys.remove("rlnAngleRot")

        tilt_present = False
        if "rlnAngleTilt" in df_keys:
            tilt_present = True
            additional_keys.remove("rlnAngleTilt")

        psi_present = False
        if "rlnAnglePsi" in df_keys:
            psi_present = True
            additional_keys.remove("rlnAnglePsi")

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


        # Store everything
        self._register_keys()

        # Now make particles
        df.reset_index()

        for idx, row in df.iterrows():

            p = self.new_particle()

            # Name
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

            # Position, recalculate to pixel coordinates not centered
            p["pos_x"] = (row["rlnCenteredCoordinateXAngst"] / pixsize) + x_center
            p["pos_y"] = (row["rlnCenteredCoordinateYAngst"] / pixsize) + y_center
            p["pos_z"] = (row["rlnCenteredCoordinateZAngst"] / pixsize) + z_center


            # Shift, rlnOriginX/Y/Z no longer in relion5 format, therefore 0
            p["shift_x"] = 0
            p["shift_y"] = 0
            p["shift_z"] = 0

            # Orientation
            if rot_present and tilt_present and psi_present and tomo_rot_present and tomo_psi_present and tomo_tilt_present:
                #print("Combining rlnTomoSubtomogram and rlnAngle")
                # Box angles in degrees
                box_angle_rot = row['rlnTomoSubtomogramRot']
                box_angle_tilt = row['rlnTomoSubtomogramTilt']
                box_angle_psi = row['rlnTomoSubtomogramPsi']

                # Particle angles in degrees
                particle_angle_rot = row['rlnAngleRot']
                particle_angle_tilt = row['rlnAngleTilt']
                particle_angle_psi = row['rlnAnglePsi']

                # Convert box angles to a rotation matrix (ZYZ convention, lowercase extrinsic)
                box_rotation = R.from_euler('zyz', [box_angle_rot, box_angle_tilt, box_angle_psi],
                                            degrees=True).as_matrix()

                # Convert particle angles to a rotation matrix (ZYZ convention, uppercase intrinsic)
                particle_rotation = R.from_euler('ZYZ',
                                                 [particle_angle_rot, particle_angle_tilt,
                                                  particle_angle_psi],
                                                 degrees=True).as_matrix()

                # Combine rotations by multiplying the matrices (box followed by particle)
                combined_rotation = box_rotation @ particle_rotation

                combined_rotation = R.from_matrix(
                    combined_rotation)  # Convert matrix back to a Rotation object

                # Convert the combined rotation matrix back to Euler angles in 'zyz' convention
                combined_euler_angles = combined_rotation.as_euler('zyz', degrees=True)

                # Store the combined Euler angles in the p dictionary
                p['ang_1'] = combined_euler_angles[0]  # Combined rot
                p['ang_2'] = combined_euler_angles[1]  # Combined tilt
                p['ang_3'] = combined_euler_angles[2]  # Combined psi

            # if only rlnAngle present
            elif rot_present and tilt_present and psi_present:
                p['ang_1'] = row['rlnAngleRot']
                p['ang_2'] = row['rlnAngleTilt']
                p['ang_3'] = row['rlnAnglePsi']
                #print("Using rlnAngle")

            # if only rlnTomoSubtomogram present
            elif tomo_rot_present and tilt_present and psi_present:
                p['ang_1'] = row['rlnTomoSubtomogramRot']
                p['ang_2'] = row['rlnTomoSubtomogramTilt']
                p['ang_3'] = row['rlnTomoSubtomogramPsi']
                #print("Using rlnTomoSubtomogram")

            else:
                print("Angle Information not complete, default set to 0")
                p['ang_1'] = 0
                p['ang_2'] = 0
                p['ang_3'] = 0

            # Everything else
            for attr in additional_entries:
                p[attr] = float(row[attr])

    def write_file(
        self,
        file_name: str = None,
        additional_files: List[str] = None,
        dimensions: List[float] = None,
        prefix: str = None,
        suffix: str = None,
        tomonumber: int = None,
        pixelsize: float = None,
    ) -> None:

        self.dimensions = dimensions
        self.prefix = prefix
        self.suffix = suffix
        self.tomonumber = tomonumber
        self.pixelsize = pixelsize

        print(f"Dimensions:{self.dimensions}")
        print(f"Prefix:{self.prefix}")
        print(f"Suffix:{self.suffix}")
        print(f"Tomonumber:{self.tomonumber}")

        x_size, y_size, z_size, name = 0, 0, 0, ""

        if self.dimensions is not None and len(self.dimensions) == 3:
            x_size, y_size, z_size = self.dimensions
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")

        if self.tomonumber != 9999:  #None was not possible for placeholder signaling no user input, therefore 9999
            tomogram_name = self.tomonumber
            print(f"Corresponding tomogram number: {tomogram_name}")
        else:
            tomogram_name = None

        if x_size is not None and y_size is not None and z_size is not None:
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")
        if self.pixelsize is not None:
            print(f"Using pixelsize: {self.pixelsize}")
            pixsize = self.pixelsize

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
                if suffix is not None and prefix is not None:
                    data['rlnTomoName'][idx] = f"{prefix}{tomogram_name}{suffix}"
                elif prefix is not None:
                    data['rlnTomoName'][idx] = f"{prefix}{tomogram_name}"
                elif suffix is not None:
                    data['rlnTomoName'][idx] = f"{suffix}{tomogram_name}"

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

        print(f"x_center:{x_center}, y_center:{y_center}, z_center:{z_center}")
        print(f"pixsize:{pixsize}")

        # Angles
        remove_angles = (0, 90, 0)

        for idx in range(len(data['rlnTomoSubtomogramRot'])):
            # Extract the original rlnTomoSubtomogram angles
            tomo_rot = data['rlnTomoSubtomogramRot'][idx]
            tomo_tilt = data['rlnTomoSubtomogramTilt'][idx]
            tomo_psi = data['rlnTomoSubtomogramPsi'][idx]

            # Convert rlnTomoSubtomogram angles to rotation matrix
            rotation_matrix = R.from_euler('zyz', [tomo_rot, tomo_tilt, tomo_psi], degrees=True).as_matrix()

            # Create a new rotation matrix for the angles to remove
            remove_rotation_matrix = R.from_euler('zyz', remove_angles, degrees=True).as_matrix()

            # Combine the two rotations: original rotation minus the removal rotation
            # Inverting the remove_rotation to effectively "remove" it
            resulting_rotation_matrix = rotation_matrix @ remove_rotation_matrix.T

            # Convert the resulting rotation matrix back to Euler angles
            combined_euler_angles = R.from_matrix(resulting_rotation_matrix).as_euler('zyz', degrees=True)

            # Update data with new angle sets
            data['rlnTomoSubtomogramRot'][idx] = combined_euler_angles[0]
            data['rlnTomoSubtomogramTilt'][idx] = combined_euler_angles[1]
            data['rlnTomoSubtomogramPsi'][idx] = combined_euler_angles[2]

            # Also create rlnAngle with (0, 90, 0)
            data['rlnAngleRot'] = remove_angles[0]
            data['rlnAngleTilt'] = remove_angles[1]
            data['rlnAnglePsi'] = remove_angles[2]

            # Also create rlnAngle with (0, 90, 0)
            data['rlnAngleTiltPrior'] = remove_angles[1]
            data['rlnAnglePsiPrior'] = remove_angles[2]

        #Coordinates
        for idx, v in enumerate(data["rlnCoordinateX"]):
                # changes unit from pixel to Angstrom and makes coordinate centered
                #print("before")
                #print(data["rlnCoordinateX"][idx])
                # center coordinate
                data["rlnCoordinateX"][idx] = (
                    data["rlnCoordinateX"][idx]
                ) - x_center
                data["rlnCoordinateY"][idx] = (
                    data["rlnCoordinateY"][idx]
                ) - y_center
                data["rlnCoordinateZ"][idx] = (
                    data["rlnCoordinateZ"][idx]
                ) - z_center

                # convert coordinate unit from pixel to angstrom
                data["rlnCoordinateX"][idx] *= pixsize
                data["rlnCoordinateY"][idx] *= pixsize
                data["rlnCoordinateZ"][idx] *= pixsize
                #print("after")

                #print(data["rlnCoordinateX"][idx])


        # Renaming the rlnCoordianteX key
        rel_key_x = 'rlnCoordinateX'
        rel5_key_x = 'rlnCenteredCoordinateXAngst'
        data[rel5_key_x] = data.pop(rel_key_x)  # Using pop to remove the old key

        #print("Value at rlnCenteredCoordinateXAngst")
        #print(data['rlnCenteredCoordinateXAngst'])

        # Renaming the rlnCoordianteY key
        rel_key_y = 'rlnCoordinateY'
        rel5_key_y = 'rlnCenteredCoordinateYAngst'
        data[rel5_key_y] = data.pop(rel_key_y)  # Using pop to remove the old key

        #print("Value at rlnCenteredCoordinateYAngst")
        #print(data['rlnCenteredCoordinateYAngst'])

        # Renaming the rlnCoordianteZ key
        rel_key_z = 'rlnCoordinateZ'
        rel5_key_z = 'rlnCenteredCoordinateZAngst'
        data[rel5_key_z] = data.pop(rel_key_z)  # Using pop to remove the old key

        #print("Value at rlnCenteredCoordinateZAngst")
        #print(data['rlnCenteredCoordinateZAngst'])

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
        #print(f"Dimension: {dimensions}")

        # Provide the voxel size explicitely also (overriding the star file)
        voxelsize = kwargs.get("voxelsize", None)
        #print(f"voxelsize: {voxelsize}")

        # Or provide a volume model to get the dimensions from (voxel size from the volume model)
        volume = kwargs.get("volume", None)
        #print(f"volume: {volume}")

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
            #print(f"Pixsize:{vs}")
            voxelsize = vs

        # If neither are present, open the dialog!
        elif (dimensions is None and volume is None) or (voxelsize is None and volume is None):
            from ...widgets.Relion5ReadAddInfo import CoordInputDialogRead
            print("Information is missing, opening input window")
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

    def additional_content(
        self,
    ):
        from Qt.QtWidgets import QLineEdit, QLabel, QHBoxLayout, QVBoxLayout, QGroupBox
        from ...widgets.NLabelValue import NLabelValue
        from ...widgets.IgnorantComboBox import IgnorantComboBox

        #Use new tomogram number with specified prefix and suffix
        # Choose single tomogram number
        self._name_layout = QHBoxLayout()
        self._name_label = QLabel("TomoNumber:")
        self._name_edit = QLineEdit("")
        self._name_layout.addWidget(self._name_label)
        self._name_layout.addWidget(self._name_edit)

        # Layout for the prefix input
        self._name_prefix_layout = QHBoxLayout()  # Horizontal layout for prefix
        self._name_prefix_label = QLabel("Prefix:")  # Label for prefix
        self._name_prefix_edit = QLineEdit("")  # Text input for prefix
        self._name_prefix_layout.addWidget(self._name_prefix_label)
        self._name_prefix_layout.addWidget(self._name_prefix_edit)

        # Layout for the suffix input (newly added)
        self._name_suffix_layout = QHBoxLayout()  # Horizontal layout for suffix
        self._name_suffix_label = QLabel("Suffix:")  # Label for suffix
        self._name_suffix_edit = QLineEdit("")  # Text input for suffix
        self._name_suffix_layout.addWidget(self._name_suffix_label)
        self._name_suffix_layout.addWidget(self._name_suffix_edit)

        # Create a vertical layout to hold both prefix and suffix fields
        self._combined_layout = QVBoxLayout()
        self._combined_layout.addLayout(self._name_layout)  # Add tomo number layout
        self._combined_layout.addLayout(self._name_prefix_layout)  # Add prefix layout
        self._combined_layout.addLayout(self._name_suffix_layout)  # Add suffix layout

        self._tomoname_group = QGroupBox("Set new TomoNumber (optional, will overwrite existing numbers):")
        self._tomoname_group.setLayout(self._combined_layout)
        self._tomoname_group.setCheckable(True)
        self._tomoname_group.setChecked(False)

        #Use existing tomonumbers
        # Layout for the prefix input
        self._keep_name_prefix_layout = QHBoxLayout()  # Horizontal layout for prefix
        self._keep_name_prefix_label = QLabel("Prefix:")  # Label for prefix
        self._keep_name_prefix_edit = QLineEdit("")  # Text input for prefix
        self._keep_name_prefix_layout.addWidget(self._keep_name_prefix_label)
        self._keep_name_prefix_layout.addWidget(self._keep_name_prefix_edit)

        # Layout for the suffix input (newly added)
        self._keep_name_suffix_layout = QHBoxLayout()  # Horizontal layout for suffix
        self._keep_name_suffix_label = QLabel("Suffix:")  # Label for suffix
        self._keep_name_suffix_edit = QLineEdit("")  # Text input for suffix
        self._keep_name_suffix_layout.addWidget(self._keep_name_suffix_label)
        self._keep_name_suffix_layout.addWidget(self._keep_name_suffix_edit)

        # Create a vertical layout to hold both prefix and suffix fields
        self._keep_combined_layout = QVBoxLayout()
        self._keep_combined_layout.addLayout(self._keep_name_prefix_layout)  # Add prefix layout
        self._keep_combined_layout.addLayout(self._keep_name_suffix_layout)  # Add suffix layout

        # Create a group box to hold both prefix and suffix inputs
        self._keep_tomoname_group = QGroupBox("Save existing TomoNumbers with specified prefix and/or suffix:")
        self._keep_tomoname_group.setLayout(self._keep_combined_layout)  # Set combined layout to group box
        self._keep_tomoname_group.setCheckable(True)  # Make group box checkable
        self._keep_tomoname_group.setChecked(False)  # Initially unchecked (disabled)


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

        self._main = QVBoxLayout()
        self._main.addWidget(self._tomoname_group)
        self._main.addWidget(self._keep_tomoname_group)
        self._main.addWidget(self._dim_group)

        from Qt.QtCore import Qt

        return [self._main], []

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
        if self._name_prefix_edit.text():  # Check if it has input
            prefix = self._name_prefix_edit.text()
        elif self._keep_name_prefix_edit.text():
            prefix = self._keep_name_prefix_edit.text()
        else:
            prefix = None  # Default empty prefix if neither field has input

        # Suffix (corrected to get from the edit field, not label)
        if self._name_suffix_edit.text():
            name_suffix = self._name_suffix_edit.text()
        elif self._keep_name_suffix_edit.text():
            name_suffix = self._keep_name_suffix_edit.text()
        else:
            name_suffix = None  # Default empty suffix if neither field has input

        if self._name_edit.text():
            name_number = self._name_edit.text()
        else:
            name_number = 9999   #if name_number was not supplied during input, set as integer placeholder because None doesnt work

        print(f"Name_number:{name_number}")
        txt = f"voldim {x:.3f},{y:.3f},{z:.3f} voxelsize {v:.3f} prefix {prefix} suffix {name_suffix} tomonumber {name_number}"

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
    ) -> None:
        print(f"partlist:{partlist}")
        print(f"voldim:{voldim}")
        print(f"voxelsize:{voxelsize}")
        print(f"volume:{volume}")
        print(f"prefix:{prefix}")
        print(f"suffix:{suffix}")
        print(f"tomonumber:{tomonumber}")
        # UserErrors for input through command line
        if voldim is None and volume is None:
            raise UserError("No volume dimensions provided.")
        if voxelsize is None and volume is None:
            raise UserError("No voxelsize provided.")
        if volume is not None and voldim is not None:
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
            print(f"Pixsize:{vs}")
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
        }


RELION5_FORMAT = ArtiaXFormat(
    name="RELION5 STAR file",
    nicks=["star", "relion5"],
    particle_data=RELION5ParticleData,
    opener_info=RELION5OpenerInfo("RELION5 STAR file"),
    saver_info=RELION5SaverInfo("RELION5 STAR file", widget=RELION5SaveArgsWidget),
)
