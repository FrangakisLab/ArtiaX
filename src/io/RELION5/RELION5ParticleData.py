# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
import numpy as np
import starfile
import pandas as pd

# Chimerax
from chimerax.core.errors import UserError

# This package
from ..formats import ArtiaXFormat
from ..ParticleData import ParticleData, EulerRotation
from ...widgets.Relion5SaveAddInfo import CoordInputDialog

EPSILON = np.finfo(np.float32).eps
EPSILON16 = 16 * EPSILON

class RELIONEulerRotation(EulerRotation):

    def __init__(self):
        super().__init__(axis_1=(0, 0, 1), axis_2=(0, 1, 0), axis_3=(0, 0, 1), invert_dir=True)

    def rot1_from_matrix(self, matrix):
        """rlnAngleRot -- Phi"""
        abs_sb = self._abs_sb(matrix)

        if abs_sb is not None:
            angle = np.arctan2(matrix[2, 1], matrix[2, 0])
        else:
            angle = 0

        return angle * 180.0 / np.pi

    def rot2_from_matrix(self, matrix):
        """rlnAngleTilt -- Theta"""
        abs_sb = self._abs_sb(matrix)

        if abs_sb is not None:
            sign_sb = self._sign_rot2(matrix)
            angle = np.arctan2(sign_sb * abs_sb, matrix[2, 2])
        else:
            if np.sign(matrix[2, 2]) > 0:
                angle = 0
            else:
                angle = np.pi

        return angle * 180.0 / np.pi

    def rot3_from_matrix(self, matrix):
        """Psi"""
        abs_sb = self._abs_sb(matrix)

        if abs_sb is not None:
            angle = np.arctan2(matrix[1, 2], -matrix[0, 2])
        else:
            if np.sign(matrix[2, 2]) > 0:
                angle = np.arctan2(-matrix[1, 0], matrix[0, 0])
            else:
                angle = np.arctan2(matrix[1, 0], -matrix[0, 0])

        return angle * 180.0 / np.pi

    def _abs_sb(self, matrix):
        abs_sb = np.sqrt(matrix[0, 2] * matrix[0, 2] + matrix[1, 2] * matrix[1, 2])

        if abs_sb > EPSILON16:
            return abs_sb
        else:
            return None

    def _sign_rot2(self, matrix):
        rot3 = np.arctan2(matrix[1, 2], -matrix[0, 2])

        if np.abs(np.sin(rot3)) < EPSILON:
            sign_sb = np.sign(-matrix[0, 2] / np.cos(rot3))
        else:
            sign_sb = np.sign(matrix[1, 2]) if (np.sin(rot3) > 0) else -np.sign(matrix[1, 2])

        return sign_sb




class RELION5ParticleData(ParticleData):


    DATA_KEYS = {
        'rlnTomoName': [],
        'rlnCenteredCoordinateXAngst': [],
        'rlnCenteredCoordinateYAngst': [],
        'rlnCenteredCoordinateZAngst': [],
        'rlnTomoSubtomogramRot': [],
        'rlnTomoSubtomogramTilt': [],
        'rlnTomoSubtomogramPsi': [],
        'rlnAngleRot': [],
        'rlnAngleTilt': [],
        'rlnAnglePsi': [],
        'rlnAngleTiltPrior': [],
        'rlnAnglePsiPrior': []
    }


    DEFAULT_PARAMS = {
      'pos_x': 'rlnCenteredCoordinateXAngst',
      'pos_y': 'rlnCenteredCoordinateYAngst',
      'pos_z': 'rlnCenteredCoordinateZAngst',
      'shift_x': 'rlnOriginX',
      'shift_y': 'rlnOriginY',
      'shift_z': 'rlnOriginZ',
      'ang_1': 'rlnAngleRot',
      'ang_2': 'rlnAngleTilt',
      'ang_3': 'rlnAnglePsi'

    }

    ROT = RELIONEulerRotation

    def __init__(self, session, file_name, oripix=1, trapix=1, additional_files=None):
        self.remaining_loops = {}
        self.remaining_data = {}
        self.loop_name = 0
        self.name_prefix = None
        self.name_leading_zeros = None

        super().__init__(session, file_name, oripix=oripix, trapix=trapix, additional_files=additional_files)

        self.oripix = oripix


    #reading of Relion5 files is included in Relion.RelionParticleData

    def write_file(self, file_name=None, additional_files=None):

        # Get the X, Y, and Z sizes from widget
        dialog = CoordInputDialog()
        x_size, y_size, z_size, tomogram_name = dialog.get_info()

        if x_size is not None and y_size is not None and z_size is not None:
            print(f"Using sizes: X: {x_size}, Y: {y_size}, Z: {z_size}")
            print(f"Using pixelsize: {self.oripix}")

            #calculate center in pixel
            x_center = (x_size / 2)
            y_center = (y_size / 2)
            z_center = (z_size / 2)

            if file_name is None:
                file_name = self.file_name

            data = self.as_dictionary()

            if self.name_prefix is not None:
                for idx, n in enumerate(data['rlnTomoName']):
                    fmt = '{{}}_{{:0{}d}}'.format(self.name_leading_zeros)
                    data['rlnTomoName'][idx] = fmt.format(self.name_prefix, data['rlnTomoName'][idx])
            else:
                for idx, n in enumerate(data['rlnTomoName']):
                    data['rlnTomoName'][idx] = tomogram_name
                #if 'rlnTomoName' in data.keys():
                #    data.pop('rlnTomoName')

            for idx, v in enumerate(data['rlnCenteredCoordinateXAngst']):
                #changes unit from pixel to Angstrom and makes coordinate centered

                #center coordinate
                data['rlnCenteredCoordinateXAngst'][idx] = (data['rlnCenteredCoordinateXAngst'][idx]) - x_center
                data['rlnCenteredCoordinateYAngst'][idx] = (data['rlnCenteredCoordinateYAngst'][idx]) - y_center
                data['rlnCenteredCoordinateZAngst'][idx] = (data['rlnCenteredCoordinateZAngst'][idx]) - z_center

                #convert coordinate unit from pixel to angstrom
                data['rlnCenteredCoordinateXAngst'][idx] *= self.oripix
                data['rlnCenteredCoordinateYAngst'][idx] *= self.oripix
                data['rlnCenteredCoordinateZAngst'][idx] *= self.oripix

            df = pd.DataFrame(data=data)

            full_dict = self.remaining_loops
            full_dict[self.loop_name] = df

            starfile.write(full_dict, file_name, overwrite=True)

        else:
            print("Input is not valid, exiting the function.")

RELION5_FORMAT = ArtiaXFormat(name='RELION5 STAR file',
                             nicks=['star', 'relion5'],
                             particle_data=RELION5ParticleData)