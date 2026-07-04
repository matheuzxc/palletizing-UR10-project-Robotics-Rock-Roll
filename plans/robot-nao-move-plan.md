# Plan: Corrigir "o robô não se move" ao enviar o URScript ao URSim

**Status:** `READY_FOR_EXECUTION`
**Agent:** Planner
**Schema Version:** `1.2.0`
**Complexity Tier:** `MEDIUM`
**Confidence:** `0.90`
**Abstain:** `is_abstaining: false`
**Summary:** A comunicação TCP/IP com o URSim já funciona (freedrive, leitura de pose e comandos simples chegam pela porta 30003), mas ao enviar o programa gerado o robô fica parado. A causa provável é o **formato do URScript gerado** em `palletizer/motion/urscript.py`: ele é emitido como uma sequência de instruções de escopo global — atribuições de variáveis, duas definições `def ... end` (`gripper`, `palletize`) e uma chamada global final `palletize()`. As interfaces cliente do UR (30001/30002/30003) só executam **um** programa recebido, e a forma idiomática/confiável é um **único bloco `def nome(): ... end` no topo** (o controlador roda esse `def` automaticamente ao recebê-lo). Instruções globais soltas + múltiplos `def` + chamada global não são executadas de forma confiável → o robô não se move, sem falha nem movimento — exatamente o sintoma relatado. O plano confirma a hipótese com um envio mínimo isolado, depois refatora o gerador para emitir um único `def` de topo (sem chamada global), atualiza os testes afetados e valida em loop com o URSim.

## Context & Analysis

Fatos verificados no repositório (não suposições):

- **Ambos os caminhos de envio** passam pelo mesmo gerador. `main.py --send` (linhas 57-69) e a GUI `RunScreen.on_send` ([palletizer/gui/run_screen.py:62](palletizer/gui/run_screen.py)) chamam `PalletizerController.send_to_robot` → `build_urscript` → `generate_script`. Corrigir o gerador corrige os dois.
- **O gerador emite escopo global** ([palletizer/motion/urscript.py:53-108](palletizer/motion/urscript.py)): `v_nominal = ...`, `def gripper(state): ... end`, `def palletize(): ... end`, e por fim `palletize()` no nível global. Não há um `def` de topo único que envolva o programa.
- **O envio é um único `sendall`** com `\n` garantido ([palletizer/comm/ur_socket.py:61-67](palletizer/comm/ur_socket.py)); o socket é **fechado imediatamente** após o envio nos dois caminhos (`with URConnection(...) as conn: ...` em [main.py:66](main.py) e [run_screen.py:71](palletizer/gui/run_screen.py)). Não há pausa/flush antes do `close()`.
- **Parâmetros de movimento têm defaults não-nulos** ([palletizer/config/models.py:42-50](palletizer/config/models.py)): `v_nominal=0.25`, `a_nominal=0.5`, `v_joint=0.8`, `a_joint=1.2`, `blend_radius=0.02`. O `examples/build_ursim_config.py` só sobrescreve `v_nominal` e `approach_height`; os demais permanecem nos defaults. **Isto descarta** a hipótese "velocidade/aceleração zero".
- **A porta aceita scripts** — a referência validada pelo grupo, `base.py`, envia `freedrive_mode()` e comandos simples pela 30003 e a "comunicação funciona". Isso prova que o URSim **não** está em modo Local/Remote bloqueando scripts; apenas prova que comandos simples rodam, **não** que um programa multi-instrução global roda.
- **O `movej(p_home, ...)` inicial não é protegido** por `is_within_safety_limits` (só os `place` são, [urscript.py:99](palletizer/motion/urscript.py)). Se o programa estivesse rodando, o robô ao menos iria para `home`. Ele não se move de todo → consistente com o programa **nunca iniciar**, não com poses inalcançáveis.
- **Testes existentes acoplados ao formato atual** ([tests/test_urscript.py](tests/test_urscript.py)): `test_params_emitted_at_top` fatia em `script.index("def palletize")`; `test_starts_and_ends_at_home` exige `script.rstrip().endswith("palletize()")`. Ambos mudarão com a refatoração e precisam ser atualizados.

Requisitos e limites que moldam o plano:

