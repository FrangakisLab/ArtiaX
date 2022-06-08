# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
import os

# ChimeraX
from chimerax.core.errors import UserError

# This package
from ..particle import ParticleList
from .Artiatomi import ArtiatomiParticleData


def open_particle_list(session, stream, file_name, format_name=None):

    if format_name is None:
        raise UserError("open_particle_list: Format name must be set.")

    if format_name not in get_partlist_fmt_names(session):
        raise UserError("open_particle_list: {} is not a known particle list format.".format(format_name))

    model = None
    modelname = ''
    status = 'Failed to open as Particle List: {}'.format(file_name)

    if format_name in get_fmt_aliases(session, "Artiatomi Motivelist"):
        modelname = os.path.basename(file_name)
        data = ArtiatomiParticleData(session, file_name, oripix=1, trapix=1)
        model = ParticleList(modelname, session, data)

    if model is not None:
        status = 'Opened Particle list {} with {} particles.'.format(modelname, model.size)

    return [model], status

def save_particle_list(session, file_name, partlist, format_name=None):
    if format_name is None:
        raise UserError("save_particle_list: Format name must be set.")

    if format_name not in get_partlist_fmt_names(session):
        raise UserError("save_particle_list: {} is not a known particle list format.".format(format_name))

    if not isinstance(partlist, ParticleList):
        raise UserError("save_particle_list: {} is not a particle list.".format(partlist.id_string))

    if format_name in get_fmt_aliases(session, "Artiatomi Motivelist"):
        if not partlist.datatype == ArtiatomiParticleData:
            raise UserError("save_particle_list: format conversion not implemented".format(partlist.id_string))

        #TODO: Does this need to be protected?
        partlist._data._write_file(file_name=file_name)


def get_partlist_formats(session):
    return [fmt for fmt in session.data_formats.formats if fmt.category == "particle list"]

def get_partlist_fmt_names(session):
    list = get_partlist_formats(session)

    names = []

    for fmt in list:
        names.append(fmt.name)
        for nick in fmt.nicknames:
            names.append(nick)

    return names

def get_fmt_aliases(session, name):
    fmt = session.data_formats[name]

    names = [name]

    for nick in fmt.nicknames:
        names.append(nick)

    return names

