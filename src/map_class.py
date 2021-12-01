"""
This scripts contains three classes
One class for a general tomogram
One class for a general motivelist
One class for an object
"""

from convert import convert

class tomo_map:
    ''' Class defining a tomogram as a map instance '''

    map_list = []
    active = None
    def __init__(self, name, path, ID, vsize, plane):
        self.name = name
        self.path = path
        self.ID =  ID
        self.vsize = vsize
        self.plane = plane      # Assign the plane that is visible
        self.show = True        # Flag to pass visibility of map


class motl_map :
    ''' Class defining a motivelist as a map instance '''

    mot_list = []
    active   = None
    def __init__(self, mot_name, mot_path, obj_name, obj_path,
                        new, firstID, ID, com, map_vsize, obj_vsize, changed):
        self.mot_name = mot_name
        self.mot_path = mot_path
        self.obj_name = obj_name
        self.obj_path = obj_path
        self.new = new                      # info if new for export
        self.firstID = firstID              # firstID and ID compared show
        self.ID = ID                        #... which particles got deleted
        self.com= com                       # centre of object if given
        self.map_vsize = map_vsize          # voxel sizes
        self.obj_vsize = obj_vsize
        self.changed = changed              # list of manipulated particles
        self.shown = True                   # flag to pass visibility of motive
        self.color = "yellow"
        self.editable = False
