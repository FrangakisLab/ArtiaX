# vim: set expandtab shiftwidth=4 softtabstop=4:

# General
import os
from typing import List, TextIO, Tuple, Union

# ChimeraX
import numpy as np
from chimerax.core.errors import UserError
from chimerax.core.session import Session
from chimerax.core.models import Model


# This package
# from ..particle import ParticleList


def open_particle_list(
    session: Session,
    stream: Union[TextIO, str],
    file_name: str,
    format_name: str = None,
    from_chimx: bool = False,
    additional_files: List[str] = None,
    **kwargs,
) -> Tuple[List[Model], str]:

    #default oripix
    oripix = 1

    if format_name is None:
        raise UserError("open_particle_list: Format name must be set.")

    if format_name not in get_partlist_fmt_names(session):
        raise UserError(
            f"open_particle_list: {format_name} is not a known particle list format."
        )

    if from_chimx:
        file_name = stream

    model = None
    modelname = ""
    status = "Failed to open as Particle List: {}".format(file_name)

    # Make sure file format manager is there
    from .formats import get_formats

    formats = get_formats(session)

    # Read file if possible
    if format_name in formats:
        modelname = os.path.basename(file_name)
        #print(f"{format_name} ")
        if format_name == "RELION STAR file":
            import starfile
            content = starfile.read(file_name, always_dict=True)
            search_string = "rlnCenteredCoordinateZAngst"
            # Check if the string is in the file contents
            for key, val in content.items():
                if "rlnCenteredCoordinateZAngst" in list(val.keys()):
                    print(f"The string '{search_string}' was found in the file. Therefore it is relion5")
                    format_name = "RELION5 STAR file"
                    break
                else:
                    print(f"The string '{search_string}' was NOT found in the file. Therefore it is old relion")

            #print(f"Changed to {format_name} ")

        #Relion5 needs additional informations
        if format_name == 'RELION5 STAR file':
            print(f"format name : {format_name}")
            #check if information supplied through command line
            voxelsize = kwargs.get('voxelsize')
            dimensions = kwargs.get('dimensions')
            prefix = kwargs.get('prefix')
            suffix = kwargs.get('suffix')

            #set oripix with value of voxelsize so that imported particles are directly shown with correct pixelsize
            oripix = voxelsize

            if dimensions is None:
            #infos not supplied, open pop up window to input infos
                print("open pop up")
                from ..widgets.Relion5ReadAddInfo import CoordInputDialogRead
                # get information through widget about tomogram size and pixelsize
                dialog = CoordInputDialogRead(session)
                x_size, y_size, z_size, pixsize, prefix, suffix = dialog.get_info_read()
                # Update the dimensions and voxelsize based on user input
                dimensions = x_size, y_size, z_size
                voxelsize = pixsize

                # After modifying the variables, update kwargs with the new values
                kwargs['dimensions'] = dimensions
                kwargs['voxelsize'] = voxelsize
                kwargs['prefix'] = prefix
                kwargs['suffix'] = suffix
                oripix = voxelsize



        data = formats[format_name].particle_data(
            session,
            file_name,
            oripix=oripix,
            trapix=1,
            additional_files=additional_files,
            **kwargs,
        )

        from ..particle import ParticleList
        model = ParticleList(modelname, session, data)

        #print("io.open_particle_list is being run")

    if model is not None:
        status = "Opened Particle list {} with {} particles.".format(
            modelname, model.size
        )

    return [model], status