- Preservar a semântica de movimento existente: `movej` nas transições/home, `movel` nas descidas/recuos, `pose_trans` no frame do pallet, guarda `is_within_safety_limits` no place, parâmetros de calibração no topo (requisito DD4 do trabalho).
- Não alterar o planner, os padrões, o adaptador RoboDK nem os modelos de config.
- A validação final é **hardware-in-the-loop no URSim** e depende do usuário (o planejador/executor não alcança o URSim do laboratório).

## Design Decisions

### Architectural Choices

- **Envolver todo o programa em um único `def` de topo** (ex.: `def palletizer_prog(): ... end`) sem chamada global final. Racional: as interfaces cliente do UR executam automaticamente uma definição de função recebida como "o programa"; é o formato usado por bibliotecas consolidadas (urx, ur_rtde em modo script, driver UR do RoboDK). Move-se as atribuições de parâmetros e o `def gripper` para **dentro** do bloco (variáveis/funções locais são válidas em URScript), e inlina-se o corpo de `palletize` no mesmo `def`.
- **Manter o gerador puro** (retorna string; não envia) — inalterado. A mudança é só na forma do texto emitido.

### Boundary & Integration Points

- Contrato de saída de `generate_script` muda de forma (mesma função, texto diferente). Consumidores: `controller.build_urscript`/`save_urscript`, `RunScreen`, `main.py --gen/--send`, e os testes de `test_urscript.py`. Nenhuma assinatura de função muda; apenas o conteúdo do script e as asserções de teste.
- Nenhuma mudança no protocolo de socket nem no formato do pacote realtime.

### Temporal Flow

Sequência (ondas):
1. **Onda 1 — Isolamento (spike):** confirmar empiricamente a hipótese enviando um `def` mínimo ao URSim e comparando com o formato atual. Gate humano: o usuário reporta se o `def` mínimo move e o formato atual não.
2. **Onda 2 — Correção do gerador + testes** (só após a Onda 1 confirmar).
3. **Onda 3 — Robustez de envio** (pausa/flush antes do `close`), condicional ao que a Onda 1 revelar.
4. **Onda 4 — Validação end-to-end no URSim** (gate humano).

### Constraints & Trade-offs

- **Spike antes de refatorar:** há incerteza residual sobre fatores do lado do URSim; um envio isolado de baixo custo confirma a causa raiz antes de mexer no gerador, evitando refatorar sobre um diagnóstico errado.
- **`gripper` como função aninhada:** URScript aceita `def` aninhado dentro de `def`; alternativa (inlinar `set_digital_out`+`sleep` a cada uso) foi descartada por poluir o script e perder o ponto único de mapeamento da garra (TODO já documentado).
- **Não trocar de porta:** manter 30003 (a referência do grupo e a leitura de pose usam essa porta). Trocar para 30002 é desnecessário se o wrapping resolve.

## Implementation Phases

### Phase 1 - Isolar e confirmar a causa raiz no URSim (spike)

- **Objective:** Provar (ou refutar) que o problema é o formato global vs. `def` de topo, antes de refatorar.
- **Owner:** local (prepara os snippets) + usuário (executa contra o URSim).
- **Wave:** 1
- **Dependencies:** URSim acessível no IP configurado (`examples/build_ursim_config.py` usa `192.168.2.103`; `main.py --read-pose` assume `192.168.2.102` — confirmar o IP real primeiro).
- **Files:** criar `scripts/_probe_min.script` (temporário) com apenas:
  ```
  def probe():
    movej(p[<home real>], a=1.2, v=0.8)
  end
  ```
  e comparar com o `scripts/palletizer_core.script` atual (formato global).
- **Tests:** nenhum automatizado; teste manual de envio.
- **Steps:**
  1. Confirmar o IP/porta reais do URSim e alinhar `examples/build_ursim_config.py` (hoje `192.168.2.103`) com o que responde a `python main.py --read-pose --ip <IP>`.
  2. Enviar o `def probe()` mínimo (via um envio pontual usando `URConnection`), usando a pose `home` já configurada. Observar se o robô vai para home.
  3. Enviar o `scripts/palletizer_core.script` atual (formato global) e observar que **não** move.
