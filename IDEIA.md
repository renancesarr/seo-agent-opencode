# Especificação do Projeto: Executor de Possibilidades - Sistema Multiagente Local para SEO e Engenharia de Software

> Para desenvolver a primeira versão, siga o [contrato do MVP](docs/SEO-AGENT-MVP.md)
> e o [processo de execução](docs/EXECUCAO.md). Este documento preserva a visão
> de longo prazo; sua lista de tecnologias e fases não amplia automaticamente
> o escopo do incremento atual.

## 1. Visão Geral do Projeto

O **Executor de Possibilidades** é um sistema multiagente de IA local, **nativo do OpenCode** (runtime: subagentes, skills e servidores MCP do OpenCode, já instalado - v1.18), focado em **SEO de ponta a ponta** e **engenharia de software assistida por IA**. O projeto é **construído nas bancadas ZCode (GLM-5.3) e Codex (GPT-6 Astra Ultra)** - os dois agentes desenvolvem; o produto roda no OpenCode. O agente e seus subagentes cobrem **todas as fases de SEO**: inteligência de concorrentes (quem são e o que fazem), keyword research, desenvolvimento de código HTML/CSS/JS, copywriting humanizado e arquitetura de páginas com seções claras e navegáveis que sistemas de IA conseguem entender. Diferente de soluções baseadas em nuvem, este sistema utiliza **Modelos de Linguagem Locais (LLMs via Ollama)**, **roteamento local de tarefas**, e uma **arquitetura de memória híbrida persistente** para fornecer análise de concorrência, geração de conteúdo otimizado, refatoração de código assistida por memória, e debugging recursivo - com **custo marginal de operação** (a infraestrutura local elimina o custo por token de API; busca web e SERPs pagas opcionais continuam exigindo internet).

O sistema é governado por **Quatro Princípios Fundamentais** de desenvolvimento (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) e utiliza uma arquitetura de **destilação de contexto assíncrona** que processa dados em background para fornecer contexto denso e limpo aos LLMs, reduzindo o uso de tokens e mitigando alucinações por contexto sujo.

## 2. Objetivos

### Objetivo Principal
Criar um **agente de SEO e engenharia de software autônomo e consciente do contexto** que roda no OpenCode (desenvolvido com ZCode/GLM-5.3 e Codex/GPT-6 Astra Ultra), capaz de:
- Descobrir e monitorar concorrentes - quem são, o que fazem, o que funciona e quais gaps deixaram (SearXNG + scraping + SERP)
- Pesquisar e agrupar keywords (keyword research & clustering)
- Projetar páginas em seções claras e navegáveis, legíveis para sistemas de IA (arquitetura AI-readable)
- Desenvolver o código front-end das páginas (HTML, CSS, JS)
- Escrever copy humanizada com filosofia **practice-first** (caso de uso real antes de explicação)
- Realizar refatoração de código assistida por memória de longo prazo
- Executar debugging recursivo via Skill of Correction Discovery (SDD)

### Objetivos Secundários
- Implementar uma **arquitetura de memória híbrida** (vetorial + gráfica + temporal) que aprende e evolui com o uso
- Utilizar **roteamento local de tarefas** (LLM leve ou classificador) para rotear inteligentemente e filtrar ruído
- Garantir **segurança de defesa em profundidade** contra ataques adversariais (Tool Poisoning, A2A Injection, etc.)
- Manter **custo mínimo** através de otimização de tokens, modelos locais e cache inteligente
- Fornecer **observabilidade completa** via tracing, monitoramento de custo e avaliação de trajetórias

## 3. Features Principais

### 3.1 Camada de Percepção e Vigilância (SEO)

#### **Motor de Busca Local (SearXNG)**
- **Descrição:** Metabuscador open-source que agrega resultados de Google, Bing, DuckDuckGo, etc., fornecendo uma API JSON local para o agente consultar rankings e concorrentes sem depender de APIs pagas.
- **Benefício:** Custo zero de API e privacidade (o software roda local; as consultas aos buscadores exigem internet).
- **Estado atual:** `docker-compose.yml` já escrito no repo; falta criar `searxng/settings.yml` habilitando o formato JSON da API (sem ele o SearXNG responde HTML) e subir o container.

