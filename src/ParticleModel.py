import numpy as np

from chimerax.core.models import Model, Surface
from chimerax.map import Volume
from chimerax.graphics import Drawing, Pick

MODEL_MOVED = "model moved"

class ParticleModel(Model):

    DEBUG = False

    def __init__(self, name, session):
        super().__init__(name, session)

        self.triggers.add_trigger(MODEL_MOVED)

    def copy_surface(self, base_model: Volume, notify=True):
        source_model = base_model.surfaces[0]
        new_model = Surface('Surface', self.session)

        vertices = source_model.vertices
        normals = source_model.normals
        triangles = source_model.triangles
        edge_mask = source_model._edge_mask
        triangle_mask = source_model._triangle_mask
        new_model.set_geometry(vertices, normals, triangles, edge_mask, triangle_mask)

        for surf in self.child_models():
            surf.delete()

        self.session.models.add([new_model], parent=self, _notify=notify)
        #self.add([new_model])

    def has_children(self):
        return len(self.child_models()) > 0

    def first_intercept(self, mxyz1, mxyz2, exclude=None):
        if exclude is not None and exclude(self):
            return None

        if len(self.child_models()) == 0:
            return None

        pd = Drawing.first_intercept(self, mxyz1, mxyz2, exclude)
        if pd:
            d = pd.drawing()
            detail = d.name
            p = PickedParticle(self, pd.distance, detail)
            p.triangle_pick = pd
            if d.display_style == d.Mesh or hasattr(pd, 'is_transparent') and pd.is_transparent():
                # Try picking opaque object under transparent map
                p.pick_through = True
            return p

    # @Model.position.setter
    # def position(self, pos):
    #     super()._model_set_position(pos)
    #     self.triggers.activate_trigger(MODEL_MOVED, self)
    #     if self.DEBUG:
    #         print("Model Set Position of {}".format(self.id_string))

    # @Drawing.position.setter
    # def position(self, pos):
    #     super()._drawing_set_position(pos)
    #     self.triggers.activate_trigger(MODEL_MOVED, self)
    #     if self.DEBUG:
    #         print("Drawing Set Position of {}".format(self.id_string))

    def _particle_model_set_position(self, pos):
        if pos != self.position:
            Drawing.position.fset(self, pos)
            self.triggers.activate_trigger(MODEL_MOVED, self)
            if self.DEBUG:
                print("Model Set Position of {}".format(self.id_string))

    position = property(Drawing.position.fget, _particle_model_set_position)

    def _particle_model_set_positions(self, positions):
        if positions != self.positions:
            Drawing.positions.fset(self, positions)
            self.triggers.activate_trigger(MODEL_MOVED, self)
            if self.DEBUG:
                print("Model Set PositionS of {}".format(self.id_string))

    positions = property(Drawing.positions.fget, _particle_model_set_positions)
    # def _scene_positions_changed(self):
    #     super()._scene_positions_changed()
    #     if DEBUG:
    #         print("Scene positions of {} changed".format(self.id_string))

    def color_with_children(self, color):
        if tuple(self.color) != tuple(color):
            self.color = color

        for c in self.child_models():
            if tuple(c.color) != tuple(color):
                c.color = color

    def sel_with_children(self, sel):
        if self.selected != sel:
            self.selected = sel

        for c in self.child_models():
            if self.selected != sel:
                c.selected = sel

    def display_with_children(self, display):
        if self.display != display:
            self.display = display

        for c in self.child_models():
            if c.display != display:
                c.display = display


class PickedParticle(Pick):

    def __init__(self, particle, distance=None, detail=''):
        super().__init__(distance)
        self.particle = particle
        self.detail = detail

    def description(self):
        return "{}".format(self.particle.id_string)

    def specifier(self):
        return "#{}".format(self.particle.id_string)

    def select(self, mode = 'add'):
        p = self.particle

        if mode == 'add':
            sel = True
        elif mode == 'subtract':
            sel = False
        elif mode == 'toggle':
            sel = not p.selected
        else:
            sel = False

        p.selected = sel

        if len(p.child_models() > 0):
            for s in p.child_models():
                s.selected = sel
