'''
This script serves as a communication script between the open windows
of the Tomo Dialog option
'''

from .start_tomo_dialogue import Tomo_Dialogue
from .tomo_dialog_visualization import Visualization
from .tomo_dialog_manipulation import Manipulation

from chimerax.core.tools import ToolInstance

class TomoCommunication(ToolInstance):
    # Inheriting from ToolInstance makes us known to the ChimeraX tool manager,
    # so we can be notified and take appropiate action when sessions are closed,
    # save, or restored, and we will be listed among running tools and so on.

    # If cleaning up is needed on finish, override the 'delete' method
    # but be sure to call 'delete' from the superclass at the end

    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = True         # We do save/restore in sessions
    help = "help:user/tools/tutorial.html"
                                # Let ChimeraX know about our help page

    def __init__(self, session, tool_name):
        # Initialize base class
        super().__init__(session, tool_name)
        # Call the main windows
        self.tomo_dialog = Tomo_Dialogue(session, tool_name)
        self.tomo_visualization = Visualization(session, tool_name)
        self.tomo_manipulation = Manipulation(session, tool_name)

    # Define functions to communicate between the windows
