# vim: set expandtab shiftwidth=4 softtabstop=4:

from .io import *

from .Artiatomi import ArtiatomiParticleData
from .Coords import CoordsParticleData
from .Copick import CopickParticleData
from .Dynamo import DynamoParticleData
from .Generic import GenericParticleData
from .PEET import PEETParticleData
from .RELION import RELIONParticleData

from .Artiatomi import ARTIATOMI_FORMAT
from .Generic import GENERIC_PARTICLE_FORMAT
from .Dynamo import DYNAMO_FORMAT
from .RELION import RELION_FORMAT
from .Coords import COORDS_FORMAT
from .Copick import COPICK_FORMAT
from .PEET import PEET_FORMAT
from .GeoModel import GEOMODEL_FORMAT

ARTIAX_FORMATS = [
    ARTIATOMI_FORMAT,
    GENERIC_PARTICLE_FORMAT,
    DYNAMO_FORMAT,
    RELION_FORMAT,
    COORDS_FORMAT,
    PEET_FORMAT,
    GEOMODEL_FORMAT,
    COPICK_FORMAT,
]