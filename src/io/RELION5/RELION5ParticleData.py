# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
from typing import Any, Dict, List, Tuple, Union
import numpy as np
import starfile
import pandas as pd

# Chimerax
import chimerax
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
    ) -> None:
        self.remaining_loops = {}
        self.remaining_data = {}
        self.loop_name = 0
        self.name_prefix = None
        self.name_leading_zeros = None

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

        if (
            x_size is not None
            and y_size is not None
            and z_size is not None
            and pixsize is not None
        ):
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")
            print(f"Using pixelsize: {pixsize}")

        # calculate center of corresponding tomogram
        x_center = x_size / 2
        y_center = y_size / 2
        z_center = z_size / 2

        self.oripix = pixsize

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
            if "_" not in first_name:
                raise UserError(
                    'Encountered particle without "_" in rlnTomoName. Aborting.'
                )

            full = first_name.split("_")
            prefix_guess = "".join(full[0:-1])
            num_guess = full[-1]

            for n in names:
                if "_" not in n:
                    raise UserError(
                        'Encountered particle without "_" in rlnTomoName. Aborting.'
                    )

                full = n.split("_")
                prefix_test = "".join(full[0:-1])

                if prefix_test != prefix_guess:
                    raise UserError(
                        f"Encountered particles with inconsistent "
                        f"rlnTomoName prefixes {prefix_test} and {prefix_guess}. Aborting."
                    )

            self.name_prefix = prefix_guess
            self.name_leading_zeros = len(num_guess)
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
                n = row["rlnTomoName"].split("_")
                num = int(n[-1])
                p["rlnTomoName"] = num

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
    ) -> None:

        # Get the X, Y, and Z sizes from widget
        # dialog = CoordInputDialog()
        # x_size, y_size, z_size, tomogram_name = dialog.get_info()
        x_size, y_size, z_size, name = 0, 0, 0, ""

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

            if self.name_prefix is not None:
                for idx, n in enumerate(data["rlnTomoName"]):
                    fmt = "{{}}_{{:0{}d}}".format(self.name_leading_zeros)
                    data["rlnTomoName"][idx] = fmt.format(
                        self.name_prefix, data["rlnTomoName"][idx]
                    )
            else:
                for idx, n in enumerate(data["rlnTomoName"]):
                    data["rlnTomoName"][idx] = ""  # tomogram_name #TODO:
                # if 'rlnTomoName' in data.keys():
                #    data.pop('rlnTomoName')

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

        else:
            print("Input is not valid, exiting the function.")


class RELION5OpenerInfo(ArtiaXOpenerInfo):

    def open(self, session, data, file_name, **kwargs):
        # Make sure plugin runs
        from ...cmd import get_singleton

        get_singleton(session)

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
            x, y, z, voxelsize = dialog.get_info_read()

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
        )

    @property
    def open_args(self):
        from chimerax.core.commands import FloatArg, Float3Arg, ModelArg

        return {"voldim": Float3Arg, "voxelsize": FloatArg, "volume": ModelArg}


class RELION5SaveArgsWidget(SaveArgsWidget):

    def additional_content(
        self,
    ):
        from Qt.QtWidgets import QLineEdit, QLabel, QHBoxLayout, QVBoxLayout, QGroupBox
        from ...widgets.NLabelValue import NLabelValue
        from ...widgets.IgnorantComboBox import IgnorantComboBox

        # Choose single tomogram name
        self._name_layout = QHBoxLayout()
        self._name_label = QLabel("TomoName:")
        self._name_edit = QLineEdit("")
        self._name_layout.addWidget(self._name_label)
        self._name_layout.addWidget(self._name_edit)

        self._tomoname_group = QGroupBox("Set TomoName:")
        self._tomoname_group.setLayout(self._name_layout)
        self._tomoname_group.setCheckable(True)
        self._tomoname_group.setChecked(False)

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
        )

    @property
    def save_args(self) -> Dict[str, Any]:
        from chimerax.core.commands import ModelArg, Float3Arg, FloatArg

        return {
            "partlist": ModelArg,
            "voldim": Float3Arg,
            "voxelsize": FloatArg,
            "volume": ModelArg,
        }


RELION5_FORMAT = ArtiaXFormat(
    name="RELION5 STAR file",
    nicks=["star", "relion5"],
    particle_data=RELION5ParticleData,
    opener_info=RELION5OpenerInfo("RELION5 STAR file"),
    saver_info=RELION5SaverInfo("RELION5 STAR file", widget=RELION5SaveArgsWidget),
)
