"""Nomes dos itens da estação RoboDK (mapeados a partir de ``robodk_sync/programs``).

Centraliza as strings usadas com ``RDK.Item(...)`` para que a estação possa mudar de nomes
sem tocar na lógica do adaptador. Os defaults correspondem ao robô B (o que paletiza, em
``RobotB_StoreParts.py``); troque para o robô A conforme a cena.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StationItems:
    robot: str = "UR10 B"
    tool: str = "GripperB"
    frame_pallet: str = "PalletB"
    target_pallet_safe: str = "PalletApproachB"
    box_reference: str = "box100mm"

    @classmethod
    def robot_a(cls) -> "StationItems":
        return cls(
            robot="UR10 A",
            tool="GripperA",
            frame_pallet="PalletA",
            target_pallet_safe="PalletApproachA",
        )
