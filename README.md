# Paletizador UR10 — Robotics Rock & Roll

Software em Python para o **operador** configurar e rodar paletizações no **UR10**, com a
**API do RoboDK** como motor de padrões (simulação) e **URScript por socket** para o robô
real. Ver a arquitetura em [`docs/arquitetura.md`](docs/arquitetura.md), o tutorial do código em
[`docs/tutorial.md`](docs/tutorial.md) e o plano em
[`plans/palletizer-ur10-plan.md`](plans/palletizer-ur10-plan.md).

## Estrutura

```
palletizer/
  config/    modelos + persistência JSON de várias paletizações nomeadas
  setup/     captura de pontos por freedrive + calibração central
  planner/   motor de padrões (grid/brick/pinhole/split_block) + plano
  robodk/    adaptador que dirige a estação via Robolink() (simulação)
  comm/      socket 30003 (URScript) + leitura de pose (pacote realtime)
  motion/    gerador do palletizer_core.script
  app/       orquestração + máquina de estados (canal serializado)
  gui/       telas PyQt6 do operador
main.py      entry point (GUI, ou --gen para gerar script sem GUI)
tests/       suíte pytest (roda sem RoboDK/PyQt/robô)
```

## Instalação

```bash
pip install -r requirements.txt   # robodk + PyQt6 + pytest
# O núcleo (config/planner/comm/motion) roda só com a stdlib.
```

> A simulação usa a **API do RoboDK** com o RoboDK **aberto** na estação. Para dirigir a
> estação, use um Python com o pacote `robodk` (o embutido `C:/RoboDK/Python-Embedded/python.exe`
> já o traz), ou instale `robodk` no seu venv.

## Uso

```bash
python main.py                       # abre a GUI (1. Config → 2. Ensino → 3. Simular/Executar)
python main.py --list                # lista as configs salvas em configs/
python main.py --gen NOME            # gera scripts/palletizer_core.script da config NOME
```

Fluxo do operador:
1. **Configuração** — escolher/editar formato, contagens do pallet, tamanho da caixa, IP; salvar.
2. **Ensino (freedrive)** — ligar o freedrive, posicionar o robô à mão e capturar cada ponto
   (`home`, `pick`, `pick_approach`, `pallet_corner`, `pallet_approach`).
3. **Simular / Executar** — simular no RoboDK, gerar/salvar o `.script` ou enviar ao robô.

## Comunicação e calibração (mapeamento de rede)

- **IP/porta padrão:** `192.168.0.10:30003` (interface realtime do UR — envio de URScript e
  leitura de estado). Ajuste na tela de Configuração ou no JSON da config.
- **Leitura de pose (freedrive):** a pose TCP atual é lida do pacote realtime no offset
  `252:300` (6 doubles), validado em `base.py`. Confirme o offset para a versão do controlador
  do laboratório antes da demonstração.
- **Calibração central:** `v_nominal`, `a_nominal`, `v_joint`, `a_joint`, `blend_radius` e
  `approach_height` ficam em `MotionParams` e são emitidos no topo do `.script`.
- **Movimentos:** `movej` nas transições/home, `movel` na descida/recuo, `blend_radius` nos
  trechos aéreos; altura de aproximação derivada do topo acumulado da camada (colisão ativa).

## Formatos de paletização

`grid` (coluna), `brick` (meia-caixa alternada), `pinhole` (centro vazio + rotação alternada),
`split_block` (metades com orientações opostas, alternando por camada). Multi-camadas com Z
dinâmico (mínimo 2 camadas).

## Testes

```bash
python -m pytest -q     # 38 testes; smoke da GUI é pulado se PyQt6 não estiver instalado
```

## Entregáveis do trabalho

- [x] Código-fonte Python (este pacote) + `palletizer_core.script` gerado.
- [ ] Cena 3D RoboDK (macros em `robodk_sync/`; sincronização por `sync_robodk.py`; preview em `robodk_sync/programs/PalletizePreview.py`).
- [ ] Vídeo demonstrativo (≤15 min) — link a inserir.
- [ ] Repositório GitHub — link a inserir.

## Pendências para hardware real (validar no laboratório)

- Confirmar o offset `252:300` na versão do controlador do UR10 do lab.
- Mapear a saída digital real da garra em `gripper()` (hoje `set_digital_out(0, ...)`).
- Reconciliar o frame do pallet ensinado (freedrive) com o `frame_pallet` da estação RoboDK.
