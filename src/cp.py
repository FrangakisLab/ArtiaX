'''
This script contains all plugin object definitions.
cp: Chimera Plugin
'''

from convert import convert
from chimera import openModels as om

import open_map                             # relative imports
import close_map

class cp_map:
    ''' class defining map instance '''
    map_list = []
    active   = None
    def __init__(self, name, path, ID, vsize, plane):
        self.name = name
        self.path = path
        self.ID = ID
        self.vsize= vsize
        self.plane= plane                   # assign plane that is visible
        self.shown= True                    # flag to pass visibility of map

    @classmethod
    def open(cls):
        ''' opens a density map as EM template '''
        name, path, ID, vsize, plane = open_map.open_map(cp_map.map_list)
        new_map = cp_map(name, path, ID, vsize, plane)# initiate map instance
        cp_map.map_list.append(new_map)     # store instance in map_list for

    def update(self):
        ''' check if chimera has changed attribute '''
        model = om.list()[convert.IDTOlistnum(self.ID)]
        if model.shown() == True:
            self.shown = True
        else:
            self.shown = False
        
    def close(self):
        ''' destroys map instance, kicks it out of map_list ''' 

        ID = self.ID
        close_map.close_map(ID)
        cp_map.map_list.pop(cp_map.active)
        cp_map.active = None

#-----------------------------------------------------------------

import create_motive                        # relative imports
import open_motive
import manipulate
import close_motive
import motive_export

class cp_motive:
    ''' class defining motive instance '''
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

    @classmethod
    def create(cls):
        ''' creates a new marker set as motive '''
        if cp_map.map_list == []:
            print "open a tomogram first"
            return
        if cp_map.active == None:
            print "choose a map first"
            return
        map_vsize = cp_map.map_list[cp_map.active].vsize# fetch map voxel size 
        init_values = create_motive.create_motive(map_vsize)# create marker set
        new_mot = cp_motive(*init_values)   # initiate motive
        cp_motive.mot_list.append(new_mot)  # store motive in mot_list
    
    @classmethod
    def open(cls, asObj = False):
        ''' opens a motive represented by dots OR objects
        asObj == True if representation comes from object file.'''
        if cp_map.map_list == []:
            print "open a tomogram first"
            return
        if cp_map.active == None:
            print "choose a map first"
            return
        map_vsize = cp_map.map_list[cp_map.active].vsize# fetch map voxel size
        init_values = open_motive.open_motive(map_vsize, asObj)# import motive
        new_mot = cp_motive(*init_values)   # initiate motive instance
        cp_motive.mot_list.append(new_mot)  # store motive in mot_list

    def manipulateOn(self, log):
        ''' Starts manipulate.py, which makes particles movable. '''
        if self.obj_path == None:
            asObj = False
        else: asObj = True
        ID = self.ID
        changedID = manipulate.manipulateOn(log, ID, asObj)# make movable, get list of
        if self.obj_path != None:           # changed models
            self.changed.append(changedID)    # append if models repr. particles
        return changedID
    def manipulateOff(self, log, changedID):
        ''' Cancels particle movability. Important if switched on again later.'''
        if self.obj_path == None:
            asObj = False
        else: asObj = True
        manipulate.manipulateOff(log, self.map_vsize, self.com, asObj, changedID)

    def close(self):
        ''' Destroys motive instance, kicks it out of mot_list.''' 
        ID = self.ID
        asObj = False
        if self.obj_path != None:
            asObj = True
        close_motive.close_motive(ID, asObj)
        cp_motive.mot_list.pop(cp_motive.active)
        cp_motive.active = None

    def export(self, log):
        ''' Starts motive_export.py '''
        mot_name=self.mot_name
        mot_path=self.mot_path
        obj_name=self.obj_name
        new =self.new
        firstID = self.firstID
        ID = self.ID
        com= self.com
        map_vsize = self.map_vsize
        changed=self.changed
        id_list = motive_export.motive_export(log, mot_name,mot_path,obj_name,
                                        new,firstID,ID,com,map_vsize,changed)
        return id_list                  # return id_list for motive features
        


