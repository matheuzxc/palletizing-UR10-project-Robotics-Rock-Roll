# PalletizePreview — roda DENTRO do RoboDK e paletiza com ciclo pick -> place real.
#
# Todos os parametros (tamanho da caixa, pallet, pontos de pick/approach, cantos
# do pallet, etc.) sao lidos do arquivo configs/ursim.json para manter a simulacao
# identica ao programa do robo real / URSim.
#
# COMO RODAR: arraste este arquivo para a janela do RoboDK (ou Tools > Run Script) e Play.

from robodk import robolink, robomath
import math
import json
import os

# ----------------------------- CONFIG FILE ---------------------------------
def _find_config():
    """Procura configs/ursim.json em varios locais possiveis."""
    candidates = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(script_dir, "..", "..", "configs", "demo.json"))
    try:
        _rdk = robolink.Robolink()
        station_path = _rdk.getParam("PATH_OPENSTATION")
        if station_path:
            candidates.append(os.path.join(os.path.dirname(station_path), "configs", "demo.json"))
    except Exception:
        pass
    try:
        _rdk = robolink.Robolink()
        proj_path = _rdk.getParam("PROJECT_PATH")
        if proj_path:
            candidates.append(os.path.join(proj_path, "configs", "demo.json"))
    except Exception:
        pass
    for path in candidates:
        norm = os.path.normpath(path)
        if os.path.isfile(norm):
            return norm
    raise FileNotFoundError(
        "Config nao encontrado em nenhum dos caminhos:\n" +
        "\n".join("  - " + os.path.normpath(c) for c in candidates)
    )

_CONFIG_PATH = _find_config()
with open(_CONFIG_PATH, "r") as f:
    CFG = json.load(f)

# ----------------------------- PARAMETROS DO CONFIG -------------------------
# Caixa (mm)
BX = CFG["box"]["length"]
BY = CFG["box"]["width"]
BZ = CFG["box"]["height"]

# Pallet (grid)
NX = CFG["pallet"].get("nx")
NY = CFG["pallet"].get("ny")
LAYERS = CFG["pallet"]["layers"]

# Padrao de amarracao
PATTERN = CFG.get("pattern", "brick")

# Movimento
MOTION = CFG.get("motion", {})
APPROACH_HEIGHT = MOTION.get("approach_height", 0.15) * 1000.0
APPROACH_DX     = MOTION.get("pallet_approach_offset_xy", 0.05) * 1000.0
APPROACH_DY     = MOTION.get("pallet_approach_offset_xy", 0.05) * 1000.0
ARC_HEIGHT      = MOTION.get("arc_height", 0.40) * 1000.0

# Pontos do demo.json
POINTS = CFG.get("points", {})

def _pose_from_cfg(point_name):
    """Converte ponto demo.json (m, rotation vector) em Pose RoboDK (mm)."""
    p = POINTS[point_name]["pose"]
    x, y, z = p[0]*1000, p[1]*1000, p[2]*1000
    rx, ry, rz = p[3], p[4], p[5]
    angle = math.sqrt(rx*rx + ry*ry + rz*rz)
    if angle < 1e-6:
        return robomath.transl(x, y, z)
    kx, ky, kz = rx/angle, ry/angle, rz/angle
    c, s, v = math.cos(angle), math.sin(angle), 1-math.cos(angle)
    from robodk.robomath import Mat
    return Mat([
        [kx*kx*v+c,   kx*ky*v-kz*s, kx*kz*v+ky*s, x],
        [kx*ky*v+kz*s, ky*ky*v+c,   ky*kz*v-kx*s, y],
        [kx*kz*v-ky*s, ky*kz*v+kx*s, kz*kz*v+c,   z],
        [0, 0, 0, 1]
    ])

def _pos_from_cfg(point_name):
    """Retorna so a posicao [x, y, z] em mm de um ponto do ursim.json."""
    p = POINTS[point_name]["pose"]
    return [p[0]*1000, p[1]*1000, p[2]*1000]