#### **Web Scraper com Renderização JS (Playwright MCP)**
- **Descrição:** Servidor MCP que permite ao agente abrir páginas web em um navegador headless, renderizar JavaScript e extrair texto limpo ou HTML estruturado de concorrentes.
- **Benefício:** Capacidade de analisar sites modernos com conteúdo dinâmico, essencial para SEO técnico.
- **Estado atual:** já existe um container `crawl4ai-mcp` nesta máquina (parado) - decidir entre reaproveitá-lo ou adotar o Playwright MCP.

#### **Monitoramento Assíncrono de Concorrentes**
- **Descrição:** Pipeline de background que ingesta URLs de concorrentes periodicamente, filtra ruído via filtro local leve, extrai entidades e relações, e persiste no Grafo de Conhecimento Temporal.
- **Benefício:** O agente "pensa" em background, compactando contexto antes da interação e reduzindo o uso de tokens na consulta final (percentual a medir com baseline).

#### **Grafo de Conhecimento de SEO**
- **Descrição:** Banco de dados gráfico (FalkorDB) que armazena relações de mercado: `(Concorrente_X) -[RANKED_IN_POSITION]-> (Keyword) @ [Data]`, `(URL_Nossa) -[OUTRANKS]-> (URL_Concorrente) -[FOR_KEYWORD]-> (Keyword)`.
- **Benefício:** Permite consultas multi-hop para análise estratégica: "Quem está no top 3 para X? Quais gaps de conteúdo eles não abordaram?"

### 3.2 Camada de Memória Híbrida Persistente

#### **Memória de Curto Prazo (Cache)**
- **Descrição:** Redis para armazenar estado de sessão, resultados intermediários e itens de trabalho recentes com TTL curto.
- **Benefício:** Latência mínima para acesso frequente, evitando sobrecarga de bancos mais lentos.

#### **Memória Semântica (Vetorial)**
- **Descrição:** Qdrant para busca semântica rápida de chunks de texto, documentos e embeddings.
- **Benefício:** Recuperação fuzzy baseada em significado, não em palavras-chave exatas.

#### **Memória de Longo Prazo (Grafo de Conhecimento)**
- **Descrição:** FalkorDB para armazenar triplas `(Sujeito, Predicado, Objeto)` e entidades, permitindo raciocínio estruturado e consultas multi-hop.
- **Benefício:** Capacidade de raciocínio lógico e exploração de relações complexas, essencial para refatoração assistida por memória.

#### **Memória Temporal (Graphiti)**
- **Descrição:** Framework open-source que automatiza a extração de conhecimento e modela explicitamente a passagem do tempo, permitindo resolução de conflitos e manutenção de histórico completo.
- **Benefício:** O agente sabe quais fatos eram válidos em qual momento, resolvendo ambiguidades com base no contexto temporal.

#### **Pipeline de Destilação de Contexto Assíncrono**
- **Descrição:** Fluxo de background que ingere dados massivos (PDFs, blogs, logs, codebases), usa um filtro local leve como "porteiro" para filtrar ruído, e usa LLM local para extrair triplas e enriquecer o Grafo de Conhecimento.
- **Benefício:** Transforma dados brutos em contexto estruturado e acionável, gastando compute em background para que a interação final use menos tokens (percentual a medir com baseline).

### 3.3 Camada de Decisão Especializada

#### **Roteamento Local de Tarefas**
- **Descrição:** Camada de decisão leve que roteia tarefas (qual modelo ou agente processa cada pedido) e faz gatekeeping de ruído, usando o próprio LLM local com prompt curto ou um classificador pequeno dedicado.
- **Benefício:** Evita gastar o modelo grande com tarefas triviais de classificação e filtragem.
- **Hipótese a medir:** latência e custo por decisão - coletar baseline antes de afirmar ganhos.

#### **Roteamento Dinâmico de Agentes**
- **Descrição:** Sistema que decide em tempo real qual modelo ou agente deve processar uma tarefa, baseado em complexidade, custo e contexto, selecionando entre modelos maiores e menores conforme o valor da tarefa.
- **Benefício:** Otimiza o uso de recursos computacionais, gastando inteligência onde ela produzirá o máximo de valor.

#### **Skill of Correction Discovery (SDD)**
- **Descrição:** Mecanismo de debugging recursivo onde falhas de agentes são capturadas, destiladas pelo filtro local, e transformadas em "Skills de Correção" que o sistema usará automaticamente na próxima ocorrência do mesmo erro.
- **Benefício:** Loop de autoaperfeiçoamento onde cada falha é uma oportunidade de aprendizado, fortalecendo o sistema contra incidentes futuros.

