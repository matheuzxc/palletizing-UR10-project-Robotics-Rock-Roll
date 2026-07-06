# [Link para o video](https://youtu.be/yfeCSCjaX8E)


# Paletizador UR10 — Robotics Rock & Roll

Software em **Python** para o operador **configurar e rodar paletizações no UR10**. A mesma
descrição de paletização alimenta dois destinos:

- **Simulação no RoboDK** — a API do RoboDK é o motor de padrões (grid, brick, pinhole,
  split_block) e valida alcance/colisão na estação 3D.
- **Robô real ou URSim** — o plano vira **URScript** enviado por **socket TCP na porta 30003**
  (a mesma interface do UR10 real e do URSim).

O núcleo (config → plano → geração de movimento) é pura geometria e roda **só com a biblioteca
padrão** do Python; PyQt6 é necessário para a GUI e o pacote `robodk` para a simulação.

---

## Requisitos

- **Python 3.12** (ver [`.python-version`](.python-version)).
- Para a **GUI**: `PyQt6`.
- Para a **simulação**: **RoboDK instalado e aberto** na estação desejada, com o pacote
  `robodk` disponível no Python que roda o script.
- Para **executar de verdade**: um **URSim** rodando ou o **UR10 real** acessível na rede
  (porta `30003`).

---

## Instalação