# ----------------------------- ROBODK --------------------------------------
ROBOT_LETTER = "B"
MOVE_ROBOT = True
BOX_ITEM_NAME = "box100mm"

RDK = robolink.Robolink()
RDK.setRunMode(robolink.RUNMODE_SIMULATE)

# =========== Cantos do pallet (demo.json, frame base do robo, mm) ===========
if "corners" in CFG["pallet"]:
    _c = CFG["pallet"]["corners"]
    C1 = [_c[0][0]*1000, _c[0][1]*1000, _c[0][2]*1000]
    C2 = [_c[1][0]*1000, _c[1][1]*1000, _c[1][2]*1000]
    C3 = [_c[2][0]*1000, _c[2][1]*1000, _c[2][2]*1000]
    C4 = [_c[3][0]*1000, _c[3][1]*1000, _c[3][2]*1000]
else:
    C1 = _pos_from_cfg("pallet_corner_1")
    C2 = _pos_from_cfg("pallet_corner_2")
    C3 = _pos_from_cfg("pallet_corner_3")
    C4 = _pos_from_cfg("pallet_corner_4")

# Calculo automatico de NX e NY se faltarem
if NX is None or NY is None:
    dist_x = math.sqrt((C1[0]-C2[0])**2 + (C1[1]-C2[1])**2)
    dist_y = math.sqrt((C2[0]-C3[0])**2 + (C2[1]-C3[1])**2)
    NX = int(round(dist_x / BX))
    NY = int(round(dist_y / BY))

# Superficie do pallet (Z medio dos cantos)
PALLET_Z = (C1[2] + C2[2] + C3[2] + C4[2]) / 4.0

# Centro do pallet
PALLET_CX = (C1[0] + C2[0] + C3[0] + C4[0]) / 4.0
PALLET_CY = (C1[1] + C2[1] + C3[1] + C4[1]) / 4.0

print("Pallet corners (mm): C1=(%.0f,%.0f) C2=(%.0f,%.0f) C3=(%.0f,%.0f) C4=(%.0f,%.0f)"
      % (C1[0], C1[1], C2[0], C2[1], C3[0], C3[1], C4[0], C4[1]))
print("Pallet Z=%.0f, centro=(%.0f, %.0f)" % (PALLET_Z, PALLET_CX, PALLET_CY))

def pallet_box_pose(i, j, layer, rot_z_deg=0.0):
    """Calcula a pose de uma caixa no pallet usando interpolacao bilinear
    entre os 4 cantos do demo.json. Retorna pose no frame base do robo."""
    # u, v: posicao normalizada (0..1) dentro do grid
    u = (i + 0.5) / NX
    v = (j + 0.5) / NY
    
    # Interpolacao bilinear entre os 4 cantos
    x = (1-u)*(1-v)*C1[0] + u*(1-v)*C2[0] + u*v*C3[0] + (1-u)*v*C4[0]
    y = (1-u)*(1-v)*C1[1] + u*(1-v)*C2[1] + u*v*C3[1] + (1-u)*v*C4[1]
    z = PALLET_Z + (layer + 0.5) * BZ
    
    # Usa a mesma rotacao da ferramenta definida no ponto de pick
    base_rot = robomath.Mat(pick_pose)
    base_rot.setPos([0,0,0])
    
    rot = robomath.rotz(robomath.pi * rot_z_deg / 180.0)
    return x, y, z, robomath.transl(x, y, z) * base_rot * rot


# =========== padroes de amarracao ===========
def _base_grid(nx, ny):
    """Retorna lista de (i, j, rot_z) para o grid basico."""
    return [(i, j, 0.0) for j in range(ny) for i in range(nx)]