### 3.4 Camada de Orquestração e Segurança

#### **Protocolo MCP (Model Context Protocol)**
- **Descrição:** Padrão de facto para comunicação entre agentes e ferramentas externas. Todas as camadas de memória e ferramentas expõem servidores MCP (stdio/HTTP) na versão suportada pelos clientes instalados (ZCode, Codex, OpenCode) - validar e fixar a versão de spec antes do desenvolvimento.
- **Benefício:** Interoperabilidade universal, escalabilidade e simplificação de deploy.

#### **Protocolo A2A (Agent-to-Agent)**
- **Descrição:** Padrão complementar para comunicação direta entre agentes, permitindo descoberta e delegação de tarefas peer-to-peer via Agent Cards.
- **Benefício:** Ecossistemas dinâmicos e descentralizados entre frameworks distintos.
- **Observação:** fase futura - não é necessário para nenhum critério de SEO do MVP.

#### **Gateway MCP com Defesa em Profundidade**
- **Descrição:** Camada de controle que valida schemas, autentica requisições, aplica RBAC/CBAC, e protege contra ataques como Tool Poisoning, Rug Pull e Cross-server Tool Shadowing.
- **Benefício:** Segurança de zero-trust aplicada em cada nível da pilha tecnológica.

#### **Políticas de Governança**
- **Descrição:** Camada de políticas determinísticas de execução: allowlist de ferramentas, limites por agente e auditoria de chamadas. Ferramentas prontas de governança são **a validar** - nenhuma confirmada para esta stack.
- **Benefício:** Governança consistente independentemente do framework de orquestração utilizado.

### 3.5 Camada de Aplicação (SEO e Engenharia de Software)

#### **Agente de Inteligência de Concorrentes**
- **Descrição:** Descobre quem disputa a SERP de um nicho/keyword (SearXNG + SERP APIs), faz scraping dos conteúdos deles, extrai estrutura (seções, tópicos, formato, profundidade) e identifica o que funciona e os gaps deixados. Persiste tudo no Grafo de Conhecimento de SEO.
- **Benefício:** O ponto de partida de toda estratégia: saber quem são os concorrentes, o que fazem e o que ainda ninguém cobriu.

#### **Agente de Arquitetura de Página (AI-Readable)**
- **Descrição:** Projeta a página em seções claras e navegáveis - hierarquia semântica de headings, âncoras, dados estruturados (Schema.org) e marcação que LLMs e buscadores consigam parsear, resumir e citar. Define o outline antes da copy ser escrita.
- **Benefício:** Páginas que sistemas de IA entendem e citam - não apenas páginas bonitas para humanos.

#### **Agente de Desenvolvimento Front-end (HTML/CSS/JS)**
- **Descrição:** Implementa as páginas a partir da arquitetura e da copy: HTML semântico, CSS responsivo, JS mínimo necessário (Simplicity First), com atenção a performance e acessibilidade.
- **Benefício:** Código de página enxuto, rápido e manutenível, gerado ponta a ponta pelo sistema.

#### **Agente de Keyword Research & Clustering**
- **Descrição:** Usa MCP de API de SERP para buscar sugestões, calcula similaridade semântica (embeddings) e agrupa keywords em "Clusters de Tópicos" (Topic Clusters). Salva os clusters no Grafo.
- **Benefício:** Descoberta de oportunidades e organização estratégica de conteúdo.

#### **Agente de SEO Técnico (Auditor)**
- **Descrição:** Analisa URLs via MCP de scraping, verifica densidade de palavras-chave, estrutura de headings, presença de alt-text, velocidade (PageSpeed Insights), e valida dados estruturados (Schema.org). Gera relatório de "Tickets de Correção".
- **Benefício:** Diagnóstico automatizado de problemas técnicos de SEO.

#### **Agente de Copywriting SEO Humanizado (On-Page)**
- **Descrição:** Antes de escrever, consulta o Grafo de Conhecimento para identificar concorrentes no top 3, extrai subtópicos obrigatórios e gaps de conteúdo. Escreve copy humanizada que cobre os gaps e supera a profundidade dos concorrentes, seguindo a filosofia practice-first (abaixo).
- **Benefício:** Conteúdo estrategicamente superior, baseado em análise real de SERP - e que soa gente, não máquina.

