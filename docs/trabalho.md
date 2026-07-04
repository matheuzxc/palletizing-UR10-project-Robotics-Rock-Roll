### 1. Divisão do Escopo do Projeto (Físico vs. Simulado)

Para atender plenamente aos requisitos do projeto final, a equipe dividiu a entrega em duas etapas complementares de validação:

- **Validação em Hardware Real (UR10):** Execução prática da **Cena Mínima Obrigatória** diretamente no robô real UR10 do laboratório. O robô executará fisicamente os ciclos de aproximação, descida, pega (Pick), transporte, deposição (Place) em 4 posições reais do pallet e o retorno seguro ao Home.
    
- **Validação em Ambiente de Simulação (RoboDK / Webots / CoppeliaSim):** Validação estendida da lógica de paletização, o cálculo paramétrico complexo de amarrações (_Brick / Pinhole / Split Block_), as trocas de malha em tempo real e o empilhamento em larga escala de **múltiplas camadas (no mínimo 2 layers completos)**.
    

### 2. Arquitetura de Movimentação e Interpolações Nativas da UR

Tanto no robô real quanto na simulação, a rotina foi programada em **URScript nativo** via comunicação **TCP/IP (Sockets)**, fazendo uso otimizado do planejador de trajetórias da Universal Robots:

- **Espaço de Juntas (`movej`):** Utilizado para os deslocamentos de transição aérea de longo curso e o retorno à posição de repouso (`p_home`), minimizando o esforço mecânico das articulações em trajetórias não lineares.
    
- **Espaço Cartesiano Linear (`movel`):** Aplicado obrigatoriamente nos vetores de aproximação vertical, descida e recuo tanto no ponto de coleta (_Pick_) quanto de entrega (_Place_). Isso garante uma aproximação estritamente perpendicular, eliminando riscos de colisões laterais com o pallet ou caixas adjacentes.
    
- **Otimização por Raio de Concordância (`blend_radius`):** Configuração do parâmetro de mistura de trajetórias (`r`) nos movimentos aéreos. Isso permite que o UR10 contorne os obstáculos de forma fluida e contínua, mantendo a velocidade linear constante sem desacelerar a zero entre as transições.
    

### 3. Parametrização, Segurança e Modos de Operação por Código

O script foi desenvolvido sob a premissa de parametrização dinâmica (rejeitando pontos estáticos gravados na memória), integrando funções de segurança ativa:

- **Calibração Centralizada de Padrões:** Todas as variáveis de velocidade linear (`v_nominal`), velocidade angular (`v_joint`), acelerações (`a_nominal`) e raios de _blend_ estão isoladas no topo do código para ajustes rápidos de conformidade com as normas de segurança do robô real.
    
- **Prevenção Ativa de Colisões:** Definição de planos de aproximação (_Approach Heights_) calculados dinamicamente em relação ao topo acumulado do pallet ($Z_{layer}$), blindando o sistema contra impactos.
    
- **Janela de Ajuste por Freedrive:** Implementação da função por software `freedrive_mode()`. Ela permite que, antes de iniciar o ciclo automático, o operador libere as juntas do UR10 por comandos temporizados para realizar o alinhamento físico e setup inicial da célula em total segurança.
    

### 📁 Arquivos e Documentação Incluídos no Pacote

1. **`palletizer_core.script`:** Código-fonte nativo em URScript pronto para ser transmitido via Socket para a porta `30003` do UR10 real ou do URSim.
    
2. **Cena 3D Virtual:** Arquivo de simulação contendo o gêmeo digital completo da célula, esteira, sensores e o empilhamento de camadas múltiplas.
    
3. **Ficheiro README:** Instruções detalhadas para calibração dos pontos e mapeamento de IPs/portas de comunicação para reprodução dos testes.
    

### 🔗 Links Oficiais para Avaliação

- **Vídeo Demonstrativo no YouTube (Máx 15 min - Demonstrando  a simulação):** `[Insira aqui o link do seu vídeo]`
    
- **Repositório do Projeto (GitHub):** `[Insira aqui o link do seu repositório]`
    
- **Apresentação no laboratório** da cena mínima no dia 06/07 ou 07/07 conforme a agenda do seu grupo.