- **Acceptance Criteria:** O `def` mínimo move o robô; o script de formato global não. (Se o `def` mínimo **também** não mover, a causa é outra — ver Failure Expectations.)
- **Quality Gates:** human_approved_if_required (o usuário confirma o comportamento observado).
- **Failure Expectations:** Se o `def` mínimo também não mover → causa raiz diferente (candidatos: modo Local/Remote no PolyScope; programa precisa ser "iniciado" no PolyScope; fechamento do socket cedo demais truncando o envio). Disposição: `needs_replan` — pular para Phase 3 (robustez de envio) e investigar o log do PolyScope. Se ambos falharem por timeout de socket → problema de rede, `escalate`.

### Phase 2 - Refatorar o gerador para um único `def` de topo

- **Objective:** Emitir todo o programa dentro de um único `def palletizer_prog(): ... end`, sem chamada global final.
- **Owner:** local
- **Wave:** 2
- **Dependencies:** Phase 1 confirmando a hipótese.
- **Files:** [palletizer/motion/urscript.py](palletizer/motion/urscript.py) (modificar `generate_script`).
- **Tests:** [tests/test_urscript.py](tests/test_urscript.py) — atualizar (Phase correlata abaixo, mesma wave).
- **Acceptance Criteria:**
  - O script começa com `def palletizer_prog():` (ou nome equivalente) e termina com `end` — **sem** `palletize()` global no fim.
  - As atribuições `v_nominal/a_nominal/v_joint/a_joint/blend_r` aparecem como primeiras linhas **dentro** do `def` (calibração centralizada preservada — DD4).
  - `def gripper(state): ... end` fica aninhado dentro do `def` de topo.
  - `movej`/`movel`/`pose_trans(p_pallet, ...)`/`is_within_safety_limits(p_place)` inalterados na lógica; uma pose de place por caixa (paridade com o plano).
  - Indentação URScript coerente (2 espaços por nível), texto termina com `\n`.
- **Quality Gates:** tests_pass; inspeção visual do `.script` gerado por `python main.py --gen ursim`.
- **Failure Expectations:** `def` aninhado rejeitado por alguma versão do controlador → fixable: inlinar `set_digital_out(0, state); sleep(0.3)` nos pontos de uso. Transiente/fixable.
- **Steps:**
  1. Reestruturar `generate_script` para: emitir o cabeçalho/comentários; abrir `def palletizer_prog():`; emitir os parâmetros e `def gripper` indentados; emitir o corpo atual de `palletize` (o loop de slots) no mesmo nível; fechar com `end`. Remover a chamada global `palletize()`.
  2. Garantir que os comentários de topo (formato/camadas/caixas) permaneçam antes do `def` (não atrapalham o parser).
  3. Regenerar `scripts/palletizer_core.script` e revisar.

### Phase 3 - Atualizar os testes do gerador

- **Objective:** Alinhar `test_urscript.py` ao novo formato, mantendo a cobertura de intenção.
- **Owner:** local
- **Wave:** 2
- **Dependencies:** Phase 2.
- **Files:** [tests/test_urscript.py](tests/test_urscript.py).
- **Tests:** os próprios (rodar `python -m pytest tests/test_urscript.py -q`).
- **Acceptance Criteria:**
  - `test_params_emitted_at_top`: passar a fatiar pelo início do corpo/primeiro `movej` (ou pelo nome do novo `def`) em vez de `"def palletize"`; ainda garante que os 5 parâmetros aparecem antes dos movimentos.
  - `test_starts_and_ends_at_home`: garantir `movej(p_home` presente e que o script termina com `end` (não mais `palletize()`).
  - `test_has_movej_movel_and_safety_guard`, `test_one_place_per_box`, `test_missing_taught_point_raises`: permanecem válidos sem alteração de intenção (ajustar apenas se o texto exato mudou).
- **Quality Gates:** tests_pass (suíte inteira: `python -m pytest -q`, alvo 38 testes verdes).
- **Failure Expectations:** outra asserção acoplada ao texto quebra → fixable no mesmo passo.

### Phase 4 - Robustez do envio (pausa/flush antes do close)

