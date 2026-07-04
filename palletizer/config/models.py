"""Modelos de dados de uma paletização.

Uma ``PalletizationConfig`` descreve TUDO que o operador precisa para adaptar o robô a um
ambiente novo: rede, pontos ensinados, geometria do pallet/caixa, formato de amarração e
parâmetros de movimento. É serializável para JSON (ver :mod:`palletizer.config.store`).

Convenções de unidade:
- Dimensões de caixa/pallet em **milímetros** (como no ``box_calc`` da estação RoboDK).
- Poses ensinadas em **metros e radianos** ``[x, y, z, rx, ry, rz]`` (formato ``get_actual_tcp_pose``).
- Velocidades/acelerações no sistema do URScript (linear m/s, m/s²; junta rad/s, rad/s²).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List

# Incrementar quando a estrutura mudar de forma incompatível. O store recusa versões que
# não sabe migrar, protegendo configs salvas de operadores (risco migration_rollback).
SCHEMA_VERSION = 1


class PatternType(str, Enum):
    """Formatos de amarração suportados pelo motor de padrões."""

    GRID = "grid"           # coluna direta, sem amarração (referência)
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
    approach_height: float = 0.15  # altura de aproximação vertical (m) acima do topo


@dataclass
class BoxSpec:
    """Dimensões da caixa em mm."""

    length: float = 100.0  # X
    width: float = 100.0   # Y
    height: float = 100.0  # Z


@dataclass
class PalletSpec:
    """Grade do pallet: contagens de caixas por eixo (como ``pallet_x/y/z`` do box_calc)."""

    nx: int = 3       # caixas ao longo de X
    ny: int = 3       # caixas ao longo de Y
    layers: int = 2   # nº de camadas (mínimo 2 exigido no trabalho)
    length: float = 800.0  # dimensão física do pallet em mm (informativo/validação)
    width: float = 600.0


@dataclass
class TaughtPoint:
    """Pose capturada por freedrive. ``pose`` = [x, y, z, rx, ry, rz] (m, rad)."""

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
    # Pontos ensinados por nome: pick, pick_approach, pallet_corner, pallet_approach, home.
    points: Dict[str, TaughtPoint] = field(default_factory=dict)

    # -- serialização --------------------------------------------------------------
    def to_dict(self) -> dict:
        data = asdict(self)
        data["pattern"] = self.pattern.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "PalletizationConfig":
        version = data.get("schema_version", 0)
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version {version} incompatível (esperado {SCHEMA_VERSION}); "
                "config salva por outra versão do software."
            )
        points = {
            name: TaughtPoint(**tp) if not isinstance(tp, TaughtPoint) else tp
            for name, tp in data.get("points", {}).items()
        }
        return cls(
            name=data["name"],
            schema_version=SCHEMA_VERSION,
            robot=RobotConfig(**data.get("robot", {})),
            motion=MotionParams(**data.get("motion", {})),
            box=BoxSpec(**data.get("box", {})),
            pallet=PalletSpec(**data.get("pallet", {})),
            pattern=PatternType(data.get("pattern", "grid")),
            points=points,
        )
