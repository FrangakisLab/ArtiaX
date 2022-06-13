# vim: set expandtab shiftwidth=4 softtabstop=4:

# ChimeraX
from chimerax.core import errors
from chimerax.core.commands import run
from chimerax.core.models import Model
from chimerax.map import Volume, open_map
from pprint import pprint

# This package
from .volume.Tomogram import Tomogram, orthoplane_cmd
from .util import ManagerModel
from .util.colors import add_colors, ARTIAX_COLORS
from .io import ArtiatomiParticleData, open_particle_list, save_particle_list, get_fmt_aliases
from .particle import ParticleList

# Triggers
TOMOGRAM_ADD = 'tomo added'
TOMOGRAM_DEL = 'tomo removed'

PARTICLES_ADD = 'parts added'
PARTICLES_DEL = 'parts removed'

GEOMODEL_ADD = 'geomodel added'
GEOMODEL_DEL = 'geomodel removed'


def print_trigger(trigger, trigger_data):
    print(trigger)
    print(trigger_data)
    print(type(trigger_data))
    pprint(vars(trigger_data))
    print(trigger_data.drawing)


class ArtiaX(Model):

    DEBUG = False

    def __init__(self, ui):
        super().__init__('ArtiaX', ui.session)

        # GUI
        self.ui = ui

        # Add self to session
        self.session.models.add([self])

        # Set color maps
        add_colors(self.session)
        self.standard_colors = ARTIAX_COLORS

        # Model Managers
        self.tomograms = ManagerModel('Tomograms', self.session)
        self.partlists = ManagerModel('Particle Lists', self.session)
        self.geomodels = ManagerModel('Geometric Models', self.session)

        self.add([self.tomograms])
        self.add([self.partlists])
        self.add([self.geomodels])

        #self.session.models.add([self.tomograms], parent=self)
        #self.session.models.add([self.partlists], parent=self)

        # Triggers
        self.triggers.add_trigger(TOMOGRAM_ADD)
        self.triggers.add_trigger(TOMOGRAM_DEL)
        #self.triggers.add_handler(TOMOGRAM_ADD, self._tomo_added)
        #self.triggers.add_handler(TOMOGRAM_DEL, self._tomo_deleted)

        self.triggers.add_trigger(PARTICLES_ADD)
        self.triggers.add_trigger(PARTICLES_DEL)
        #self.triggers.add_handler(PARTICLES_ADD, self._partlist_added)
        #self.triggers.add_handler(PARTICLES_DEL, self._partlist_deleted)

        self.triggers.add_trigger(GEOMODEL_ADD)
        self.triggers.add_trigger(GEOMODEL_DEL)
        #self.triggers.add_handler(GEOMODEL_ADD, self._geomodel_added)
        #self.triggers.add_handler(GEOMODEL_DEL, self._geomodel_deleted)

        # Graphical preset
        run(self.session, "preset artiax default")

        # Selection
        self.selected_tomogram = None
        self._options_tomogram = None
        self._selected_partlist = None
        self._options_partlist = None
        self._selected_geomodel = None
        self._options_geomodel = None

        # Mouse modes
        from .mouse import (TranslateSelectedParticlesMode,
                            RotateSelectedParticlesMode,
                            TranslatePickedParticleMode,
                            RotatePickedParticleMode,
                            DeletePickedParticleMode,
                            DeleteSelectedParticlesMode)

        self.translate_selected = TranslateSelectedParticlesMode(self.session)
        self.translate_picked = TranslatePickedParticleMode(self.session)
        self.rotate_selected = RotateSelectedParticlesMode(self.session)
        self.rotate_picked = RotatePickedParticleMode(self.session)
        self.delete_selected = DeleteSelectedParticlesMode(self.session)
        self.delete_picked = DeletePickedParticleMode(self.session)
        self.session.ui.mouse_modes.add_mode(self.translate_selected)
        self.session.ui.mouse_modes.add_mode(self.rotate_selected)
        self.session.ui.mouse_modes.add_mode(self.translate_picked)
        self.session.ui.mouse_modes.add_mode(self.rotate_picked)
        self.session.ui.mouse_modes.add_mode(self.delete_selected)
        self.session.ui.mouse_modes.add_mode(self.delete_picked)
        #TODO: Add a bunch of commands here

    def redraw_needed(self, **kw):
        if self.DEBUG:
            print('redraw!')
            print(kw)
        super().redraw_needed(**kw)

    @property
    def selected_partlist(self):
        return self._selected_partlist

    @selected_partlist.setter
    def selected_partlist(self, value):
        self._selected_partlist = value

        if value is not None:
            self.partlists.get(value).store_marker_information()

    @property
    def options_partlist(self):
        return self._options_partlist

    @options_partlist.setter
    def options_partlist(self, value):
        self._options_partlist = value

        if value is None:
            self.ui.ow.motl_widget.setEnabled(False)

    @property
    def options_tomogram(self):
        return self._options_tomogram

    @options_tomogram.setter
    def options_tomogram(self, value):
        self._options_tomogram = value

        if value is None:
            self.ui.ow.tomo_widget.setEnabled(False)

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Convenience Methods
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def get_tomograms(self):
        """Return list of all tomogram models."""
        return self.tomograms.child_models()

    def get_tomogram(self, identifier):
        """Return one tomogram model at idx.

         Parameters
        ----------
        identifier : int, model id tuple
        """
        return self.tomograms.get(identifier)

    def get_particlelists(self):
        """Return list of all particlelist models."""
        return self.partlists.child_models()

    def get_particlelist(self, identifier):
        """Return one particlelist model at idx.

         Parameters
        ----------
        identifier : int
        """
        return self.partlists.get(identifier)

    def add_tomogram(self, model):
        """Add a tomogram model."""
        self.tomograms.add([model])
        self.triggers.activate_trigger(TOMOGRAM_ADD, model)

    def add_particlelist(self, model):
        """Add a particle list model."""
        self.partlists.add([model])
        self.triggers.activate_trigger(PARTICLES_ADD, model)

    @property
    def tomo_count(self):
        return self.tomograms.count

    @property
    def partlist_count(self):
        return self.partlists.count

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# I/O
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def open_tomogram(self, path):
        """Load a tomogram from file."""
        volume = open_map(self.session, path)[0][0]
        tomo = Tomogram.from_volume(self.session, volume)
        self.add_tomogram(tomo)

        # TODO: Do this in pure python?
        run(self.session, "volume #{} capFaces false".format(tomo.id_string), log=False)
        run(self.session, orthoplane_cmd(tomo, 'xy'))
        run(self.session, 'artiax view xy')

    def import_tomogram(self, model):
        """Import a tomogram from ChimeraX."""
        if not isinstance(model, Volume):
            raise errors.UserError("Cannot import data of type {} to ArtiaX as a tomogram.".format(type(model)))

        tomo = Tomogram.from_volume(self.session, model)
        #tomo.triggers.add_handler('deleted', self._tomogram_deleted)
        self.add_tomogram(tomo)

        # TODO: Do this in pure python?
        run(self.session, "volume #{} capFaces false".format(tomo.id_string), log=False)
        run(self.session, orthoplane_cmd(tomo, 'xy'))
        run(self.session, 'artiax view xy')

    def close_tomogram(self, identifier):
        """Close a tomogram by ArtiaX identifier."""
        self.tomograms.get(identifier).delete()
        self.triggers.activate_trigger(TOMOGRAM_DEL, '')

    def open_partlist(self, path, format):
        partlist = open_particle_list(self.session, [], path, format)[0][0]
        self.add_particlelist(partlist)

    def create_partlist(self, pixelsize=1, format_name="Artiatomi Motivelist"):
        partlist = None
        if format_name in get_fmt_aliases(self.session, "Artiatomi Motivelist"):
            name = "particles"
            data = ArtiatomiParticleData(self.session, file_name=None, oripix=1, trapix=1)
            partlist = ParticleList(name, self.session, data)

        if partlist is not None:
            self.add_particlelist(partlist)

    def close_partlist(self, identifier):
        self.partlists.get(identifier).delete()
        self.triggers.activate_trigger(PARTICLES_DEL, '')

    def save_partlist(self, identifier, file_name, format_name):
        partlist = self.partlists.get(identifier)
        save_particle_list(self.session, file_name, partlist, format_name=format_name)

    def attach_display_model(self, identifier, model):
        self.partlists.get(identifier).attach_display_model(model)

    def show_tomogram(self, idx):
        # TODO: log command
        self.tomograms.get(idx).display = True

    def hide_tomogram(self, idx):
        # TODO: log command
        self.tomograms.get(idx).display = False

    def show_partlist(self, idx):
        # TODO: log command
        self.partlists.get(idx).display = True

    def hide_partlist(self, idx):
        # TODO: log command
        self.partlists.get(idx).display = False

    def show_particles(self, identifier, attributes, minima, maxima):
        id = self.partlists.get(identifier).id
        from .util.select import display_cmd
        display_cmd(self.session, id, attributes, minima, maxima)

    def select_particles(self, identifier, attributes, minima, maxima):
        id = self.partlists.get(identifier).id
        from .util.select import selection_cmd
        selection_cmd(self.session, id, attributes, minima, maxima)

    def color_particles(self, identifier, color):
        id = self.partlists.get(identifier).id
        from .util.select import color_cmd
        color_cmd(self.session, id, color)

    def color_particles_byattribute(self, identifier, palette, attribute, minimum, maximum):
        id = self.partlists.get(identifier).id
        from .util.select import colormap_cmd
        colormap_cmd(self.session, id, palette, attribute, minimum, maximum)
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Callbacks
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # def _tomo_added(self, name, data):
    #     self._tomos_changed(name, data)
    #
    # def _tomo_deleted(self, name, data):
    #     self._tomos_changed(name, data)
    #
    # def _tomos_changed(self, name, data):
    #     ui = self.ui
    #     ui._update_tomo_table()
    #
    # def _partlist_added(self, name, data):
    #     self._partlists_changed(name, data)
    #
    # def _partlist_deleted(self, name, data):
    #     self._partlists_changed(name, data)
    #
    # def _partlists_changed(self, name, data):
    #     ui = self.ui
    #     ui._update_partlist_table()