def layer_positions(pattern, nx, ny, layer):
    """Retorna lista de (i, j, rot_z_deg) para cada caixa na camada."""
    pos = _base_grid(nx, ny)
    if pattern == "brick":
        if layer % 2 == 1:
            # Offset de meio box em X (simula brick deslocando u em +0.5/nx)
            pass  # O offset sera aplicado no pallet_box_pose com u ajustado
    elif pattern == "pinhole":
        center = round((ny - 1) / 2.0) * nx + round((nx - 1) / 2.0)
        pos = [p for k, p in enumerate(pos) if k != center]
        if layer % 2 == 1:
            pos = [(i, j, 90.0) for (i, j, r) in pos]
    elif pattern == "split_block":
        mid = nx / 2.0
        pos = [(i, j, 90.0 if ((k % nx < mid) == (layer % 2 == 1)) else 0.0)
               for k, (i, j, r) in enumerate(pos)]
    return pos


# =========== itens da estacao ===========
suffix = ROBOT_LETTER.upper()
robot = RDK.Item("UR10 " + suffix, robolink.ITEM_TYPE_ROBOT)
tool = RDK.Item("Gripper" + suffix, robolink.ITEM_TYPE_TOOL)
frame_pallet = RDK.Item("Pallet" + suffix, robolink.ITEM_TYPE_FRAME)
partref = RDK.Item(BOX_ITEM_NAME)

for label, item in [("UR10 " + suffix, robot), (BOX_ITEM_NAME, partref)]:
    if not item.Valid():
        raise Exception("Item '%s' nao encontrado na estacao." % label)

# Frame base do robo (TODOS os movimentos sao neste frame)
frame_robot_base = robot.Parent()

# --- Pick: 100% fiel ao demo.json ---
pick_pose = _pose_from_cfg("pick")

# --- Pontos dinâmicos baseados no JSON ---
if "pallet_approach" in POINTS:
    pallet_approach_pose = _pose_from_cfg("pallet_approach")
else:
    # Cria approach generico sobre o pallet
    base_rot = robomath.Mat(pick_pose)
    base_rot.setPos([0,0,0])
    pallet_approach_pose = robomath.transl(PALLET_CX, PALLET_CY, PALLET_Z + 400.0) * base_rot

home_pose = _pose_from_cfg("home")

if "pick_approach" in POINTS:
    pick_approach_pose = _pose_from_cfg("pick_approach")
else:
    # Sobe no Z em relacao a rotacao da ferramenta (a rotacao já inverte Z)
    pick_approach_pose = pick_pose * robomath.transl(0, 0, -MOTION.get("approach_pick_offset_z", 0.15)*1000)

box_local = robomath.transl(*pick_pose.Pos())

print("Pick: Ponto exato do demo.json (%.0f, %.0f, %.0f) mm." % (pick_pose.Pos()[0], pick_pose.Pos()[1], pick_pose.Pos()[2]))


# =========== limpa caixas anteriores ===========
RDK.Render(False)
for obj in RDK.ItemList(robolink.ITEM_TYPE_OBJECT, False):
    if obj.Name().startswith("Caixa "):
        obj.Delete()

if MOVE_ROBOT and tool.Valid():
    robot.setPoseTool(tool)

# =========== Forcar configuracao Elbow Up ===========
# Para evitar que o cotovelo bata nas caixas ao alcancar posicoes baixas,
# inicializamos o robo na solucao IK "Cotovelo para Cima" do home_pose.
if MOVE_ROBOT:
    all_ik = robot.SolveIK_All(home_pose)
    best_ik = None
    try:
        for i in range(all_ik.size(1)):
            jts = [all_ik[k, i] for k in range(6)]
            # Queremos cotovelo para cima (jts[2] > 0)
            # e ombro apontando para frente/cima (-180 < jts[1] < 0)
            if jts[2] > 0 and -180 < jts[1] < 0:
                best_ik = jts
                break
        if best_ik:
            robot.setJoints(best_ik)
    except Exception:
        pass


# =========== helpers ===========
def new_box(index, layer):
    partref.Copy()
    part = frame_robot_base.Paste() if not frame_pallet.Valid() else frame_pallet.Paste()
    part.Scale([BX / 100.0, BY / 100.0, BZ / 100.0])
    part.setName("Caixa %d" % index)
    part.Recolor([0.2, 0.5, 0.2 + 0.6 * (layer % 2), 1])
    part.setVisible(True, False)
    return part


