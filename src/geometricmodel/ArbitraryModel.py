# General imports
import numpy as np

# ChimeraX imports
from chimerax.core.models import Model

# ArtiaX imports
from .GeoModel import GeoModel


class ArbitraryModel(GeoModel):
    """An arbitrary model, generated from a volume"""

    def __init__(self, name, session, vertices, normals, triangles):
        super().__init__(name, session)

        session.logger.info("Created an arbitrary model.")

        self.set_geometry(vertices, normals, triangles)
        self.vertex_colors = np.full((len(vertices), 4), self.color)

    def write_file(self, file_name):
        with open(file_name, 'wb') as file:
            np.savez(file, model_type="ArbitraryModel", vertices=self.vertices, normals=self.normals,
                     triangles=self.triangles)

    def take_snapshot(self, session, flags):
        data = {
            'vertices': self.vertices,
            'normals': self.normals,
            'triangles': self.triangles
        }
        data['model state'] = super().take_snapshot(session, flags)
        return data

    @classmethod
    def restore_snapshot(cls, session, data):
        model = cls(data['model state']['name'], session, data['vertices'], data['normals'], data['triangles'])
        Model.set_state_from_snapshot(model, session, data['model state'])
        return model