Caminho padrão, com `pip` (não depende do `uv`):

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
```

Alternativa com **uv** (opcional — o projeto também traz `pyproject.toml` + `uv.lock`):

```bash
uv sync
```

> **RoboDK:** para dirigir a estação pela API, use um Python que tenha o pacote `robodk`. O
> Python embutido do RoboDK já o traz: `C:/RoboDK/Python-Embedded/python.exe`. Como alternativa,
> `pip install robodk` (já incluído no `requirements.txt`) instala o pacote no seu venv.

---

## Como executar

### GUI do operador

```bash
python main.py
```

Fluxo: **1. Configuração** (formato, contagens do pallet, tamanho da caixa, IP) → **2. Ensino**
(freedrive: posicionar o robô à mão e capturar `home`/`pick`) → **3. Simular / Executar**.

### Linha de comando (sem GUI — útil para URSim)

```bash
python main.py --list                 # lista as configs salvas em configs/
python main.py --gen NOME             # gera scripts/palletizer_core.script da config NOME
python main.py --send NOME --ip IP    # gera e ENVIA o URScript ao robô/URSim (o robô se move!)
python main.py --read-pose --ip IP    # conecta e imprime a pose TCP atual
```

### Simulação no RoboDK

Com o RoboDK **aberto** na estação, rode o exemplo (dirige o robô via API MoveJ/MoveL):

```bash
python examples/run_robodk_sim.py                                    # robô B, grid 3x3, 2 camadas
python examples/run_robodk_sim.py --robot A --pattern brick --layers 2
```

### Config de exemplo para o URSim

Cria uma config com pontos manuais e gera o `.script` correspondente (edite as poses TODO com
valores alcançáveis no seu URSim):

```bash
python examples/build_ursim_config.py
```

### Sincronizar macros do RoboDK

Os programas Python da estação RoboDK ficam espelhados em `robodk_sync/`. Veja
[`robodk_sync/README.md`](robodk_sync/README.md) para o fluxo `pull`/`push` (requer o Python
embutido do RoboDK).

---

## A config (`configs/demo.json`) e onde ela cai no `.script`

Cada arquivo em `configs/` é uma **config de paletização** (schema v2) — descreve *o quê*
paletizar. `configs/demo.json` é o exemplo de referência. O comando
`python main.py --gen demo` lê essa config, roda o planner e escreve
[`scripts/palletizer_core.script`](scripts/palletizer_core.script). Abaixo, o que cada bloco
significa e **em que ponto do URScript ele reaparece**.

```jsonc
{
  "name": "demo",              // nome da config (arquivo configs/<name>.json)
  "schema_version": 2,         // versão do formato (v1 é migrada automaticamente)
  "robot":   { "ip": "192.168.0.10", "port": 30003 },
  "motion":  { ... },          // calibração de movimento (ver tabela)
  "box":     { "length": 125.0, "width": 125.0, "height": 70.0 },  // mm
  "pallet":  { "corners": [c0, c1, c2, c3], "layers": 2 },         // 4 cantos no chão (m)
  "pattern": "pinhole",        // formato de amarração (grid/brick/pinhole/split_block)
  "points":  { "home": {...}, "pick": {...} }  // poses ensinadas [x,y,z,rx,ry,rz] (m,rad)
}
```

### De onde vem cada linha do `.script`

| Campo na config                 | Onde aparece no `palletizer_core.script`                                             |
|---------------------------------|--------------------------------------------------------------------------------------|
| `robot.ip` / `robot.port`       | **não** entra no script — é usado pela camada `comm` para enviar por TCP (`--send`).  |
| `motion.v_nominal` / `a_nominal`| `v_nominal` / `a_nominal` no topo (usados nos `movel`).                               |
| `motion.v_joint` / `a_joint`    | `v_joint` / `a_joint` no topo (usados nos `movej`).                                   |
| `motion.blend_radius`           | `blend_r` no topo (parâmetro `r=` dos movimentos aéreos).                             |
| `motion.approach_height`        | altura da aproximação sobre a camada — entra no Z de `p_place_app`.                   |
| `motion.place_offset_z`         | somado ao Z de **toda** caixa em `p_place` (não esmagar a caixa no robô real).        |
| `motion.approach_pick_offset_z` | deriva `p_pick_app` (offset vertical sobre `p_pick`).                                 |
| `motion.pallet_approach_offset_xy/z` | offset diagonal + elevação de `p_place_app` (aproxima pelo lado ainda vazio).   |
| `motion.gripper_do`             | `set_digital_out(N, ...)` e o `D<N>` do atuador de ventosas.                          |
| `motion.gripper_hold_s`         | `sleep(...)` dentro de `gripper(True)` (segundos prendendo a caixa).                  |
| `box.length/width/height`       | **não** são impressos, mas definem `nx`/`ny` da grade e os offsets `dx/dy/dz` de cada `p_place`. |
| `pallet.corners`                | `p_pallet` (frame do pallet dos 4 cantos); todo place é `pose_trans(p_pallet, ...)`.  |
| `pallet.layers`                 | cabeçalho `camadas: N` e o nº de caixas empilhadas (Z por camada).                    |
| `pattern`                       | cabeçalho `Formato: ...` e a ordem/rotação das células (`i`, `j`, `rot_z`).           |
| `points.home`                   | `p_home` (ida inicial e retorno final).                                               |
| `points.pick`                   | `p_pick` (descida de coleta).                                                         |

**Exemplo concreto (`demo.json` → script):** o primeiro canto do pallet
`[0.9694, -0.5625, -0.4054]` vira `p_pallet = p[0.969400, -0.562500, -0.405400, ...]`; a caixa
de `125 mm` produz o meio-passo `0.0625` que aparece nos offsets `pose_trans`; e cada `p_place`
é montado **relativo** a `p_pallet`, com o Z somando o topo acumulado da camada + `place_offset_z`.

> O `.script` é um **artefato gerado** — reflete a config no momento do `--gen`. Se você editar
> `demo.json` (pela GUI ou à mão), rode `python main.py --gen demo` de novo para regerá-lo. Por
> isso os números literais do `.script` versionado podem divergir da config atual até você
> regenerar.

---

## Árvore de arquivos

Visão geral por responsabilidade — só os arquivos principais são detalhados pelo nome.

```
.
├── main.py                     # entry point: GUI (sem args) ou CLI (--list/--gen/--send/--read-pose)
├── requirements.txt            # dependências de runtime (pip, sem uv)
├── pyproject.toml / uv.lock    # metadados e lock do projeto (opcional, para quem usa uv)
├── configs/                    # configs de paletização em JSON (uma por ambiente; ignoradas no git)
├── palletizer/                 # pacote da aplicação (o núcleo)
│   ├── config/                 # modelos de dados + persistência JSON das paletizações
│   ├── planner/                # motor de padrões (grid/brick/pinhole/split_block) + plano
│   ├── motion/                 # geração do URScript (palletizer_core.script) a partir do plano
│   ├── comm/                   # socket TCP 30003 (envio URScript) + leitura de pose realtime
│   ├── robodk/                 # adaptador que dirige a estação RoboDK via API (simulação)
│   ├── setup/                  # captura de pontos por freedrive + parâmetros de calibração
│   ├── app/                    # orquestração + máquina de estados do ciclo
│   └── gui/                    # telas PyQt6 do operador
├── examples/
│   ├── run_robodk_sim.py       # roda uma paletização na estação RoboDK aberta
│   └── build_ursim_config.py   # monta uma config + gera o .script para o URSim
└── robodk_sync/                # macros Python da estação RoboDK + sync_robodk.py (ver README próprio)
```

A ideia central: uma **config** descreve *o quê* paletizar; o **planner** transforma isso numa
lista ordenada de posições (o *plano*); o plano é renderizado em **URScript** (vai por TCP ao
robô/URSim) ou em **movimentos RoboDK** (pela API, na simulação). Trocar de padrão ou de
ambiente é trocar dados de entrada — o resto se recalcula.

---

## Comunicação e calibração

- **IP/porta:** a porta é sempre `30003` (interface realtime do UR — envio de URScript e leitura
  de estado). O IP fica na config (ex.: `192.168.2.102` no URSim); ajuste na tela de Configuração,
  no JSON, ou via `--ip`.
- **Leitura de pose (freedrive):** a pose TCP cartesiana atual é lida do pacote realtime no
  offset de bytes `444:492` (6 doubles). Confirme o offset para a versão do controlador antes de
  usar em hardware real.
- **Calibração central:** velocidades, acelerações, `blend_radius` e altura de aproximação ficam
  centralizados e são emitidos no topo do `.script` gerado.
- **Movimentos:** `movej` nas transições/home, `movel` na aproximação/descida/recuo, com
  `blend_radius` nos trechos aéreos e altura de aproximação derivada do topo acumulado da camada.

## Formatos de paletização

`grid` (coluna), `brick` (meia-caixa alternada), `pinhole` (centro vazio + rotação alternada) e
`split_block` (metades com orientações opostas por camada). Suporta múltiplas camadas com Z
dinâmico (mínimo 2 camadas).

---

## Entregáveis

- Código-fonte Python (este pacote) + `palletizer_core.script` gerado.
- Cena 3D do RoboDK (macros espelhados em `robodk_sync/`).
- Vídeo demonstrativo (≤15 min) — _link a inserir_.
- Repositório GitHub — _link a inserir_.