#### **Filosofia de Conteúdo: Practice-First**
- **Descrição:** Todo conteúdo de blog segue esta ordem: (1) **prática primeiro** - casos de uso diretos, como aquilo foi usado e como mudou o workflow/vida de pessoas reais; (2) **exemplos o mais próximos possível da realidade do cliente-alvo**; (3) **só então a explicação** - o que é, como funciona, conceitos. Pergunta-guia do editor: *"o leitor consegue agir com o que leu nos primeiros 30 segundos?"*
- **Benefício:** Diferencia dos concorrentes que só teorizam: o conteúdo resolve antes de explicar, engaja mais e converte melhor.

#### **Agente de Refatoração Assistida por Memória**
- **Descrição:** Consulta o grafo de conhecimento para responder: "Quais são todas as dependências transitivas desta função? Existem testes que falham quando ela é modificada? Qual issue de bug anterior estava relacionado a seu comportamento?". Valida mudanças contra a especificação de desenvolvimento do projeto e a suíte de testes existente.
- **Benefício:** Refatoração guiada por evidências, com menor chance de introduzir regressões.

#### **Agente de Depuração Recursiva via SDD**
- **Descrição:** Captura falhas com contexto completo, re-ingesta no pipeline de destilação, cria SDD vinculada ao grafo, e na próxima ocorrência roteia diretamente para a SDD sem acionar o LLM principal.
- **Benefício:** Aprendizado contínuo com erros, resolução cada vez mais rápida.

### 3.6 Camada de Desenvolvimento e Skills (já implementada)

#### **Skills de Matt Pocock (base primária)**
- **Descrição:** 27 skills de engenharia e produtividade (`implement`, `tdd`, `code-review`, `pr`, `triage`, `wizard` etc.), instaladas localmente: clone em `~/.agents/src/mattpocock-skills` ligado por symlink a `~/.agents/skills/` (ZCode) e `~/.codex/skills/` (Codex). Atualização via `git pull` no clone (manifesto em `~/.agents/src/README.md`).
- **Benefício:** Código simples, cirúrgico e orientado a objetivos, disponível nos dois agentes.

#### **Diretrizes de Andrej Karpathy (complemento)**
- **Descrição:** O repo `multica-ai/andrej-karpathy-skills` contém uma única skill, `karpathy-guidelines` - diretrizes **comportamentais** de codificação (não skills de ML/Python). Também instalada localmente nos dois agentes.
- **Benefício:** Reforço sob demanda dos princípios durante escrita, revisão e refatoração de código.

#### **Quatro Princípios Fundamentais (instruções globais obrigatórias)**
- **Descrição:** Os princípios (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) estão gravados como instruções globais em `~/.zcode/AGENTS.md` e `~/.codex/AGENTS.md` (texto verbatim do repo Karpathy) - valem em todo workspace, sem depender de invocação de skill.
- **Benefício:** Garante que o agente não invente complexidade, não refatore sem solicitação e sempre defina critérios de sucesso verificáveis.

#### **Workflow de Execução**
- **Descrição:** Quando um repositório precisar do loop obrigatório (Analysis → Planning → Clarification → Implementation → Verification), incluí-lo no `<repo>/AGENTS.md` - este é o canal que ZCode e Codex realmente leem automaticamente.
- **Benefício:** Estrutura disciplinada que força o agente a pensar antes de codar e verificar após implementar.

### 3.7 Camada de Observabilidade e Avaliação

#### **Langfuse (Observabilidade)**
- **Descrição:** Plataforma open-source que captura traces de todas as chamadas LLM, custos de tokens, latências e avalia trajetórias de agentes.
- **Benefício:** Visibilidade completa do comportamento do agente, detecção de gargalos e otimização de custo.

#### **Framework de Avaliação Multi-dimensional**
- **Descrição:** Suite de benchmarks (SWE-bench, Promptfoo) com métricas como Taxa de Resolução, Taxa de Regressão, Custo por Tarefa Resolvida, Tempo de Execução e Taxa de Fidelidade ao Grafo.
- **Benefício:** Melhoria contínua mensurável, com dados acionáveis sobre onde o sistema está evoluindo e onde está regredindo.

#### **Pipeline de CI/CD para Agentes**
- **Descrição:** Pipeline Git-native (Promptfoo) que executa smoke tests a cada commit, regression suite a cada merge, full benchmark semanal e red team mensal.
- **Benefício:** Detecção precoce de regressões, garantia de qualidade em produção.

