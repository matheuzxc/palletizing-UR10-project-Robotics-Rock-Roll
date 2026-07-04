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

# define default approach distance
APPROACH = 100

# gather robot, tool and reference frames from the station
robot               = RDK.Item('UR10 A', robolink.ITEM_TYPE_ROBOT)
tool                = RDK.Item('GripperA', robolink.ITEM_TYPE_TOOL)
frame_pallet        = RDK.Item('PalletA', robolink.ITEM_TYPE_FRAME)
frame_conv          = RDK.Item('ConveyorReference', robolink.ITEM_TYPE_FRAME)
frame_conv_moving   = RDK.Item('MovingRef', robolink.ITEM_TYPE_FRAME)

# gather targets
target_pallet_safe = RDK.Item('PalletApproachA', robolink.ITEM_TYPE_TARGET)
target_conv_safe = RDK.Item('ConvApproachA', robolink.ITEM_TYPE_TARGET)
target_conv = RDK.Item('Put Conveyor', robolink.ITEM_TYPE_TARGET)

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

def TCP_On(toolitem):
    """Attaches the closest object to the toolitem Htool pose,
    It will also output appropriate function calls on the generated robot program (call to TCP_On)"""
    toolitem.AttachClosest()
    toolitem.RDK().RunMessage('Set air valve on')
    toolitem.RDK().RunProgram('TCP_On()');
        
def TCP_Off(toolitem, itemleave=0):
    """Detaches the closest object attached to the toolitem Htool pose,
    It will also output appropriate function calls on the generated robot program (call to TCP_Off)"""
    toolitem.DetachAll(itemleave)
    toolitem.RDK().RunMessage('Set air valve off')
    toolitem.RDK().RunProgram('TCP_Off()');

#RL.Set_Simulation_Speed(500);
#RL.Set_Simulation_Mode(1)

# calculate an array of positions to get/store the parts
parts_positions = box_calc(SIZE_BOX_XYZ, SIZE_PALLET_XYZ)

# Calculate a new TCP that takes into account the size of the part (targets are set to the center of the box)
tool_xyzrpw = tool.PoseTool()*robomath.transl(0,0,SIZE_BOX_Z/2)
tool_tcp = robot.AddTool(tool_xyzrpw, 'TCP A')

# ---------------------------------------------------------------------------------
# -------------------------- PROGRAM START ----------------------------------------

robot.setPoseTool(tool_tcp)
nparts = len(parts_positions)
i = nparts-1
while i >= 0:
    # ----------- take a part from the pallet ------
    # get the xyz position of part i
    robot.setPoseFrame(frame_pallet)
    part_position_i = parts_positions[i]
    target_i = robomath.transl(part_position_i)*robomath.rotx(pi)
    target_i_app = target_i * robomath.transl(0,0,-(APPROACH+SIZE_BOX_Z))    
    # approach to the pallet
    robot.MoveJ(target_pallet_safe)
    # get the box i
    robot.MoveJ(target_i_app)
    robot.MoveL(target_i)
    TCP_On(tool) # attach the closest part
    robot.MoveL(target_i_app)
    robot.MoveJ(target_pallet_safe)

    # ----------- place the box i on the convegor ------
    # approach to the conveyor
    robot.setPoseFrame(frame_conv)
    target_conv_pose = target_conv.Pose()*robomath.transl(0,0,-SIZE_BOX_Z/2)
    target_conv_app = target_conv_pose*robomath.transl(0,0,-APPROACH)
    robot.MoveJ(target_conv_safe)
    robot.MoveJ(target_conv_app)
    robot.MoveL(target_conv_pose)
    TCP_Off(tool, frame_conv_moving) # detach an place the object in the moving reference frame of the conveyor
    robot.MoveL(target_conv_app)
    robot.MoveJ(target_conv_safe)
    
    i = i - 1
    
    