- **Objective:** Evitar truncar o programa ao fechar o socket imediatamente após o `sendall`.
- **Owner:** local
- **Wave:** 3 (aplicar se a Phase 1 indicar que o fechamento cedo contribui; caso contrário, aplicar como melhoria defensiva de baixo risco).
- **Dependencies:** Phase 1.
- **Files:** [palletizer/comm/ur_socket.py](palletizer/comm/ur_socket.py) e/ou os call sites em [main.py:66](main.py) e [palletizer/gui/run_screen.py:71](palletizer/gui/run_screen.py).
- **Tests:** [tests/test_comm.py](tests/test_comm.py) — adicionar/ajustar cobertura se um método novo (ex.: `send_program`) for introduzido; não regredir os testes existentes.
- **Acceptance Criteria:** após `send`, há uma pequena espera/flush (ex.: `sleep(0.2-0.5)` ou drenar antes de `close`) de modo que o programa não seja abortado. A serialização por `Lock` e a máquina de estados permanecem intactas.
- **Quality Gates:** tests_pass; sem regressão de `test_comm.py`.
- **Failure Expectations:** espera fixa insuficiente para scripts grandes → fixable (tornar configurável). Baixo risco.

### Phase 5 - Validação end-to-end no URSim

- **Objective:** Confirmar que o robô executa o ciclo completo com o script corrigido.
- **Owner:** usuário (hardware-in-the-loop) com suporte local.
- **Wave:** 4
- **Dependencies:** Phases 2-4.
- **Files:** `scripts/palletizer_core.script` regenerado; config `configs/ursim.json`.
- **Tests:** manual.
- **Steps:**
  1. `python examples/build_ursim_config.py` (regenera config + script com poses reais).
  2. `python main.py --gen ursim` e inspecionar o `.script`.
  3. `python main.py --send ursim --ip <IP do URSim>` e acompanhar no PolyScope.
- **Acceptance Criteria:** o robô vai para `home`, executa pegar→transportar→colocar por caixa e retorna a `home`; nenhuma parada de proteção por pose inalcançável (se houver, é ajuste de pontos, não do gerador).
- **Quality Gates:** human_approved_if_required.
- **Failure Expectations:** parada de proteção → poses ensinadas inalcançáveis: reensinar por freedrive/`--read-pose` (fora do escopo do bug do gerador, `fixable` pelo operador). Programa ainda não roda apesar do `def` de topo → `needs_replan` com evidência do log do PolyScope.

## Inter-Phase Contracts

- **Phase 1 -> Phase 2:** veredito empírico (o `def` de topo move; o formato global não).
  - **Format:** confirmação do usuário (sim/não para cada envio) + qualquer mensagem do log do PolyScope.
  - **Validation:** Phase 2 só inicia com o "sim" para o `def` de topo.
- **Phase 2 -> Phase 3:** novo texto de script.
  - **Format:** string com um único `def` de topo, sem chamada global.
  - **Validation:** os testes atualizados passam contra o texto gerado.
- **Phase 2/4 -> Phase 5:** `scripts/palletizer_core.script` regenerado.
  - **Format:** URScript pronto para envio.
  - **Validation:** execução observada no URSim.

## Open Questions

- ~~Qual é o IP real do URSim?~~ **RESOLVIDO** (2026-07-04): o `192.168.2.103` de `examples/build_ursim_config.py` é o IP da VM do usuário e está correto; o `192.168.2.102` era de outra VM. Nenhuma mudança necessária no exemplo.
- Alguma versão do controlador do URSim exige "iniciar" o programa manualmente no PolyScope após o envio? (A validação na Phase 5 responde.)

## Risks

- **Diagnóstico parcialmente incorreto:** mitigado pela Phase 1 (spike de isolamento antes de refatorar).
- **Testes acoplados ao texto:** mitigado atualizando `test_urscript.py` na mesma wave da refatoração.
- **Fechamento de socket cedo demais mascarar a correção:** mitigado pela Phase 4 (pausa/flush).
- **Poses inalcançáveis confundidas com o bug:** o `movej(p_home)` inicial não é protegido, então movimento parcial distingue "programa não roda" de "pose ruim"; documentado na Phase 5.

## Semantic Risk Review

