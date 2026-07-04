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


PARAM_SIZE_BOX = 'SizeBox'
PARAM_SIZE_PALLET = 'SizePallet'
PARAM_CONV_SPEED_MM = 'ConvSpeed'




size_box = RDK.getParam(PARAM_SIZE_BOX)
size_pallet = RDK.getParam(PARAM_SIZE_PALLET)
conv_speed = RDK.getParam(PARAM_CONV_SPEED_MM)

# ------------------------------------------------------------
size_box_input = mbox('Enter the size of the box in mm [L,W,H]', entry=size_box)
if size_box_input:
    RDK.setParam(PARAM_SIZE_BOX, size_box_input)
else:
    raise Exception('Operation cancelled by user')

# ------------------------------------------------------------
size_pallet_input = mbox('Enter the size of the pallet', entry=size_pallet)
if size_pallet_input:
    RDK.setParam(PARAM_SIZE_PALLET, size_pallet_input)
else:
    raise Exception('Operation cancelled by user')

# ------------------------------------------------------------
conv_speed_input = mbox('Enter the speed of the conveyor in mm/s', entry=conv_speed)
if conv_speed_input:
    RDK.setParam(PARAM_CONV_SPEED_MM, conv_speed_input)
    conv_speed = float(conv_speed_input)
    conv = RDK.Item('Conveyor Belt', robolink.ITEM_TYPE_ROBOT)
    conv.setSpeed(conv_speed)
    
else:
    raise Exception('Operation cancelled by user')









