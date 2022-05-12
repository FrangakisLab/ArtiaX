from chimerax.core.models import Model
from chimerax.core.errors import UserError
from chimerax.graphics import Drawing

from .Tomogram import Tomogram

class ManagerModel(Model):

    def __init__(self, name, session):
        super().__init__(name, session)

    def get(self, identifier):
        if identifier is None:
            return None

        func = None
        #if isinstance(identifier, str):
        #    func = self._get_by_name
        if isinstance(identifier, int):
            func = self._get_by_idx
        elif isinstance(identifier, tuple):
            func = self._get_by_model_id
        else:
            raise UserError("Unknown Model identifier type {}.".format(type(identifier)))

        return func(identifier)

    def has_name(self, name):
        models = [model for model in self.child_models() if model.name == name]
        if len(models) > 0:
            return True
        else:
            return False

    def has_id(self, id):
        models = [model for model in self.child_models() if model.id == id]
        if len(models) > 0:
            return True
        else:
            return False

    def get_idx(self, identifier):
        if identifier is None:
            return None

        func = None
        #if isinstance(identifier, str):
        #    func = self._get_by_name
        if isinstance(identifier, tuple):
            func = self._get_by_model_id
        elif isinstance(identifier, Tomogram):
            pass
        else:
            raise UserError("Unknown Model identifier type {}.".format(type(identifier)))

        if func is not None:
            model = func(identifier)
        else:
            model = identifier

        return self.child_models().index(model)

    def get_id(self, identifier):
        if identifier is None:
            return None

        func = None
        #if isinstance(identifier, str):
        #    func = self._get_by_name
        if isinstance(identifier, int):
            func = self._get_by_idx
        elif isinstance(identifier, Tomogram):
            pass
        else:
            raise UserError("Unknown Model identifier type {}.".format(type(identifier)))

        if func is not None:
            model = func(identifier)
        else:
            model = identifier

        return model.id

    def get_name(self, identifier):
        if identifier is None:
            return None

        func = None
        if isinstance(identifier, int):
            func = self._get_by_idx
        elif isinstance(identifier, tuple):
            func = self._get_by_model_id
        elif isinstance(identifier, Tomogram):
            pass
        else:
            raise UserError("Unknown Model identifier type {}.".format(type(identifier)))

        if func is not None:
            model = func(identifier)
        else:
            model = identifier

        return model.name

    def set_name(self, idx, name):
        model = self.get(idx)
        #if self.has_name(name) and model.name == name:
        #    return False
        #elif self.has_name(name):
        #    self.session.logger.warning("Name already used on other Model {} in {} ({})".format(self.get(name), self.name, self.id_string))
        #    return False

        model.name = name
        #return True

    @property
    def count(self):
        return len(self.child_models())

    def iter(self):
        return iter(self.child_models())

    def _get_by_idx(self, idx):
        if idx is None:
            return None

        return self.child_models()[idx]

    def _get_by_model_id(self, id):
        if id is None:
            return None

        models = [model for model in self.child_models() if model.id == id]
        return models[0]

    def _managermodel_set_position(self, pos):
        """ManagerModel has static position at the origin."""
        return

    position = property(Drawing.position.fget, _managermodel_set_position)

    def _managermodel_set_positions(self, positions):
        """ManagerModel has static position at the origin."""
        return

    positions = property(Drawing.positions.fget, _managermodel_set_positions)
