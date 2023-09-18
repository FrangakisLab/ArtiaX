# General imports
import numpy as np

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
        #Todo: fix
        with open(file_name, 'wb') as file:
            np.savez(file, model_type="TriangulationSurface", triangles=self.tri)