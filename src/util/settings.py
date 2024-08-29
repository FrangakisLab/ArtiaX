from chimerax.core.settings import Settings
from chimerax.core.configfile import Value
from chimerax.core.commands import EnumOf

class FullEnum(EnumOf):
    allow_truncated = False


class ArtiaXSettings(Settings):
    EXPLICIT_SAVE = {'contrast': Value('DARK_ON_LIGHT', FullEnum(('DARK_ON_LIGHT', 'LIGHT_ON_DARK')), str),}

    AUTO_SAVE = {}