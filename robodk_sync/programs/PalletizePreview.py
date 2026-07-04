# PalletizePreview — roda DENTRO do RoboDK e paletiza com ciclo pick -> place real.
#
# O pick e feito na ESTEIRA (Get Conveyor / ConvApproach), do lado oposto ao pallet, como no
# RobotB_StoreParts.py: a caixa surge sobre a esteira, o robo PEGA (a caixa segue a garra),
# leva ao pallet e SOLTA, camada por camada. Padroes (grid/brick/pinhole/split_block) sao os
# mesmos de palletizer/planner/patterns.py.
#
# COMO RODAR: arraste este arquivo para a janela do RoboDK (ou Tools > Run Script) e Play.

from robodk import robolink, robomath

# ----------------------------- AJUSTE AQUI -----------------------------
PATTERN = "brick"        # "grid" | "brick" | "pinhole" | "split_block"
LAYERS = 4               # no de camadas (minimo 2)
ROBOT_LETTER = "B"       # "A" ou "B" (qual UR10 da estacao)
MOVE_ROBOT = True        # False = so preenche o pallet, sem pick nem robo
APPROACH = 100.0         # folga de aproximacao vertical (mm)

# Nomes da esteira na estacao (fonte do pick). Ajuste se forem diferentes.
CONV_FRAME = "ConveyorReference"
CONV_TARGET = "Get Conveyor"        # ponto de coleta sobre a esteira
CONV_APPROACH = "ConvApproach"      # + letra do robo (ex.: ConvApproachB)

# Fallback (usado SO se a esteira nao for encontrada): pick ao lado do pallet.
PICK_DX = None           # None = centro do pallet em X
PICK_DY = -150.0
# -----------------------------------------------------------------------

RDK = robolink.Robolink()
RDK.setRunMode(robolink.RUNMODE_SIMULATE)


# =========== padroes de amarracao (espelho de planner/patterns.py) ===========
def _base_grid(nx, ny, bx, by):
    return [((i + 0.5) * bx, (j + 0.5) * by, 0.0)
            for j in range(ny) for i in range(nx)]


def layer_positions(pattern, nx, ny, bx, by, layer):
    pos = _base_grid(nx, ny, bx, by)
    if pattern == "brick":
        if layer % 2 == 1:
            pos = [(x + bx / 2.0, y, r) for (x, y, r) in pos]
    elif pattern == "pinhole":
        center = round((ny - 1) / 2.0) * nx + round((nx - 1) / 2.0)
        pos = [p for k, p in enumerate(pos) if k != center]
        if layer % 2 == 1:
            pos = [(x, y, (r + 90.0) % 180.0) for (x, y, r) in pos]
    elif pattern == "split_block":
        mid = nx / 2.0
        pos = [(x, y, 90.0 if ((k % nx < mid) == (layer % 2 == 1)) else 0.0)
               for k, (x, y, r) in enumerate(pos)]
    return pos


# =========== geometria a partir dos params da estacao ===========
def _parse_triplet(value, default):
    try:
        parts = [float(v.replace(" ", "")) for v in str(value).split(",")]
        if len(parts) >= 3:
            return parts[:3]
    except Exception:
        pass
    return default


BX, BY, BZ = _parse_triplet(RDK.getParam("SizeBox"), [100.0, 100.0, 100.0])
size_pallet = _parse_triplet(RDK.getParam("SizePallet"), [3.0, 3.0, float(LAYERS)])
NX, NY = int(size_pallet[0]), int(size_pallet[1])


# =========== itens da estacao ===========
suffix = ROBOT_LETTER.upper()
robot = RDK.Item("UR10 " + suffix, robolink.ITEM_TYPE_ROBOT)
tool = RDK.Item("Gripper" + suffix, robolink.ITEM_TYPE_TOOL)
frame_pallet = RDK.Item("Pallet" + suffix, robolink.ITEM_TYPE_FRAME)
target_safe = RDK.Item("PalletApproach" + suffix, robolink.ITEM_TYPE_TARGET)
partref = RDK.Item("box100mm")

for label, item in [("UR10 " + suffix, robot), ("Pallet" + suffix, frame_pallet),
                    ("box100mm", partref)]:
    if not item.Valid():
        raise Exception("Item '%s' nao encontrado na estacao. Ajuste os nomes no topo." % label)

