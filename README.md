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
