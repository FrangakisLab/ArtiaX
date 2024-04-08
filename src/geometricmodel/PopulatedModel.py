# General imports
import numpy as np

# ChimeraX imports
from chimerax.bild.bild import _BildFile
from chimerax.atomic import AtomicShapeDrawing

# ArtiaX imports
from .GeoModel import GeoModel, GEOMODEL_CHANGED
from ..particle.SurfaceCollectionModel import SurfaceCollectionModel


class PopulatedModel(GeoModel):
    """
    Parent class to the models that can create particles. Used to draw the markers that show
    how the particles would be created.
    """

    def __init__(self, name, session):
        super().__init__(name, session)
        self.has_particles = False
        """Whether the model should display how particles would look when created."""
        self.marker_axis_display_options = True
        if session.ArtiaX.tomograms.count > 0:
            pix = session.ArtiaX.tomograms.get(0).pixelsize[0]
            self.marker_size = 4 * pix
            self.axes_size = 15 * pix
        else:
            self.marker_size = 4
            self.axes_size = 15
        self.marker_size_edit_range = (0, self.marker_size*2)
        self.axes_size_edit_range = (0, self.axes_size*2)
        """Options for the widget."""

        self.collection_model = SurfaceCollectionModel('Spheres', session)
        """Collection model for collecting the fake particles so that not every one has to be drawn separately."""
        self.add([self.collection_model])
        self.collection_model.add_collection('direction_markers')
        v, n, t, vc = self.get_direction_marker_surface()
        self.collection_model.set_surface('direction_markers', v, n, t)
        self.spheres_places = np.array([])
        """List containing the place object for every fake particle."""
        self.indices = []
        """list of strings with the indices for all fake particles. Used to delete them from the collection model."""

    @GeoModel.color.setter
    def color(self, color):
        if len(color) == 3:  # transparency was not given
            color = np.append(color, self._color[3])
        self._color = color
        self.vertex_colors = np.full(np.shape(self.vertex_colors), color)
        self.collection_model.color = color

    def change_marker_size(self, r):
        if self.marker_size != r:
            self.marker_size = r
            v, n, t, vc = self.get_direction_marker_surface()
            self.collection_model.set_surface('direction_markers', v, n, t)

    def change_axes_size(self, s):
        if self.axes_size != s:
            self.axes_size = s
            v, n, t, vc = self.get_direction_marker_surface()
            self.collection_model.set_surface('direction_markers', v, n, t)

    def get_direction_marker_surface(self):
        b = _BildFile(self.session, 'dummy')

        b.sphere_command('.sphere 0 0 0 {}'.format(self.marker_size).split())
        b.arrow_command(".arrow 0 0 0 {} 0 0 {} {}".format(self.axes_size, self.axes_size / 15,
                                                           self.axes_size / 15 * 4).split())
        b.arrow_command(".arrow 0 0 0 0 0 {} {} {}".format(self.axes_size, self.axes_size / 15,
                                                           self.axes_size / 15 * 4).split())

        d = AtomicShapeDrawing('shapes')
        d.add_shapes(b.shapes)

        return d.vertices, d.normals, d.triangles, d.vertex_colors

    def remove_spheres(self):
        """Removes fake particles."""
        self.collection_model.delete_places(self.indices)
        self.indices = []
        self.has_particles = False
        self.triggers.activate_trigger(GEOMODEL_CHANGED, self)

    def create_particle_list(self):
        """Creates a new particle list with the positions from sphere_places."""
        artia = self.session.ArtiaX
        artia.create_partlist(name=self.name + " particles")
        partlist = artia.partlists.child_models()[-1]
        artia.ui.ow._show_tab("geomodel")


        partlist.new_particles(self.spheres_places, np.zeros((len(self.spheres_places), 3)), self.spheres_places)