# Angulo do pallet (orientacao da base do pallet)
PALLET_ANGLE = math.atan2(C2[1]-C1[1], C2[0]-C1[0])

def snap(part, pose_place, rot_z_deg=0.0):
    """Posiciona a caixa na posicao final (frame base do robo) com a rotacao certa."""
    part.setParentStatic(frame_robot_base)
    x, y, z = pose_place.Pos()
    # Rotaciona a caixa visualmente para alinhar com o pallet + padrao
    box_rot = robomath.rotz(PALLET_ANGLE + robomath.pi * rot_z_deg / 180.0)
    part.setPose(robomath.transl(x, y, z) * box_rot)


# =========== execucao ===========
count = 0
reach_fail = 0
first_error_shown = False

# TODOS os movimentos no frame base do robo
robot.setPoseFrame(frame_robot_base)

for layer in range(LAYERS):
    for (i, j, rot_z) in layer_positions(PATTERN, NX, NY, layer):
        # Brick offset: desloca meio box em u na camada impar
        i_eff = i
        if PATTERN == "brick" and layer % 2 == 1:
            i_eff = i + 0.5
        
        x, y, z, place_pose = pallet_box_pose(i_eff, j, layer, rot_z)
        count += 1
        part = new_box(count, layer)

        if not MOVE_ROBOT:
            snap(part, place_pose, rot_z)
            continue

        # Caixa surge no ponto de pick
        part.setParent(frame_robot_base)
        box_rot_start = robomath.rotz(PALLET_ANGLE)
        part.setPose(box_local * box_rot_start)
        RDK.Render(True)

        # Approach diagonal fixo no 'lado vazio' (+X, +Y do frame do pallet),
        # garantindo que nao passe por cima das caixas ja empilhadas (como o urscript.py).
        off_x_local = APPROACH_DX
        off_y_local = APPROACH_DY
        
        # Roda o offset (1.0, 1.0) do grid do pallet para as coordenadas do RoboDK
        dx_world = off_x_local * math.cos(PALLET_ANGLE) - off_y_local * math.sin(PALLET_ANGLE)
        dy_world = off_x_local * math.sin(PALLET_ANGLE) + off_y_local * math.cos(PALLET_ANGLE)
        
        app_x = x + dx_world
        app_y = y + dy_world
        app_z = z + APPROACH_HEIGHT + BZ
        rot = robomath.rotz(robomath.pi * rot_z / 180.0)
        place_app = robomath.transl(app_x, app_y, app_z) * base_rot * rot

        try:
            # === PICK ===
            robot.MoveJ(pick_approach_pose)
            robot.MoveL(pick_pose)
            part.setParentStatic(tool)
            robot.MoveL(pick_approach_pose)

            # === TRANSICAO SEGURA: pick → home → pallet_approach ===
            # Passa pelo HOME (posicao centralizada e alta) para evitar
            # arcos perigosos por cima do robo.
            robot.MoveJ(home_pose)
            robot.MoveJ(pallet_approach_pose)

            # === PLACE ===
            robot.MoveJ(place_app)
            robot.MoveL(place_pose)
            snap(part, place_pose, rot_z)
            robot.MoveL(place_app)
            
        except Exception as exc:
            reach_fail += 1
            snap(part, place_pose, rot_z)
            if not first_error_shown:
                import traceback
                print("ERRO de movimento na caixa %d: %r" % (count, exc))
                traceback.print_exc()
                first_error_shown = True

# Volta para home
if MOVE_ROBOT:
    try:
        robot.MoveJ(home_pose)
    except Exception:
        pass

RDK.Render(True)
if MOVE_ROBOT:
    robot.MoveJ(home_pose)

print("Padrao '%s': %d caixas, %d camada(s), %d falha(s) de alcance."
      % (PATTERN, count, LAYERS, reach_fail))
print("Config: %s" % os.path.basename(_CONFIG_PATH))
