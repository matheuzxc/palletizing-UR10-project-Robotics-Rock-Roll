# Tutorial — Entendendo o código do Paletizador UR10

Guia para a equipe entender como o software funciona. Responde a 4 perguntas:
1. Estrutura de código
2. Como são feitas as paletizações
3. As paletizações estão generalizadas?
4. Qual protocolo de comunicação é usado

---

## 1. Estrutura de código

O código vive em `palletizing-UR10-project-Robotics-Rock-Roll/palletizer/` e é dividido em
camadas, cada uma com **uma responsabilidade**. A ideia central: uma paletização é
**descrita como dados** e depois **renderizada** de duas formas (simulação e robô real).

```
palletizer/
  config/     O QUE paletizar  → modelos de dados + salvar/carregar JSON
  planner/    ONDE vão as caixas → motor de padrões + "plano" (lista de posições)
  motion/     COMO falar com o robô real → gera o texto URScript
  comm/       CANAL com o robô real → socket TCP + leitura de estado
  robodk/     SIMULAÇÃO → dirige a estação RoboDK pela API
  setup/      CALIBRAÇÃO → captura de pontos (freedrive) + parâmetros
  app/        ORQUESTRAÇÃO → junta tudo, máquina de estados
  gui/        TELAS do operador (PyQt)
```

### O fluxo de dados (a espinha dorsal)

Tudo gira em torno de **uma fonte de verdade única**: o *plano*. Ele é calculado uma vez e
alimenta os dois "renderizadores".

```
   CONFIG                PLANNER                    RENDERIZADORES
┌───────────┐   build_plan()   ┌───────────┐    ┌──────────────────────┐
│ nx, ny,   │ ───────────────► │  PLANO    │ ─┬─► motion/urscript.py    │──► TCP ──► UR10 real
│ camadas,  │                  │ (lista de │  │  (texto URScript)       │        (ou URSim)
│ caixa,    │                  │  posições)│  │                         │
│ formato   │                  │           │  └─► robodk/adapter.py     │──► API ──► RoboDK (sim)
└───────────┘                  └───────────┘     (MoveJ / MoveL)
```

Por que separar assim? Porque o trabalho exige **calibração centralizada** e que a
**simulação e o robô real façam a mesma coisa**. Com uma fonte única, os dois lados nunca
divergem: mudou o padrão → muda o plano → mudam os dois renderizadores juntos.

### Arquivos-chave para ler primeiro (nesta ordem)

| Ordem | Arquivo | O que entender |
|---|---|---|
| 1 | `config/models.py` | `PalletizationConfig` = tudo que descreve uma paletização |
| 2 | `planner/patterns.py` | as 4 amarrações (grid/brick/pinhole/split_block) |
| 3 | `planner/plan.py` | como as camadas viram uma lista ordenada de `PlaceSlot` |
| 4 | `motion/urscript.py` | como o plano vira texto URScript |
| 5 | `comm/ur_socket.py` | como o texto é enviado por TCP |

---

## 2. Como são feitas as paletizações

Em **3 etapas**.

### Etapa A — o padrão calcula as posições de UMA camada

`planner/patterns.py` → `layer_positions(pattern, box, pallet, layer)` devolve uma lista de
`(x, y, rot_z)`: o **centro** de cada caixa, em milímetros, **relativo ao canto do pallet**.

A base é uma grade (igual ao `box_calc` da estação RoboDK):

```python
# caixa i na coluna, j na linha → centro em (i+0.5)*largura, (j+0.5)*profundidade
[((i + 0.5) * bx, (j + 0.5) * by, 0.0) for j in range(ny) for i in range(nx)]
```

Cada **amarração** é uma variação dessa grade que muda conforme a camada:
- **grid**: todas as camadas iguais (coluna direta).
- **brick**: camadas ímpares deslocadas meia-caixa em X → as juntas verticais não se alinham.
- **pinhole**: remove a caixa central (o "furo") e gira 90° em camadas alternadas.
- **split_block**: metade esquerda e direita com orientações opostas, trocando por camada.

### Etapa B — empilhar as camadas vira o "plano"

`planner/plan.py` → `build_plan(config)` percorre cada camada, calcula a **altura** de cada
uma (Z dinâmico) e monta a lista final ordenada:

```python
z_center = (layer + 0.5) * box.height     # topo acumulado das camadas de baixo + meia caixa
```

O resultado é um `PalletizationPlan` = lista de `PlaceSlot(seq, layer, x, y, z, rot_z)`.
Essa lista **é** a paletização. Nada depende de robô ainda — é pura geometria, e por isso
dá para **testar sem hardware** (temos 38 testes automáticos disso).

### Etapa C — renderizar o plano

- **Robô real** → `motion/urscript.py` transforma cada slot em comandos URScript. As posições
  do pallet saem do canto ensinado via `pose_trans` (frame do pallet), e a **aproximação**
  é calculada a partir do topo da camada (nunca um valor fixo → previne colisão):
  ```python
  movej(p_pallet_app, ...)                # transição aérea
  movel(p_place_app, ...)                 # desce até a aproximação (linear)
  if (is_within_safety_limits(p_place)):  # trava de segurança
      movel(p_place, ...)                 # descida final
  ```