## 4. Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────┐
│           INTERFACE - OpenCode (dev: ZCode + Codex)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              CAMADA DE ORQUESTRAÇÃO (MCP + A2A)             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Gateway MCP  │  │  Agent Mesh  │  │  Governance  │      │
│  │  (Security)  │  │  (Identity)  │  │  (Policies)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           CAMADA DE DECISÃO (Roteamento local)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Roteador LLM │  │   Router     │  │  SDD Engine  │      │
│  │   (local)    │  │ (Dynamic)    │  │ (Recursive)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              CAMADA DE MEMÓRIA HÍBRIDA                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Cache      │  │   Vetorial   │  │    Grafo     │      │
│  │  (Redis)     │  │  (Qdrant)    │  │ (FalkorDB)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │   Temporal   │  │  Destilação  │                         │
│  │ (Graphiti)   │  │  (Pipeline)  │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              CAMADA DE PERCEPÇÃO (MCP Servers)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  SearXNG     │  │  Playwright  │  │  APIs SERP   │      │
│  │  (Busca)     │  │  (Scraper)   │  │  (Opcional)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              CAMADA DE APLICAÇÃO (Agentes Especializados)    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ SEO Keyword  │  │ SEO Técnico  │  │ Copywriting  │      │
│  │  Research    │  │   (Auditor)  │  │   (On-Page)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Refatoração  │  │  Depuração   │                         │
│  │  (Memória)   │  │  (SDD)       │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## 5. Stack Tecnológico

| Componente | Tecnologia | Justificativa |
| :--- | :--- | :--- |
| **Runtime do Agente** | OpenCode 1.18 (instalado) - subagentes, skills e MCP nativos | O produto roda onde o usuário trabalha |
| **Bancada de Desenvolvimento** | ZCode (GLM-5.3) + Codex (GPT-6 Astra Ultra) | Os dois agentes constroem o projeto em paralelo |
| **Orquestrador de LLM** | Ollama (instalado e rodando) | Padrão da indústria para rodar LLMs localmente de forma leve |
| **Modelos de Texto (LLM)** | deepseek-r1:32b, Qwen 27B (já presentes no Ollama local) | Já baixados e em uso nesta máquina |
| **Roteamento de tarefas** | LLM local com prompt curto (classificador dedicado se comprovado necessário) | Sem dependência externa; ganhos a medir com baseline |
| **Modelos de Embedding** | nomic-embed-text | Alta performance para RAG local |
| **Banco Vetorial** | Qdrant | Leve, fácil de integrar e persistir localmente |
| **Banco Gráfico** | FalkorDB | Alto desempenho para consultas multi-hop e GraphRAG |
| **Memória Temporal** | Graphiti | Extração automática de conhecimento e modelagem temporal |
| **Cache** | Redis | Latência mínima para acesso frequente |
| **Framework do Agente** | LangChain | Facilita a criação de chains, RAG e tool calling (alternativas LlamaIndex/ADK apenas se justificar) |
| **Orquestração de Workflow** | MVP: agendador simples (cron + fila no Redis) | Temporal/Kestra ficam para fase futura, se durabilidade complexa for necessária |
| **Protocolo de Ferramentas** | MCP (stdio/HTTP, versão dos clientes instalados) | Padrão universal para comunicação agente-ferramenta |
| **Protocolo de Agentes** | A2A (fase futura) | Comunicação peer-to-peer entre agentes |
| **Gateway de Segurança** | Gateway próprio: validação de schema + allowlist de ferramentas | Defesa em profundidade sem dependência não confirmada |
| **Observabilidade** | Langfuse | Tracing, monitoramento de custo e avaliação de trajetórias |
| **Avaliação** | SWE-bench, Promptfoo | Benchmarks padronizados e CI/CD para agentes |
| **Linguagem do Agente** | Python, TypeScript | Ecossistema mais rico para IA e scripts de SEO |
| **Containerização** | Docker, Docker Compose | Garante que o deploy do ambiente local seja idêntico em qualquer máquina |

## 6. Critérios de Sucesso

O projeto será considerado bem-sucedido quando:

### SEO
- [ ] O agente consegue analisar uma keyword e gerar um outline estratégico baseado em análise real de SERP
- [ ] O agente monitora concorrentes e identifica gaps de conteúdo automaticamente
- [ ] O agente gera copies humanizadas, practice-first, que superam a profundidade dos concorrentes
- [ ] Páginas geradas passam por validação estrutural: headings semânticos, Schema.org válido e seções navegáveis
- [ ] Todo conteúdo de blog começa por caso de uso prático antes da explicação conceitual (checklist editorial)
- [ ] Tokens por tarefa medidos com e sem destilação de contexto (baseline coletado antes de otimizar; meta de redução definida a partir do baseline)

