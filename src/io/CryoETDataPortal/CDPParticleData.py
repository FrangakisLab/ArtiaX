# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
import json
import numpy as np
import pydantic

if pydantic.VERSION.startswith("1"):
    from pydantic import BaseModel, validator
elif pydantic.VERSION.startswith("2"):
    from pydantic.v1 import BaseModel, validator
else:
    raise ImportError(f"Unsupported pydantic version {pydantic.VERSION}.")
from typing import List, Literal, Optional, Union

# Chimerax
from chimerax.map import open_map
from chimerax.core.errors import UserError

# This package
from ..formats import ArtiaXFormat
from ..ParticleData import ParticleData, EulerRotation


class CDPLocation(BaseModel):
    x: float
    y: float
    z: float


class CDPPoint(BaseModel):
    type: str = "Point"
    location: CDPLocation


class CDPOrientedPoint(CDPPoint):
    type: str = "OrientedPoint"
    xyz_rotation_matrix: List[List[float]] = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


class CDPInstancePoint(CDPPoint):
    type: str = "instancePoint"
    instance_id: int


class CDPGenericPoint(BaseModel):
    type: Literal["Point", "orientedPoint", "instancePoint"]
    location: CDPLocation
    xyz_rotation_matrix: Optional[List[List[float]]] = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    instance_id: Optional[int] = 0


point_factory = {
    "Point": CDPPoint,
    "orientedPoint": CDPOrientedPoint,
    "instancePoint": CDPInstancePoint,
}


class CDPEulerRotation(EulerRotation):

    def __init__(self):
        super().__init__(axis_1=(0, 0, 1), axis_2=(1, 0, 0), axis_3=(0, 0, 1))

    def rot1_from_matrix(self, matrix):
        """Phi"""
        matrix = np.clip(matrix, -1, 1, out=matrix)
        # Singularity check
        if matrix[2, 2] > 0.9999:
            angle = 0
        else:
            angle = np.arctan2(matrix[2, 0], matrix[2, 1]) * 180.0 / np.pi

        return angle

    def rot2_from_matrix(self, matrix):
        """Theta"""
        matrix = np.clip(matrix, -1, 1, out=matrix)

        angle = (
            np.arctan2(np.sqrt(1 - (matrix[2, 2] * matrix[2, 2])), matrix[2, 2])
            * 180.0
            / np.pi
        )

        return angle

    def rot3_from_matrix(self, matrix):
        """Psi"""
        matrix = np.clip(matrix, -1, 1, out=matrix)
        # Singularity check
        if matrix[2, 2] > 0.9999:
            angle = (
                -1.0 * np.sign(matrix[0, 1]) * np.arccos(matrix[0, 0]) * 180.0 / np.pi
            )
        else:
            angle = np.arctan2(matrix[0, 2], -matrix[1, 2]) * 180.0 / np.pi

        return angle


def points_to_particles(
    points: List[CDPGenericPoint], particle_data: "CDPParticleData"
):
    particle_data.type = points[0].type

    for point in points:
        p = particle_data.new_particle()

        p["instance_id"] = point.instance_id
        p["location_x"] = point.location.x
        p["location_y"] = point.location.y
        p["location_z"] = point.location.z

        p.rotation = np.transpose(np.array(point.xyz_rotation_matrix))


def particles_to_points(
    particle_data: "CDPParticleData",
) -> List[Union[CDPPoint, CDPOrientedPoint, CDPInstancePoint]]:
    points = []
    for _id, p in particle_data:
        points.append(
            point_factory[particle_data.type](
                type=particle_data.type,
                location=CDPLocation(
                    x=p["location_x"], y=p["location_y"], z=p["location_z"]
                ),
                xyz_rotation_matrix=np.transpose(p.rotation.matrix).tolist(),
                instance_id=p["instsnce_id"],
            )
        )
    return points


class CDPParticleData(ParticleData):
    DATA_KEYS = {
        "location_x": ["location_x"],
        "location_y": ["location_y"],
        "location_z": ["location_z"],
        "instance_id": ["instance_id"],
        "shift_x": ["shift_x"],
        "shift_y": ["shift_y"],
        "shift_z": ["shift_z"],
        "phi": ["phi"],
        "the": ["the"],
        "psi": ["psi"],
    }

    DEFAULT_PARAMS = {
        "pos_x": "location_x",
        "pos_y": "location_y",
        "pos_z": "location_z",
        "shift_x": "shift_x",
        "shift_y": "shift_y",
        "shift_z": "shift_z",
        "ang_1": "phi",
        "ang_2": "the",
        "ang_3": "psi",
    }

    ROT = CDPEulerRotation

    def __init__(self, session, file_name, oripix=1, trapix=1, additional_files=None):
        self.type = "orientedPoint"

        super().__init__(
            session,
            file_name,
            oripix=oripix,
            trapix=trapix,
            additional_files=additional_files,
        )

    def read_file(self):
        points = []
        with open(self.file_name, "r") as f:
            for line in f:
                data = json.loads(line)
                points.append(CDPGenericPoint(**data))

        points_to_particles(points, self)

    def write_file(self, file_name=None, additional_files=None):
        if file_name is None:
            file_name = self.file_name

        points = particles_to_points(self)

        with open(file_name, "w") as f:
            for p in points:
                f.write(f"{json.dumps(p.dict())}\n")


CDP_FORMAT = ArtiaXFormat(
    name="cryoET Data Portal",
    nicks=["cdp", "data_portal"],
    particle_data=CDPParticleData,
)