- **Simulação** → `robodk/adapter.py` faz o mesmo caminho na estação RoboDK com
  `robot.MoveJ(...)` / `robot.MoveL(...)`, relativo ao `frame_pallet`.

> O macro `robodk_sync/programs/PalletizePreview.py` é uma versão **autossuficiente** dessas
> mesmas 3 etapas, para rodar dentro do RoboDK sem instalar nada.

---

## 3. As paletizações estão generalizadas?

**Sim**, em três sentidos — com algumas ressalvas honestas.

**Generalizado por parâmetros:** a mesma lógica serve qualquer ambiente mudando só a config —
`nx`, `ny`, `layers`, tamanho da caixa e o formato. Nada de posições fixas gravadas no código.

**Generalizado por "plugin" de padrão:** adicionar um novo formato é **uma função + uma
linha**. Em `patterns.py` existe um despachante:

```python
_DISPATCH = {
    PatternType.GRID: ...,
    PatternType.BRICK: _brick,
    PatternType.PINHOLE: _pinhole,
    PatternType.SPLIT_BLOCK: _split_block,
}
```

Para criar um padrão novo (ex.: "pinwheel"): escreva `_pinwheel(box, pallet, layer)`, adicione
o valor no enum `PatternType` e registre no `_DISPATCH`. O resto (plano, URScript, RoboDK,
GUI) funciona sem tocar em mais nada — é essa a vantagem da fonte única.

**Generalizado por coordenadas relativas:** tudo é relativo ao **frame do pallet**. Trocou o
pallet de lugar? Basta reensinar o canto (freedrive) ou mover o frame no RoboDK; as posições
se recalculam sozinhas.

### Ressalvas (para não vender demais)

- As amarrações são **heurísticas** pensadas para **caixas ~cúbicas** (como o `box100mm`). Com
  caixas bem retangulares + rotação (split_block/pinhole), a checagem de sobreposição precisa
  ser revista.
- `pinhole` remove **uma** caixa central; num pallet par isso é uma simplificação.
- Não há (ainda) otimização de empacotamento nem detecção de alcance/colisão real — isso é o
  RoboDK que valida na simulação.

---

## 4. Qual protocolo de comunicação é usado

Há **dois canais**, um para cada renderizador.

### Canal 1 — Robô real (e URSim): TCP + URScript

- **Protocolo:** socket **TCP/IP** puro para a porta **30003** do controlador UR (a interface
  *realtime*). É o padrão da Universal Robots para controle remoto — sem ROS, sem RTDE.
- **Envio:** o software manda **texto URScript** (UTF-8, uma linha por comando):
  ```
  movej(p_home, a=..., v=...)
  ```
  Está em `comm/ur_socket.py` (`URConnection.send`). A conexão é **reutilizada** e
  **serializada** (um `Lock`) para nunca haver dois comandos sobrepostos no robô — segurança.
- **Leitura de estado:** a porta 30003 transmite um **pacote binário** contínuo. A pose atual
  do TCP está num offset fixo (bytes **252:300** = 6 doubles big-endian), usado na captura por
  freedrive. Está em `comm/ur_state.py`. Isso foi validado no `base.py` original.
- **Importante:** o **mesmo canal serve o robô real e o URSim** (o simulador da UR fala o mesmo
  protocolo na 30003). Basta trocar o IP.

### Canal 2 — Simulação RoboDK: API Python (Robolink)

- `robodk/adapter.py` usa `Robolink()` (pacote `robodk`). Por baixo, a API também fala TCP com
  o RoboDK (localhost, porta ~20500), mas isso fica **abstraído**: você chama `robot.MoveJ(...)`
  e o RoboDK anima. Aqui **não** há URScript — é a API do RoboDK dirigindo a estação.

### Resumo dos protocolos

| Destino | Como | Onde no código |
|---|---|---|
| UR10 real / URSim | Socket TCP porta 30003, texto URScript + pacote realtime | `comm/`, `motion/urscript.py` |
| Simulação RoboDK | API Python `robodk` (Robolink, TCP interno abstraído) | `robodk/adapter.py` |
| Macro no RoboDK | API `robolink`/`robomath` de dentro do RoboDK | `PalletizePreview.py` |

> Detalhe de projeto ainda em aberto (D1, que discutimos): usar o RoboDK **como motor** (API) ou
> mandar URScript por TCP também para a simulação (URSim). Os dois canais existem no código; a
> escolha do grupo define qual vira o principal.

---

## Mapa mental de 1 minuto

> Uma **config** descreve o quê. O **planner** transforma isso numa **lista de posições**
> (o plano). Essa lista é renderizada em **URScript** (vai por **TCP** ao robô real/URSim) ou
> em **movimentos RoboDK** (pela **API**, na simulação). Trocar de padrão ou de ambiente é
> trocar dados de entrada — o resto se recalcula.