### Engenharia de Software
- [ ] Refatorações multi-arquivo sem quebrar a suíte de testes do projeto-alvo (0 regressões nos testes existentes)
- [ ] Debugging recursivo via SDD com ciclos e tempo registrados por ocorrência
- [ ] Tempo de resolução medido por ocorrência, com meta de redução na repetição definida a partir do baseline
- [ ] O código gerado segue os 4 Princípios Fundamentais (simples, cirúrgico, orientado a objetivos)

### Arquitetura
- [ ] A memória híbrida (vetorial + gráfica + temporal) opera de forma integrada (smoke test passando)
- [ ] O roteador local decide tarefa → agente com latência e custo por decisão medidos (baseline primeiro)
- [ ] Pipelines de ingestão sobrevivem a reinício do container (retomam do ponto de falha)
- [ ] O gateway valida schema e allowlist em 100% das chamadas, com testes de injeção básicos passando

### Observabilidade
- [ ] O Langfuse captura traces de todas as chamadas LLM com custo e latência
- [ ] O framework de avaliação multi-dimensional mede Taxa de Resolução, Regressão e Custo por Tarefa
- [ ] O pipeline de CI/CD executa smoke tests a cada commit e full benchmark semanal
- [ ] O dashboard contínuo exibe tendências de melhoria ao longo do tempo

### Custo e Performance
- [ ] Custo por tarefa medido e publicado (a infraestrutura local tem custo marginal de energia/computação; sem meta fixa até existir baseline)
- [ ] Tempo médio de resolução de tarefas complexas medido por tipo de tarefa
- [ ] Operação local para LLM, memória e scraping; internet necessária apenas para busca (SearXNG) e SERP APIs opcionais

---

## 7. Próximos Passos

1. **Fase 1: Fundação e Infraestrutura (Semanas 1-2)** - parcialmente pronta
   - Criar `searxng/settings.yml` (habilitando a API JSON) e subir o SearXNG (compose já existe)
   - Decidir scraper: reativar o `crawl4ai-mcp` existente ou adotar Playwright MCP
   - Adicionar FalkorDB, Qdrant e Redis ao docker-compose
   - Definir prompts de roteamento no LLM local (Ollama já rodando com deepseek-r1:32b e Qwen 27B)
   - Estruturar o projeto no OpenCode: subagentes em `opencode.json`, skills em `~/.config/opencode/skills/` e servidores MCP (SearXNG)

2. **Fase 2: Memória e RAG (Semanas 3-4)**
   - Implementar pipeline de destilação de contexto assíncrono
   - Configurar Graphiti para memória temporal
   - Desenvolver lógica de Retrieval para alimentar o prompt do LLM com contexto do Grafo

3. **Fase 3: SEO, Arquitetura de Página e Copywriting (Semanas 5-7)**
   - Implementar o Agente de Inteligência de Concorrentes e o Grafo de Conhecimento de SEO
   - Implementar o Agente de Arquitetura de Página (AI-readable: outline, headings, Schema.org)
   - Implementar o Agente Front-end (HTML/CSS/JS) e o Agente de Copywriting practice-first
   - Desenvolver ferramentas para o agente ler arquivos do projeto e sugerir alterações de SEO

4. **Fase 4: Engenharia de Software e SDD (Semanas 8-10)**
   - Integrar SWE-bench (ou subset) e Promptfoo para avaliação
   - Desenvolver ciclo de depuração recursiva via SDD
   - Implementar refatoração assistida por memória

5. **Fase 5: Segurança e Governança (Semanas 11-12)**
   - Configurar Gateway MCP com validação de schema e allowlist de ferramentas
   - Implementar políticas determinísticas de execução e auditoria (toolkit pronto: a validar)
   - Implementar testes de Red Team e avaliação adversarial

6. **Fase 6: Observabilidade e Melhoria Contínua (Semanas 13-14)**
   - Configurar Langfuse para tracing e monitoramento de custo
   - Implementar pipeline de CI/CD para agentes (Agent CI, Promptfoo)
   - Criar dashboard contínuo com métricas multi-dimensionais