def save_particle_list(
    session: Session,
    file_name: str,
    partlist: Model,
    format_name: str = None,
    additional_files: List[str] = None,
    **kwargs,
) -> None:
    if format_name is None:
        raise UserError("save_particle_list: Format name must be set.")

    if format_name not in get_partlist_fmt_names(session):
        raise UserError(
            f"save_particle_list: {format_name} is not a known particle list format."
        )

    from ..particle import ParticleList

    if not isinstance(partlist, ParticleList):
        raise UserError(
            f"save_particle_list: #{partlist.id_string} is not a particle list."
        )

    save_data = None

    from .formats import get_formats

    formats = get_formats(session)

    if format_name in formats:
        if not partlist.datatype == formats[format_name].particle_data:
            save_data = formats[format_name].particle_data.from_particle_data(
                partlist.data
            )
            # add info which particle belongs to which tomo number
            all_keys = partlist.get_all_attributes()
            print(f"all_keys: {all_keys}")
            if 'rlnTomoName' in all_keys or 'tomo_number' in all_keys:  # check if tomo number info is already present
                print('info present')

                tomo_number_values = None
                # Get TomoNumber infos
                if 'rlnTomoName' in all_keys:
                    tomo_number_values = partlist.get_values_of_attribute('rlnTomoName')  # when input was star file
                elif 'tomo_number' in all_keys:
                    tomo_number_values = partlist.get_values_of_attribute('tomo_number')  # when input was em file

                # Add rlnTomoNumber infos when desired output file is star file
                if format_name == 'RELION STAR file' or format_name == 'RELION5 STAR file':
                    # Update the 'rlnTomoName' values in save_data for all entries
                    if 'rlnTomoName' in save_data._data_keys:  # Ensure the key exists
                        rlnTomoName_count = len(tomo_number_values)  # Number of new values
                        save_data_count = sum(1 for _id, p in save_data)  # Number of entries in save_data

                        # Check if lengths match
                        if rlnTomoName_count == save_data_count:
                            for index, (_id, p) in enumerate(save_data):  # Using enumerate to get index
                                print(f"former value: {p['rlnTomoName']}")
                                p['rlnTomoName'] = tomo_number_values[index]  # Assign the corresponding value
                                print(f"New value: {p['rlnTomoName']}")
                                print("values updated")
                        else:
                            print(f"Warning: Length mismatch! rlnTomoName_values ({rlnTomoName_count}) "
                                  f"does not match save_data entries ({save_data_count}).")

                # Add rlnTomoNumber infos when desired output file is star file
                if format_name == 'Artiatomi Motivelist':
                    # Update the 'tomo_number' values in save_data for all entries
                    if 'tomo_number' in save_data._data_keys:  # Ensure the key exists
                        tomo_number_count = len(tomo_number_values)  # Number of new values
                        save_data_count = sum(1 for _id, p in save_data)  # Number of entries in save_data

                        # Check if lengths match
                        if tomo_number_count == save_data_count:
                            for index, (_id, p) in enumerate(save_data):  # Using enumerate to get index
                                print(f"former value: {p['tomo_number']}")
                                p['tomo_number'] = tomo_number_values[
                                    index]  # Assign the corresponding value
                                print(f"New value: {p['tomo_number']}")
                                print("values updated")
                        else:
                            print(f"Warning: Length mismatch! rlnTomoName_values ({tomo_number_count}) "
                                  f"does not match save_data entries ({save_data_count}).")
        else:
            save_data = partlist.data

    if save_data is not None:
        save_data.write_file(
            file_name=file_name,
            additional_files=additional_files,
            **kwargs,
        )


def open_geomodel(session, stream, file_name, format_name=None):
    model_type = None
    status = ""

    # Read file if possible
    modelname = os.path.basename(file_name)
    data = np.load(stream)
    try:
        model_type = data["model_type"]
    except:
        status = "Failed to open as Geometric Model: {}".format(file_name)

    from ..geometricmodel.GeoModel import open_model

    model = open_model(session, modelname, model_type, data)

    if model_type is not None:
        status = "Opened {}, a {} Geometric Model.".format(modelname, model_type)

    return [model], status


def save_geomodel(session, file_name, geomodel, format_name=None):
    from ..geometricmodel.GeoModel import GeoModel

    if not isinstance(geomodel, GeoModel):
        raise UserError(
            "save_geomodel: {} is not a geometric model.".format(geomodel.id_string)
        )

    geomodel.write_file(file_name)


def get_partlist_formats(session: Session):
    return [
        fmt for fmt in session.data_formats.formats if fmt.category == "particle list"
    ]


def get_partlist_fmt_names(session: Session):
    list = get_partlist_formats(session)

    names = []

    for fmt in list:
        names.append(fmt.name)
        for nick in fmt.nicknames:
            names.append(nick)

    return names


def get_fmt_aliases(session: Session, name: str) -> List[str]:
    fmt = session.data_formats[name]

    names = [name]

    for nick in fmt.nicknames:
        names.append(nick)

    return names
