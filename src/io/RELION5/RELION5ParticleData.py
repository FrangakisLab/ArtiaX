# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
from typing import Any, Dict, List, Tuple, Union
import numpy as np
import starfile
import pandas as pd

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
        "rlnCenteredCoordinateXAngst": [],
        "rlnCenteredCoordinateYAngst": [],
        "rlnCenteredCoordinateZAngst": [],
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
        "ang_1": "rlnAngleRot",
        "ang_2": "rlnAngleTilt",
        "ang_3": "rlnAnglePsi",
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
        voxel_size: float = None,
        prefix: str = None,
        suffix: str = None,
    ) -> None:
        self.remaining_loops = {}
        self.remaining_data = {}
        self.loop_name = 0
        self.name_prefix = None
        self.name_leading_zeros = None

        self.dimensions = dimensions
        self.voxel_size = voxel_size
        self.prefix = prefix
        self.suffix = suffix

        super().__init__(
            session,
            file_name,
            oripix=oripix,
            trapix=trapix,
            additional_files=additional_files,
        )

        self.oripix = oripix

    # reading of Relion5 files is included in Relion.RelionParticleData
    def read_file(self) -> None:
        """Reads RELION5 star file."""
        content = starfile.read(self.file_name, always_dict=True)

        # Identify the loop that contains the data, and checks if relion or relion5
        data_loop = None
        format_version = None
        for key, val in content.items():
            if "rlnCenteredCoordinateZAngst" in list(val.keys()):
                data_loop = key
                break

        if data_loop is None:
            raise UserError(
                f"rlnCenteredCoordinateZAngst was not found in any loop section of file {self.file_name}."
            )

        x_size, y_size, z_size, pixsize = 0, 0, 0, 0

        if self.dimensions is not None and len(self.dimensions) == 3:
            x_size, y_size, z_size = self.dimensions
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")

        if self.oripix is not None:
            pixsize = self.oripix
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

            # Ensure proper handling of prefix and suffix
            if first_name.startswith(prefix):
                if suffix:  # Check if suffix is not empty
                    if first_name.endswith(suffix):
                        num = first_name[len(prefix): -len(suffix)]
                    else:
                        raise UserError('Tomogram number cannot be extracted due to unmatched suffix.')
                else:
                    # If suffix is empty, just get the part after the prefix
                    num = first_name[len(prefix):]
            else:
                raise UserError('Tomogram number cannot be extracted due to unmatched prefix.')

            for n in names:
                if not (n.startswith(prefix)):
                    raise UserError('Encountered particle without matching prefix in rlnTomoName. Aborting.')

                # Extract number only once
                if suffix:
                    if n.endswith(suffix):
                        num = n[len(prefix): -len(suffix)]
                    else:
                        raise UserError(
                            'Encountered particle without matching suffix in rlnTomoName. Aborting.')
                else:
                    # If suffix is empty, extract part after the prefix
                    num = n[len(prefix):]

                if num.isdigit():
                    pass  # Optionally, you can add additional processing here
                else:
                    print(f"Encountered particles with inconsistent 'rlnTomoName' prefixes and suffixes in {n}")

            self.name_prefix = prefix
            self.name_leading_zeros = len(num)
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

        # Additional data (everything that is a number)
        additional_entries = []
        for key in additional_keys:
            if np.issubdtype(df.dtypes[key], np.number):
                additional_entries.append(key)
                self._data_keys[key] = []
            else:
                self.remaining_data[key] = df[key]

        # remove column names from regular relion format
        self._data_keys.pop("rlnCoordinateX")
        self._data_keys.pop("rlnCoordinateY")
        self._data_keys.pop("rlnCoordinateZ")
        self._data_keys.pop("rlnOriginX")
        self._data_keys.pop("rlnOriginY")
        self._data_keys.pop("rlnOriginZ")

        # Store everything
        self._register_keys()

        # Now make particles
        df.reset_index()

        for idx, row in df.iterrows():

            p = self.new_particle()

            # Name
            if names_present:
                n = row['rlnTomoName']

                if suffix:
                    if n.endswith(suffix):
                        num = n[len(prefix): -len(suffix)]
                        num = float(num)
                        p['rlnTomoName'] = num
                else:
                    # If suffix is empty, extract part after the prefix
                    num = n[len(prefix):]
                    num = float(num)
                    p['rlnTomoName'] = num

            # Position, recalculate to pixel coordinates not centered
            p["pos_x"] = (row["rlnCenteredCoordinateXAngst"] / pixsize) + x_center
            p["pos_y"] = (row["rlnCenteredCoordinateYAngst"] / pixsize) + y_center
            p["pos_z"] = (row["rlnCenteredCoordinateZAngst"] / pixsize) + z_center

            # Shift, rlnOriginX/Y/Z no longer in relion5 format, therefore 0
            p["shift_x"] = 0
            p["shift_y"] = 0
            p["shift_z"] = 0

            # Orientation
            if rot_present:
                p["ang_1"] = row["rlnAngleRot"]
            else:
                p["ang_1"] = 0

            if tilt_present:
                p["ang_2"] = row["rlnAngleTilt"]
            else:
                p["ang_2"] = 0

            if psi_present:
                p["ang_3"] = row["rlnAnglePsi"]
            else:
                p["ang_3"] = 0

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
    ) -> None:

        self.dimensions = dimensions
        self.prefix = prefix
        self.suffix = suffix
        self.tomonumber = tomonumber

        x_size, y_size, z_size, name = 0, 0, 0, ""

        if self.dimensions is not None and len(self.dimensions) == 3:
            x_size, y_size, z_size = self.dimensions
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")

        if self.tomonumber is not None:
            tomogram_name = self.tomonumber
            print(f"Corresponding tomogram number: {tomogram_name}")

        if x_size is not None and y_size is not None and z_size is not None:
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")
            print(f"Using pixelsize: {self.oripix}")

        # calculate center in pixel
        x_center = x_size / 2
        y_center = y_size / 2
        z_center = z_size / 2

        if file_name is None:
            file_name = self.file_name

        data = self.as_dictionary()

        # Tomo Name/Number
        if tomogram_name is not None:  # name/number is being overwritten by what was inputted
            for idx, n in enumerate(data['rlnTomoName']):
                data['rlnTomoName'][idx] = f"{prefix}{tomogram_name}{suffix}"

        elif tomogram_name is None:  # no overwriting desired
            # get tomo numbers from internal particle list data
            for idx, n in enumerate(data['rlnTomoName']):
                num = int(float(n))

                # Ensure self.name_leading_zeros has a default value if it's None
                leading_zeros = self.name_leading_zeros if self.name_leading_zeros is not None else 0
                # Zero-pad the number based on the leading zeros
                formatted_num = f"{num:0{leading_zeros}d}"
                # Combine the prefix, zero-padded number, and suffix
                data['rlnTomoName'][idx] = f"{prefix}{formatted_num}{suffix}"


        #Coordinates
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
                data["rlnCenteredCoordinateXAngst"][idx] *= self.oripix
                data["rlnCenteredCoordinateYAngst"][idx] *= self.oripix
                data["rlnCenteredCoordinateZAngst"][idx] *= self.oripix

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
        if suffix_input is not None:
            suffix = suffix_input

        #Dimensions
        # Users can either:
        # Provide the dimensions explictely (voxel size and binning from the star file)
        dimensions = kwargs.get("voldim", None)

        # Provide the voxel size explicitely also (overriding the star file)
        voxelsize = kwargs.get("voxelsize", None)

        # Or provide a volume model to get the dimensions from (voxel size from the volume model)
        volume = kwargs.get("volume", None)

        # Validate input (only one of the two options)
        if dimensions is not None and volume is not None:
            raise UserError(
                "Both dimensions and volume model are provided. Please provide only one (explicite dimensions or volume"
                "to get dimensions from)."
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

        # If neither are present, open the dialog!
        if dimensions is None and volume is None:
            from ...widgets.Relion5ReadAddInfo import CoordInputDialogRead

            dialog = CoordInputDialogRead()
            x, y, z, voxelsize, prefix, suffix = dialog.get_info_read()

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
        x = float(self._dimx_edit.text())
        y = float(self._dimy_edit.text())
        z = float(self._dimz_edit.text())

        txt = f"voldim {x:.3f},{y:.3f},{z:.3f}"

        return txt

#TODO continue here
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
        # No volume dimensions provided
        if voldim is None:
            raise UserError("No volume dimensions provided.")

        from ..io import save_particle_list

        save_particle_list(
            session,
            path,
            partlist,
            format_name=self.name,
            additional_files=[],
            dimensions=voldim,
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
