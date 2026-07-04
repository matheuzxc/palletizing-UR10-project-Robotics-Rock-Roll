# Type help("robodk.robolink") or help("robodk.robomath") for more information
# Press F5 to run the script
# Documentation: https://robodk.com/doc/en/RoboDK-API.html
# Reference:     https://robodk.com/doc/en/PythonAPI/robodk.html
# Note: It is not required to keep a copy of this file, your Python script is saved with your RDK project

# You can also use the new version of the API:
from robodk import robolink    # RoboDK API
from robodk import robomath    # Robot toolbox
RDK = robolink.Robolink()

# Forward and backwards compatible use of the RoboDK API:
# Remove these 2 lines to follow python programming guidelines
from robodk import *      # RoboDK API
from robolink import *    # Robot toolbox
# Link to RoboDK
# RDK = Robolink()
# Type help("robolink") or help("robodk") for more information
# Press F5 to run the script
# Note: you do not need to keep a copy of this file, your python script is saved with the station

# Use RoboDK API as RL

frame_pallet        = RDK.Item('PalletA', robolink.ITEM_TYPE_FRAME)

# get variable parameters
SIZE_BOX = RDK.getParam('SizeBox')
SIZE_PALLET = RDK.getParam('SizePallet')
SIZE_BOX_XYZ = [float(x.replace(' ','')) for x in SIZE_BOX.split(',')]
SIZE_PALLET_XYZ = [float(x.replace(' ','')) for x in SIZE_PALLET.split(',')]
SIZE_BOX_Z = SIZE_BOX_XYZ[2] # the height of the boxes is important to take into account when approaching the positions

def box_calc(size_xyz, pallet_xyz):
    """Calculates a list of points to store parts in a pallet"""
    [size_x, size_y, size_z] = size_xyz
    [pallet_x, pallet_y, pallet_z] = pallet_xyz    
    xyz_list = []
    for h in range(int(pallet_z)):
        for j in range(int(pallet_y)):
            for i in range(int(pallet_x)):
                xyz_list = xyz_list + [[(i+0.5)*size_x, (j+0.5)*size_y, (h+0.5)*size_z]]
    return xyz_list

def parts_setup(frame, positions, size_xyz):
    """Place a list of parts in a reference frame. The part/reference object must have been previously copied to the clipboard."""
    [size_x, size_y, size_z] = size_xyz
    nparts = len(positions)
    cstep = 1.0/(nparts - 1)
    for i in range(nparts):
        newpart = frame.Paste()
        newpart.Scale([size_x/100, size_y/100, size_z/100]) #scale with respect to the reference object (100mm cube)
        newpart.setName('Part ' + str(i+1)) #set item name
        newpart.setPose(robomath.transl(positions[i])) #set item position with respect to parent
        newpart.setVisible(True, False) #make item visible but hide the reference frame
        newpart.Recolor([1-cstep*i, cstep*i, 0.2, 1]) #set RGBA color

def cleanup(objects, startswith="Part "):
    """Deletes all objects where the name starts with "startswith", from the provided list of objects."""    
    for item in objects:
        if item.Name().startswith(startswith):
            item.Delete()

# turn off rendering (much faster when setting up the station)
RDK.Render(False)

# cleanup previous simulation (generated parts and tools)
all_objects = RDK.ItemList(robolink.ITEM_TYPE_OBJECT, False)
cleanup(all_objects, 'Part ')
all_tools = RDK.ItemList(robolink.ITEM_TYPE_TOOL, False)
cleanup(all_tools, 'TCP ')

# copy the reference part
partref = RDK.Item('box100mm')
partref.Copy()

#RL.Set_Simulation_Speed(500);
#RL.Set_Simulation_Mode(1)

# calculate an array of positions to get/store the parts
parts_positions = box_calc(SIZE_BOX_XYZ, SIZE_PALLET_XYZ)

# setup/initialise the parts on the palled
parts_setup(frame_pallet, parts_positions, SIZE_BOX_XYZ)

RDK.Render(True)