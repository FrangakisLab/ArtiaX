# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
import numpy as np
import starfile
import pandas as pd

# Chimerax
from chimerax.core.errors import UserError

# This package
from ..ParticleData import ParticleData, EulerRotation


class RELIONEulerRotation(EulerRotation):

    def __init__(self):
        super().__init__(axis_1=(0, 0, 1), axis_2=(0, 1, 0), axis_3=(0, 0, 1))

    def rot1_from_matrix(self, matrix):
        """rlnAngleRot -- Phi"""
        # Singularity check
        if matrix[2, 2] > 0.9999:
            angle = 0
        else:
            angle = np.arctan2(matrix[2, 1], matrix[2, 0]) * 180.0 / np.pi

        return angle

    def rot2_from_matrix(self, matrix):
        """rlnAngleTilt -- Theta"""
        angle = np.arccos(matrix[2, 2]) * 180.0 / np.pi

        return angle

    def rot3_from_matrix(self, matrix):
        """Psi"""
        # Singularity check
        if matrix[2, 2] > 0.9999:
            angle = np.arctan2(-matrix[1, 0], matrix[0, 0]) * 180.0 / np.pi
        else:
            angle = np.arctan2(matrix[1, 2], -matrix[0, 2]) * 180.0 / np.pi

        return angle


class RELIONParticleData(ParticleData):

    DATA_KEYS = {
        'rlnCoordinateX': [],
        'rlnCoordinateY': [],
        'rlnCoordinateZ': [],
        'rlnOriginX': [],
        'rlnOriginY': [],
        'rlnOriginZ': [],
        'rlnAngleRot': [],
        'rlnAngleTilt': [],
        'rlnAnglePsi': []
    }

    DEFAULT_PARAMS = {
        'pos_x': 'rlnCoordinateX',
        'pos_y': 'rlnCoordinateY',
        'pos_z': 'rlnCoordinateZ',
        'shift_x': 'shift_x',
        'shift_y': 'shift_y',
        'shift_z': 'shift_z',
        'ang_1': 'rlnAngleRot',
        'ang_2': 'rlnAngleTilt',
        'ang_3': 'rlnAnglePsi'
    }

    ROT = RELIONEulerRotation

    remaining_data = {}
    loop_name = 0

    def read_file(self):
        content = starfile.read(self.file_name, always_dict=True)

        # Identify the loop that contains the data
        data_loop = None
        for key, val in content.items():
            if 'rlnCoordinateZ' in list(val.keys()):
                data_loop = key
                break

        # Abort if none found
        if data_loop is None:
            raise UserError('rlnCoordinateZ was not found in any loop section of file {}.'.format(self.file_name))

        # Take the good one, store the rest and the loop name so we can write it out again later on
        df = content[data_loop]
        content.pop(data_loop)
        self.loop_name = data_loop
        self.remaining_data = content

        # What is present
        df_keys = list(df.keys())
        additional_keys = df_keys

        # If we have shifts in Angstrom, use those instead of the pixel shifts, remodel the format definition
        origin_present = False
        origin_angstrom = False
        if 'rlnOriginZ' in df_keys:
            origin_present = True

            additional_keys.remove('rlnOriginX')
            additional_keys.remove('rlnOriginY')
            additional_keys.remove('rlnOriginZ')

        elif 'rlnOriginZAngst' in df_keys:
            origin_present = True
            origin_angstrom = True

            self._data_keys.pop('rlnOriginX')
            self._data_keys.pop('rlnOriginY')
            self._data_keys.pop('rlnOriginZ')

            self._data_keys['rlnOriginXAngst'] = []
            self._data_keys['rlnOriginYAngst'] = []
            self._data_keys['rlnOriginZAngst'] = []

            self._default_params['pos_x'] = 'rlnOriginXAngst'
            self._default_params['pos_y'] = 'rlnOriginYAngst'
            self._default_params['pos_z'] = 'rlnOriginZAngst'

            additional_keys.remove('rlnOriginXAngst')
            additional_keys.remove('rlnOriginYAngst')
            additional_keys.remove('rlnOriginZAngst')

        #TODO: what about rlnTomoSubtomogramRot/Tilt/Psi? Disregard it for now.

        # If angles are not there, take note
        rot_present = False
        if 'rlnAngleRot' in df_keys:
            rot_present = True
            additional_keys.remove('rlnAngleRot')

        tilt_present = False
        if 'rlnAngleTilt' in df_keys:
            tilt_present = True
            additional_keys.remove('rlnAngleTilt')

        psi_present = False
        if 'rlnAnglePsi' in df_keys:
            psi_present = True
            additional_keys.remove('rlnAnglePsi')

        # Additional data (everything that is a number)
        additional_entries = []
        for key in additional_keys:
            if np.issubdtype(df.dtypes[key], np.number):
                additional_entries.append(key)
                self._data_keys[key] = []

        # Store everything
        self._register_keys()

        # Now make particles
        df.reset_index()
        for idx, row in df.iterrows():
            p = self.new_particle()

            # Position
            p['pos_x'] = row['rlnCoordinateX']
            p['pos_y'] = row['rlnCoordinateY']
            p['pos_z'] = row['rlnCoordinateZ']

            # Shift
            if origin_present:
                if origin_angstrom:
                    # Note negation due to convention
                    p['shift_x'] = - row['rlnOriginXAngst']
                    p['shift_y'] = - row['rlnOriginYAngst']
                    p['shift_z'] = - row['rlnOriginZAngst']
                else:
                    # Note negation due to convention
                    p['shift_x'] = - row['rlnOriginX']
                    p['shift_y'] = - row['rlnOriginY']
                    p['shift_z'] = - row['rlnOriginZ']
            else:
                p['shift_x'] = 0
                p['shift_y'] = 0
                p['shift_z'] = 0

            # Orientation
            if rot_present:
                p['ang_1'] = row['rlnAngleRot']
            else:
                p['ang_1'] = 0

            if tilt_present:
                p['ang_2'] = row['rlnAngleTilt']
            else:
                p['ang_2'] = 0

            if psi_present:
                p['ang_3'] = row['rlnAnglePsi']
            else:
                p['ang_3'] = 0

            # Everything else
            for attr in additional_entries:
                p[attr] = float(row[attr])


    def write_file(self, file_name=None):
        if file_name is None:
            file_name = self.file_name

        data = self.as_dictionary()

        # Convert shifts back to their convention
        if 'rlnOriginXAngst' in self._data_keys.keys():
            for idx, v in enumerate(data['rlnOriginXAngst']):
                data['rlnOriginXAngst'][idx] *= -1
                data['rlnOriginYAngst'][idx] *= -1
                data['rlnOriginZAngst'][idx] *= -1
        else:
            for idx, v in enumerate(data['rlnOriginX']):
                data['rlnOriginX'][idx] *= -1
                data['rlnOriginY'][idx] *= -1
                data['rlnOriginZ'][idx] *= -1

        df = pd.DataFrame(data=data)

        full_dict = self.remaining_data
        full_dict[self.loop_name] = df

        starfile.write(full_dict, file_name)