| Category | Applicability | Impact | Evidence Source | Disposition |
| --- | --- | --- | --- | --- |
| data_volume | not_applicable | LOW | script de ~18 caixas é texto pequeno ([urscript.py](palletizer/motion/urscript.py)) | not_applicable |
| performance | not_applicable | LOW | geração e envio únicos; sem laço quente | not_applicable |
| concurrency | applicable | MEDIUM | `Lock` no socket + máquina de estados ([ur_socket.py:66](palletizer/comm/ur_socket.py), [controller.py:69-85](palletizer/app/controller.py)) | resolved — wrapping não altera concorrência; Phase 4 mantém `Lock`/estado |
| access_control | applicable | MEDIUM | envio move um robô (real/sim); modo Local/Remote do PolyScope | resolved — `base.py` prova que a 30003 aceita scripts (não bloqueado); reconfirmado na Phase 1 |
| migration_rollback | applicable | LOW | muda o formato do `.script`; arquivos são regenerados por `--gen` | resolved — sem estado persistente; reverter é reverter `urscript.py` |
| dependency | applicable | MEDIUM | depende do comportamento da interface cliente do UR (auto-run de `def` na 30003) | research_phase_added — Phase 1 confirma empiricamente antes da refatoração |
| operability | applicable | MEDIUM | validação exige URSim vivo; garra é TODO (`set_digital_out(0,...)`); guarda de segurança no place | open_question — validação delegada ao usuário na Phase 5; mapeamento da garra fora do escopo deste bug |

## Success Criteria

- Um envio isolado de `def` mínimo move o robô no URSim (Phase 1).
- `generate_script` emite um único `def` de topo sem chamada global; `python -m pytest -q` verde (38 testes).
- `python main.py --send ursim` faz o robô ir para `home`, ciclar as caixas e voltar a `home` no URSim (Phase 5).
- Nenhuma regressão em `test_comm.py` / demais suítes.

## Idempotence & Recovery

- **Idempotente:** `--gen` e `build_ursim_config.py` podem ser reexecutados; sobrescrevem `scripts/palletizer_core.script` e `configs/ursim.json` deterministicamente.
- **Recuperação:** reverter é `git checkout palletizer/motion/urscript.py tests/test_urscript.py` (e `ur_socket.py`/call sites se a Phase 4 for aplicada). Nenhuma migração de dados nem estado externo; o robô/URSim retorna a `home` ou é parado pelo PolyScope. O arquivo `scripts/_probe_min.script` da Phase 1 é temporário e pode ser apagado.

## Handoff

- **Target:** `/controlflow-claude-code:controlflow-orchestration`
- **Review Before Execution:** `/controlflow-claude-code:controlflow-plan-audit` (SMALL+) e `/controlflow-claude-code:controlflow-assumption-verifier` (MEDIUM — verificar a asserção sobre auto-run de `def` na interface 30003 e o acoplamento dos testes ao texto).
- **Prompt:** "Auditar e verificar as suposições de `plans/robot-nao-move-plan.md` (em especial: interface cliente do UR executa automaticamente um `def` de topo recebido na 30003; parâmetros de movimento têm defaults não-nulos; ambos os caminhos de envio passam por `generate_script`). Depois executar as fases em ordem, com a Phase 1 (spike no URSim) como gate humano antes da refatoração."

## Notes for Orchestration

- Ordem recomendada: 1 → (2 ∥ 3, mesma wave) → 4 → 5.
- Paralelizável: Phase 2 e Phase 3 tocam arquivos diferentes (`urscript.py` vs `test_urscript.py`) mas 3 depende do texto de 2 — trate como sequência curta dentro da wave 2.
- Passos sensíveis a aprovação: Phase 1 e Phase 5 (envio real ao URSim — o robô se move).
- Retry/replan: se a Phase 1 refutar a hipótese, replanejar a partir do log do PolyScope antes de tocar em `urscript.py`.

## Progress

