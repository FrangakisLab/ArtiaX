# vim: set expandtab shiftwidth=4 softtabstop=4

from chimerax.core.toolshed import BundleAPI

# Subclass from chimerax.core.toolshed.BundleAPI and
# override the method for registering commands,
# inheriting all other methods from the base class.
class _MyAPI(BundleAPI):
    api_version = 1     # start_tool called with BundleInfo and
                        # ToolInfo instance (vs. BundleInfo and
                        # tool name when api_version==0 [the default])

    # Override method
    @staticmethod
    def start_tool(session, bi, ti):
        # session is an instance of chimerax.core.session.Session
        # bi is an instance of chimerax.core.toolshed.BundleInfo
        # ti is an instance of chimerax.core.toolshedToolInfo

        # This method is called once for each time the tool is invoked

        # We check the name of the tool, which should match one of the
        # ones listed in bundle_info.xml (without leading and
        # trailing whitespace), and create and return an instance of the
        # appropiate class from the ''tool'' module.
        if ti.name == "ArtiaX":
            from . import tool
            return tool.ArtiaXUI(session, ti.name)
        raise ValueError("Trying to start unknown tool: %s" % ti.name)

    @staticmethod
    def get_class(class_name):
        # class_name will be a string
        if class_name == "Rotate_Euler":
            from . import start_rotate_euler
            return start_rotate_euler.Rotate_Euler
        raise ValueError("Unknown class name '%s'" % class_name)

    # ==========================================================================
    # Open and save a new file format ==========================================
    # ==========================================================================

    @staticmethod
    def run_provider(session, name, mgr, **kw):
        # 'run_provider' is called by a manager to invoke the functionality
        # of the provider. Since the "data formats" manager never calls
        # run_provider (all the info it needs is in the Provider tag), we know
        # that only the "open command" manager will call this function, and
        # customize it accordingly

        # The 'name' arg will be the same as the 'name' attribute of your
        # Provider tag, and mgr will be the corresponding Manager instance

        # For the "open command" manager, this method must return a
        # chimerax.open_command.OpenerInfo subclass instance.

        # Preset
        if mgr == session.presets:#mgr.name == 'presets':
            from .presets import run_preset
            run_preset(session, name, mgr)

        elif mgr == session.toolbar:#mgr.name == 'toolbar':
            from .toolbar import run_provider
            run_provider(session, name)

        elif mgr == session.open_command:#mgr.name == 'open_command':
            from chimerax.open_command import OpenerInfo
            from .io import open_particle_list, get_fmt_aliases

            # Artiatomi Particles
            if name == "Artiatomi Motivelist":
                class ArtiatomiMotivelistInfo(OpenerInfo):
                    def open(self, session, data, file_name, **kw):
                        return open_particle_list(session, data, file_name, format_name=name)

                    @property
                    def open_args(self):
                        return {}

                return ArtiatomiMotivelistInfo()

        elif mgr == session.save_command:#mgr.name == 'save_command':
            from chimerax.save_command import SaverInfo
            from .io import save_particle_list

            if name == "Artiatomi Motivelist":
                class ArtiatomiMotivelistInfo(SaverInfo):
                    def save(self, session, path, *, partlist=None):
                        save_particle_list(session, path, partlist, format_name="Artiatomi Motivelist")

                    @property
                    def save_args(self):
                        from chimerax.core.commands import ModelArg
                        return {'partlist': ModelArg}

                return ArtiatomiMotivelistInfo()

    @staticmethod
    def register_command(bi, ci, logger):
        logger.status(ci.name)
        # Register all ArtiaX commands
        if 'artiax' in ci.name:
            print('Registered')
            from . import cmd
            cmd.register_artiax(logger)

        #raise ValueError('Test')

# Create the ''bundle_api'' object that ChimeraX expects.
bundle_api = _MyAPI()
