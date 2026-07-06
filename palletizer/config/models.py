"""Modelos de dados de uma paletização.

Uma ``PalletizationConfig`` descreve TUDO que o operador precisa para adaptar o robô a um
ambiente novo: rede, pontos ensinados, geometria do pallet/caixa, formato de amarração e
parâmetros de movimento. É serializável para JSON (ver :mod:`palletizer.config.store`).

Convenções de unidade:
- Dimensões de caixa em **milímetros**.
- Cantos do pallet e poses ensinadas em **metros e radianos** (formato ``get_actual_tcp_pose``):
  cantos são ``[x, y, z]`` (chão do pallet); poses são ``[x, y, z, rx, ry, rz]`` com a
  orientação em **vetor de rotação** (estilo PolyScope).
- Velocidades/acelerações no sistema do URScript (linear m/s, m/s²; junta rad/s, rad/s²).

Modelo de entrada (v2):
- Caixa (L/W/H).
- Pallet = **4 cantos** no chão (suporta pallet girado no plano); ``nx``/``ny`` e a área útil são
  DERIVADOS pela caixa (ver :mod:`palletizer.planner.geometry`).
- Pose de pick (ensinada). ``pick_approach`` é DERIVADO (offset vertical), não ensinado.
- Approach do pallet é DINÂMICO por caixa (offset diagonal pelo lado vazio), não um ponto único.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List

# Incrementar quando a estrutura mudar de forma incompatível. v2 troca o pallet de
# (canto único + nx/ny) para 4 cantos, adiciona offsets/atuador e remove pontos derivados.
SCHEMA_VERSION = 2


class PatternType(str, Enum):
    """Formatos de amarração suportados pelo motor de padrões."""

    GRID = "grid"           # coluna direta, sem amarração (base interna reutilizada)
    BRICK = "brick"         # camadas ímpares deslocadas meia-caixa (juntas defasadas)
    PINHOLE = "pinhole"     # centro vazio + orientação girada em camadas alternadas
    SPLIT_BLOCK = "split_block"  # metades com orientações opostas, alternando por camada


@dataclass
class RobotConfig:
    """Endereço do robô/URSim. Porta 30003 = interface realtime (envio + estado)."""

    ip: str = "192.168.0.10"
    port: int = 30003


@dataclass
class MotionParams:
    """Calibração centralizada — emitida no topo do URScript gerado (requisito do trabalho)."""

    v_nominal: float = 0.25   # velocidade linear (m/s) para movel
    a_nominal: float = 0.5    # aceleração linear (m/s²) para movel
    v_joint: float = 0.8      # velocidade de junta (rad/s) para movej
    a_joint: float = 1.2      # aceleração de junta (rad/s²) para movej
    blend_radius: float = 0.02  # raio de concordância (m) nos trechos aéreos
    approach_height: float = 0.15  # folga de aproximação vertical (m) acima do topo acumulado

    # -- compensação de altura no place (calibração do robô real) ----------------------
    # Sobe o Z de TODA caixa ao pousar no pallet, para não esmagar (chão/TCP ensinado baixo).
    # Aplicado só na geração do URScript; NÃO afeta a simulação RoboDK (plano intacto).
    place_offset_z: float = 0.0  # m adicionados ao Z de colocação de cada caixa

    # -- approachPick derivado (offset vertical sobre o ponto pick) --------------------
    approach_pick_offset_z: float = 0.15  # m acima do pick

    # -- approach dinâmico do pallet (offset diagonal pelo lado vazio, por caixa) -------
    pallet_approach_offset_xy: float = 0.10  # m no plano do pallet, direção do lado vazio
    pallet_approach_offset_z: float = 0.05   # m de elevação extra sobre a altura de aproximação

    # -- atuador (ventosas) ------------------------------------------------------------
    gripper_do: int = 0        # saída digital do atuador (D0)
    gripper_hold_s: float = 5.0  # segundos com o atuador ativo para prender a caixa nas ventosas


@dataclass
class BoxSpec:
    """Dimensões da caixa em mm."""

    length: float = 100.0  # X
    width: float = 100.0   # Y
    height: float = 100.0  # Z


def _default_corners() -> List[List[float]]:
    """Retângulo 0.8 x 0.6 m no chão (z=0). Ordem: c0 origem, c1 +X, c2 diagonal, c3 +Y."""
    return [
        [0.0, 0.0, 0.0],   # c0 — origem
        [0.8, 0.0, 0.0],   # c1 — fim do comprimento (eixo X do pallet)
        [0.8, 0.6, 0.0],   # c2 — canto oposto (diagonal)
        [0.0, 0.6, 0.0],   # c3 — fim da largura (eixo Y do pallet)
    ]


@dataclass
class PalletSpec:
    """Pallet por 4 cantos no CHÃO (m). ``nx``/``ny``/área são derivados pela caixa.

    ``corners`` = ``[c0, c1, c2, c3]``, cada um ``[x, y, z]`` em metros:
    - ``c0`` origem, ``c1`` fim do comprimento (eixo X), ``c3`` fim da largura (eixo Y),
      ``c2`` o canto diagonalmente oposto (usado para checagem de consistência).
    """

    corners: List[List[float]] = field(default_factory=_default_corners)
    layers: int = 2   # nº de camadas (mínimo 2 exigido no trabalho)


@dataclass
class TaughtPoint:
    """Pose capturada por freedrive. ``pose`` = [x, y, z, rx, ry, rz] (m, rad, vetor de rotação)."""

    name: str
    pose: List[float] = field(default_factory=lambda: [0.0] * 6)


@dataclass
class PalletizationConfig:
    """Configuração completa e nomeada de uma paletização."""

    name: str
    schema_version: int = SCHEMA_VERSION
    robot: RobotConfig = field(default_factory=RobotConfig)
    motion: MotionParams = field(default_factory=MotionParams)
    box: BoxSpec = field(default_factory=BoxSpec)
    pallet: PalletSpec = field(default_factory=PalletSpec)
    pattern: PatternType = PatternType.GRID
    # Pontos ensinados por nome (v2): apenas ``home`` e ``pick``. ``pick_approach`` é derivado
    # (offset vertical) e o frame do pallet vem dos 4 cantos, não de um ponto ensinado.
    points: Dict[str, TaughtPoint] = field(default_factory=dict)

    # -- serialização --------------------------------------------------------------
    def to_dict(self) -> dict:
        data = asdict(self)
        data["pattern"] = self.pattern.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "PalletizationConfig":
        version = data.get("schema_version", 0)
        if version == SCHEMA_VERSION:
            return cls._from_v2(data)
        if version == 1:
            return cls._from_v2(_migrate_v1_to_v2(data))
        raise ValueError(
            f"schema_version {version} incompatível (esperado {SCHEMA_VERSION}); "
            "config salva por outra versão do software e sem caminho de migração."
        )

    @classmethod
    def _from_v2(cls, data: dict) -> "PalletizationConfig":
        points = {
            name: TaughtPoint(**tp) if not isinstance(tp, TaughtPoint) else tp
            for name, tp in data.get("points", {}).items()
        }
        pallet_data = dict(data.get("pallet", {}))
        # corners pode vir como lista de listas; normaliza para list[list[float]].
        if "corners" in pallet_data:
            pallet_data["corners"] = [[float(v) for v in c] for c in pallet_data["corners"]]
        return cls(
            name=data["name"],
            schema_version=SCHEMA_VERSION,
            robot=RobotConfig(**data.get("robot", {})),
            motion=MotionParams(**data.get("motion", {})),
            box=BoxSpec(**data.get("box", {})),
            pallet=PalletSpec(**pallet_data),
            pattern=PatternType(data.get("pattern", "grid")),
            points=points,
        )


def _migrate_v1_to_v2(data: dict) -> dict:
    """Migra uma config v1 (canto único + nx/ny) para o formato v2 (4 cantos).

    Best-effort (DD7/A3): preserva caixa, movimento, IP, formato, home e pick; converte
    ``length``/``width`` físicos (mm) num retângulo de 4 cantos no chão; descarta os pontos
    derivados (``pick_approach``, ``pallet_approach``) e o antigo ``pallet_corner`` (o frame do
    pallet passa a vir dos 4 cantos). Campos novos recebem defaults do modelo.
    """
    out = dict(data)
    out["schema_version"] = SCHEMA_VERSION

    old_pallet = data.get("pallet", {})
    length_m = float(old_pallet.get("length", 800.0)) / 1000.0
    width_m = float(old_pallet.get("width", 600.0)) / 1000.0
    layers = int(old_pallet.get("layers", 2))
    out["pallet"] = {
        "corners": [
            [0.0, 0.0, 0.0],
            [length_m, 0.0, 0.0],
            [length_m, width_m, 0.0],
            [0.0, width_m, 0.0],
        ],
        "layers": layers,
    }

    # motion: mantém os campos v1 conhecidos; os novos (offsets/atuador) ficam com default.
    old_motion = data.get("motion", {})
    keep = {"v_nominal", "a_nominal", "v_joint", "a_joint", "blend_radius", "approach_height"}
    out["motion"] = {k: v for k, v in old_motion.items() if k in keep}

    # pontos: só home e pick sobrevivem; o resto era ensinado e agora é derivado/geométrico.
    old_points = data.get("points", {})
    out["points"] = {
        name: old_points[name] for name in ("home", "pick") if name in old_points
    }
    return out