# esteira (fonte do pick)
frame_conv = RDK.Item(CONV_FRAME, robolink.ITEM_TYPE_FRAME)
target_conv = RDK.Item(CONV_TARGET, robolink.ITEM_TYPE_TARGET)
conv_safe = RDK.Item(CONV_APPROACH + suffix, robolink.ITEM_TYPE_TARGET)
use_conveyor = frame_conv.Valid() and target_conv.Valid()

has_pallet_safe = target_safe.Valid()

# --- define onde e como fazer o pick ---
if use_conveyor:
    pick_frame = frame_conv
    pick_safe = conv_safe if conv_safe.Valid() else None
    pick_tool = target_conv.Pose() * robomath.transl(0, 0, -BZ / 2.0)  # pose de coleta na esteira
    box_local = robomath.transl(*pick_tool.Pos())                      # caixa upright sobre a esteira
    print("Pick: ESTEIRA ('%s')." % CONV_TARGET)
else:
    pick_frame = frame_pallet
    pick_safe = target_safe if has_pallet_safe else None
    px = (NX * BX / 2.0) if PICK_DX is None else PICK_DX
    pick_tool = robomath.transl(px, PICK_DY, BZ / 2.0) * robomath.rotx(robomath.pi)
    box_local = robomath.transl(px, PICK_DY, BZ / 2.0)
    print("Pick: esteira nao encontrada; usando ponto ao lado do pallet (%.0f, %.0f)."
          % (px, PICK_DY))

pick_app = pick_tool * robomath.transl(0, 0, -(APPROACH + BZ))


# =========== limpa caixas anteriores ===========
RDK.Render(False)
for obj in RDK.ItemList(robolink.ITEM_TYPE_OBJECT, False):
    if obj.Name().startswith("Caixa "):
        obj.Delete()
partref.Copy()

if MOVE_ROBOT and tool.Valid():
    robot.setPoseTool(tool)


# =========== helpers ===========
def new_box(index, layer):
    part = frame_pallet.Paste()
    part.Scale([BX / 100.0, BY / 100.0, BZ / 100.0])
    part.setName("Caixa %d" % index)
    part.Recolor([0.2, 0.5, 0.2 + 0.6 * (layer % 2), 1])
    part.setVisible(True, False)
    return part


def rotz(deg):
    return robomath.rotz(robomath.pi * deg / 180.0)


def snap(part, x, y, z, rot_z):
    part.setParentStatic(frame_pallet)
    part.setPose(robomath.transl(x, y, z) * rotz(rot_z))


# =========== execucao ===========
count = 0
reach_fail = 0
first_error_shown = False
for layer in range(LAYERS):
    z_center = (layer + 0.5) * BZ
    for (x, y, rot_z) in layer_positions(PATTERN, NX, NY, BX, BY, layer):
        count += 1
        part = new_box(count, layer)

        if not MOVE_ROBOT:
            snap(part, x, y, z_center, rot_z)
            continue

        # a caixa surge no ponto de coleta (esteira)
        part.setParent(pick_frame)
        part.setPose(box_local)
        RDK.Render(True)

        place = robomath.transl(x, y, z_center) * robomath.rotx(robomath.pi) * rotz(rot_z)
        place_app = place * robomath.transl(0, 0, -(APPROACH + BZ))

        try:
            # PEGA na esteira
            robot.setPoseFrame(pick_frame)
            if pick_safe is not None:
                robot.MoveJ(pick_safe)
            robot.MoveJ(pick_app)
            robot.MoveL(pick_tool)
            part.setParentStatic(tool)      # anexa a caixa a garra
            robot.MoveL(pick_app)
            # SOLTA no pallet
            robot.setPoseFrame(frame_pallet)
            if has_pallet_safe:
                robot.MoveJ(target_safe)
            robot.MoveJ(place_app)
            robot.MoveL(place)
            snap(part, x, y, z_center, rot_z)  # encaixa exato
            robot.MoveL(place_app)
        except Exception as exc:
            reach_fail += 1
            snap(part, x, y, z_center, rot_z)
            if not first_error_shown:
                print("ERRO de movimento na caixa %d: %s" % (count, exc))
                print("  -> verifique alcance do pick/place ou os nomes da esteira no topo.")
                first_error_shown = True

if MOVE_ROBOT and has_pallet_safe:
    try:
        robot.setPoseFrame(frame_pallet)
        robot.MoveJ(target_safe)
    except Exception:
        pass

RDK.Render(True)
print("Padrao '%s': %d caixas, %d camada(s), %d falha(s) de alcance."
      % (PATTERN, count, LAYERS, reach_fail))