- [~] Phase 1 — Spike no URSim: **delegado ao usuário** (o executor não alcança a VM); combinado com a Phase 5. Pré-requisito de IP resolvido.
- [x] Phase 2 — Refatorar o gerador para um único `def` de topo — FEITO ([urscript.py](../palletizer/motion/urscript.py)).
- [x] Phase 3 — Atualizar os testes — FEITO ([test_urscript.py](../tests/test_urscript.py), [test_controller.py](../tests/test_controller.py)); 43 testes verdes.
- [x] Phase 4 — Robustez do envio (settle de 0.5s antes do close) — FEITO ([main.py](../main.py), [run_screen.py](../palletizer/gui/run_screen.py)).
- [ ] Phase 5 — Validação end-to-end no URSim — **pendente (usuário)**.

## Discoveries

- pytest não está no Python global; o projeto usa `.venv` (uv). Comando de teste: `.venv\Scripts\python.exe -m pytest -q`.
- Suíte cresceu de 38 → 43 testes (havia mais do que os 38 do README); todos passam após a mudança.
- `configs/ursim.json` e `scripts/palletizer_core.script` regenerados com as poses atuais do usuário; o script gerado mostra o `def palletizer_prog()` de topo, `gripper` aninhado, e fim em `movej(p_home...)` + `end`, sem chamada global.

## Decision Log

- Diagnóstico priorizado: formato de escopo global do URScript gerado, não velocidade zero (defaults são não-nulos) nem bloqueio de modo Remote (`base.py` prova que a 30003 aceita scripts).
- Phase 1 (spike) não pôde ser executada pelo assistente (sem acesso à VM do usuário). Como o wrapping em `def` de topo é a forma correta e reversível independentemente de fatores adicionais do URSim, optou-se por implementar as Phases 2-4 e delegar a confirmação empírica (Phase 1+5) ao usuário, com passos explícitos.
- Phase 4 aplicada como robustez defensiva de baixo risco (settle de 0.5s no call site, onde o socket fecha), sem tocar em `send_to_robot`/controller para não introduzir sleep nos testes.

## Outcomes

- Phase 2: `generate_script` emite um único `def palletizer_prog(): ... end`; chamada global `palletize()` removida.
- Phase 3: testes acoplados ao texto antigo (`"def palletize"`, `endswith("palletize()")`, `"palletize()" in ...`) atualizados; novo `test_wrapped_in_single_top_level_def` trava a correção. `43 passed`.
- Phase 4: settle de 0.5s antes do `close()` nos dois caminhos de envio (CLI `--send` e GUI).
- Pendente: Phase 5 (o usuário envia ao URSim e confirma o movimento).

### Phase 6 (replan) — Corrigir o offset de leitura de pose (`read-pose`)

- **Sintoma (2026-07-04):** após o wrapping, o programa passou a rodar e o URSim retornou
  `movej is unable to find an inverse kinematics solution` / "robô não consegue chegar na pose".
- **Root cause (2ª causa, distinta):** `read-pose` lia o offset `252:300` do pacote realtime,
  que é **`q actual` (posições de junta em rad)**, não a pose TCP. Os valores capturados eram
  ângulos de junta emitidos como `p[x,y,z,rx,ry,rz]` → poses cartesianas impossíveis (ex.:
  `p_pallet` com x=3.803 m, muito além do alcance de 1.3 m do UR10) → IK falha. A pose TCP
  cartesiana ("Tool vector actual") está no offset **`444:492`**.
- **Fix aplicado:** `RT_TCP_POSE_SLICE` (252,300) → (444,492) em
  [ur_state.py](../palletizer/comm/ur_state.py); testes de `test_comm.py` atualizados
  (offset + buffers ≥ 492); docstrings de `ur_socket.py`/`teach.py` e docs
  (README, tutorial, arquitetura) corrigidos. `43 passed`.
- **Ação do usuário obrigatória:** os pontos capturados antes do fix são ângulos de junta e
  precisam ser **recapturados** com o `read-pose` corrigido (os novos valores devem ter
  posição `|x,y,z|` dentro do alcance ~1.3 m).

## Idempotence & Recovery

- Ver a seção "Idempotence & Recovery" acima. Reexecuções de `--gen`/`build_ursim_config.py` são seguras e determinísticas; reversão por `git checkout` dos arquivos tocados; nenhum estado externo persistente além dos artefatos regeneráveis em `scripts/` e `configs/`.
