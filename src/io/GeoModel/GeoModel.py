# vim: set expandtab shiftwidth=4 softtabstop=4:

# This package
from ..formats import ArtiaXFormat, ArtiaXSaverInfo, ArtiaXOpenerInfo


class GeoModelOpenerInfo(ArtiaXOpenerInfo):

    def __init__(self, name, category='geometric model'):
        super().__init__(name, category=category)


class GeoModelSaverInfo(ArtiaXSaverInfo):

    def __init__(self, name, category='geometric model'):
        super().__init__(name, category=category)

GEOMODEL_FORMAT = ArtiaXFormat(name='ArtiaX geometric model',
                               nicks=['geomodel'],
                               geomodel_data=[],
                               opener_info=GeoModelOpenerInfo('ArtiaX geometric model'),
                               saver_info=GeoModelSaverInfo('ArtiaX geometric model'))
