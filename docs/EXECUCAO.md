# Processo de desenvolvimento do agente SEO

## Ponto de partida

Objetivo: implementar o [contrato do MVP](SEO-AGENT-MVP.md). Cada tarefa abaixo
entrega uma capacidade verificável da ferramenta genérica.

Estado em 13/10/2026: T00–T02 integradas em dev-ai pelo PR #5. A CLI valida
projetos e preserva execuções preparadas. T04A acrescenta busca real e inspeção
SEO; sua verificação está abaixo. Integração por modelo/OpenCode, navegação
em browser, outlines e monitoramento ainda estão pendentes.

O watcher de PRs pertence ao desenvolvimento. O agendador diário do produto
SEO é uma capacidade separada, a implementar em T05.

## Procedimento para cada tarefa

1. Escolher a primeira tarefa pendente cujas dependências estejam verificadas.
2. Ler seu aceite e registrar o resultado esperado antes de editar.
3. Seguir [AGENTS.md](../AGENTS.md) para branch, identidade e sincronização.
4. Implementar a menor mudança que atende ao aceite. Registrar decisões
   técnicas e limitações na seção de evidências desta tarefa.
5. Executar a verificação indicada e registrar comando, resultado e arquivos.
6. Atualizar o estado local e preparar o PR para revisão cruzada conforme
   [REVIEW-WORKFLOW.md](REVIEW-WORKFLOW.md). Código revisado e integrado é um
   estado diferente de documentação pronta ou de teste local aprovado.
7. Se faltar uma decisão humana, registrar a pergunta específica e avançar
   somente nas tarefas que independam dela.

Estados: `pendente`, `em execução`, `verificada localmente`, `em revisão`,
`integrada`. Uma falha de teste mantém a tarefa em execução; uma dependência
não atendida mantém a próxima tarefa pendente.

Uma dependência libera a próxima tarefa quando está `verificada localmente`
ou em estado posterior e seu conteúdo validado está presente na branch de
trabalho. Em outra branch, aguarde a integração em `dev-ai` e sincronize.
A verificação local permite continuar o desenvolvimento, mas não substitui
revisão cruzada nem autoriza merge. Se uma revisão invalidar o aceite anterior,
reabra a tarefa em execução e repita as verificações dos dependentes afetados
antes de considerá-los prontos para integração.

## Fila em ordem de dependência

| ID | Entrega | Depende de | Estado |
|---|---|---|---|
| T00 | Consolidar decisões, processo e critérios de aceite | — | integrada |
| T01 | Verificar integração disponível no OpenCode e definir contrato técnico mínimo | T00 | integrada |
| T02 | Configuração de projeto e estrutura de execução genérica | T01 | integrada |
| T04A | Busca web, leitura de HTML e inspeção SEO | T02 | em revisão |
| T04N | Navegação, jornadas observadas e comparação por tela | T04A | pendente |
| T03 | Fluxo manual completo com fontes simuladas, histórico e revisão | T04A | pendente |
| T04B | Integrar coleta e geração de outlines pelo OpenCode | T03 | pendente |
| T05 | Monitoramento diário, comparação e avisos | T04B | pendente |
| T06 | Validar o MVP completo e documentar instalação/operação | T05 | pendente |

### T00 — Contrato e processo

Aceite: decisões confirmadas distinguíveis de propostas técnicas; primeira
entrega genérica; piloto tratado como configuração; cada tarefa tem dependência
e verificação. README, IDEIA, AGENTS e HANDOFF encaminham ao processo atual.
Verificação: integridade dos links locais, `git diff --check` e leitura crítica
independente. Documentação não demonstra funcionamento do produto.

### T01 — Compatibilidade local

Inspecionar versão, ajuda e interfaces locais do OpenCode e Ollama; registrar
o mecanismo real de agentes, ferramentas e execução sem interação disponível.
Escolher linguagem e persistência mínimas a partir dessa evidência.
Aceite: uma nota técnica com versões observadas, forma de invocação, limites e
decisões suficientes para T02–T04, sem inventar chaves de configuração.
Verificação: comandos locais reproduzíveis; indisponibilidade de serviço
registrada separadamente da existência do executável.

### T02 — Projeto e execução

Implementar a entrada do contrato e identificar projeto, execução e resultado.
Aceite: dois contextos de negócios diferentes são aceitos pelo mesmo fluxo;
um projeto sem domínio é válido; entrada incompleta gera mensagem acionável;
os resultados de um projeto não entram no histórico do outro.
Verificação: testes isolados com entradas válidas e inválidas, sem rede ou LLM.

A prioridade de busca/leitura antes dos outlines foi solicitada pelo usuário.
T04 foi dividida em coleta T04A e integração T04B; T04N incorpora a solicitação
posterior de navegação e comparação de jornadas, antes de ampliar a análise.

### T04A — Coleta e inspeção SEO

Aceite: a CLI consulta SearXNG, preserva consulta/posição observada/mecanismos,
lê uma URL pública e extrai conteúdo, metadados, links, headings, imagens,
JSON-LD, HTTP/TLS, robots e sitemap. Falhas ficam explícitas; não inventar score
SEO, indexação ou métricas de ranking. Não seguir links recursivamente.
Verificação: suíte isolada e smoke real da busca e leitura, separados.

### T04N — Navegação e jornadas

Implementar o aceite de [NAVEGACAO-CONCORRENTES.md](NAVEGACAO-CONCORRENTES.md):
leitura dinâmica, ações observadas, verificação do resultado e comparação por
tela em contextos isolados. Jev/Donut são candidatos, não integrações prontas.
Verificação: fixture local com JS e fluxo reproduzível, evidências de desktop e
mobile e teste real do controlador escolhido.

### T03 — Fluxo manual com evidências controladas

Implementar etapas de descoberta, leitura, análise, outline, histórico e revisão
por meio de dependências substituíveis nos testes, sem criar uma plataforma.
Aceite: um comando percorre o fluxo, preserva fontes e pendências, gera outline
proposto e recupera uma versão anterior. Aprovação refere-se à versão revisada;
uma atualização exige nova revisão. Falha de leitura não se torna evidência.
Verificação: testes com respostas e relógio controlados, incluindo leitura
parcial, ausência de evidências e dois projetos. A geração do LLM é simulada.

### T04B — Integração real no OpenCode

Conectar a coleta T04A e modelo local usando as interfaces verificadas em T01.
Manter a mesma entrada e saída de T03. Incorporar navegador quando T04N estiver
verificada e a tarefa exigir interação ou conteúdo dinâmico.
Aceite: uma invocação no OpenCode pesquisa e lê fontes, entrega outline com
referências rastreáveis e registra indisponibilidade, sem publicar conteúdo.
Verificação: testes de integração separados da suíte isolada; smoke test real
explicitamente executado e registrado com consulta e fontes. Se não executado,
o aceite permanece pendente. A pesquisa é executada pela ferramenta construída.

### T05 — Execução diária e avisos

Reutilizar o fluxo manual no agendador. Antes da ativação, resolver as
preferências operacionais pendentes listadas no contrato.
Aceite: mudança relevante cria proposta e aviso; ausência de mudança preserva
o outline e evita aviso repetitivo; falha preserva histórico e é reportada.
Execuções concorrentes do mesmo projeto não duplicam uma rodada de trabalho.
Verificação: relógio controlado, mudança real versus ruído e erro de coleta;
teste do disparo pelo agendador e do canal de aviso escolhido.

### T06 — Aceite e operação

Documentar configuração, execução manual, agendamento, consulta do histórico,
revisão, interrupção do monitoramento e diagnóstico de falhas.
Aceite: outro operador reproduz o ciclo com dois projetos de setores diferentes;
histórico e revisão sobrevivem ao reinício; o agendamento diário é demonstrado.
Verificação: registrar comandos e resultados reais. O piloto de igrejas é
opcional para este teste; nenhum teste exige site próprio já publicado.

## Evidências e próximo passo

T00–T02 estão no [PR #5](https://github.com/renancesarr/seo-agent-opencode/pull/5),
de `codex-ai` para `dev-ai`, aprovado e integrado em `3bbe639` em 13/10/2026.

T00 — verificada localmente em 13/10/2026:

- `git diff --check`: sem erros nos arquivos rastreados alterados.
- Verificação local dos seis documentos: 26 links resolvidos; arquivos novos
  verificados também quanto a espaços finais.
- Revisão interna por outro agente Codex: corrigida a ambiguidade sobre quando
  uma dependência libera a próxima tarefa. Essa leitura não é a revisão cruzada
  do ZCode exigida para o PR.

T01 — verificada localmente em 13/10/2026:

- Versões, ajuda e respostas do serviço local registradas em
  [COMPATIBILIDADE-OPENCODE.md](COMPATIBILIDADE-OPENCODE.md).
- Decisões técnicas: CLI Python, configuração JSON e snapshots em SQLite.
- Inferência, configuração de agente/provedor e integração com busca pendem de T04.

T02 — verificada localmente em 13/10/2026:

- [CLI.md](CLI.md) documenta `validate`, `prepare` e `history`.
- `python3 -B -m unittest discover -s tests -v`: sete testes passaram, com
  cenários parametrizados; sem rede ou LLM. Falhas iniciais reproduzidas antes
  da implementação de validação, registro/histórico e validação do identificador.
- Negócios distintos sem domínio aceitos; entradas inválidas não criam registros;
  snapshots anteriores preservados e histórico segregado por projeto.
- `prepare` registra somente estado `prepared` com `result: null`.
- Revisão interna independente de código e testes: sem bloqueadores. Revisão
  cruzada do ZCode posteriormente concluída no PR #5.
- Exemplo da CLI validado; sintaxe Python, 33 links locais da documentação e
  `git diff --check` verificados.

T04A — verificada localmente em 13/10/2026, no
[PR #6](https://github.com/renancesarr/seo-agent-opencode/pull/6), de `codex-ai`
para `dev-ai`; revisão cruzada pendente:

- `python3 -B -m unittest discover -s tests -v`: 43 testes isolados passaram.
  Ciclos red→green para busca, extração, transporte e comandos. A revisão interna
  identificou `X-Robots-Tag: follow, none`/`googlebot: none`; corrigido e coberto
  por regressão. Essa revisão não substitui o ZCode no PR.
- `docker compose -p seo-agent-web config --quiet`: configuração válida.
  `healthz`: HTTP 200; `/search?format=json` sem consulta: HTTP 400 com JSON,
  conforme contrato do SearXNG.
- Imagem observada: `2026.10.13-22c64b8d3`, digest
  `sha256:9b61996edcc679fb6665290f95fda15389a14eda6060e41a25c63ab2758f2436`.
- `python3 -B -m seo_agent search --query OpenCode --limit 3`: três resultados,
  incluindo `https://opencode.ai/`. DuckDuckGo e Google CSE indicados pelo
  agregador; indisponibilidade do Brave por excesso de requisições preservada.
- `python3 -B -m seo_agent inspect --url https://opencode.ai/`: HTTP 200,
  título extraído, 2.101 caracteres de texto, seis headings e 20 links;
  robots e sitemap HTTP 200, tipo urlset, relatório `ok`.
- `python3 -B -m seo_agent inspect --url https://example.com`: HTML e TLS
  válidos; robots e sitemap HTTP 404, relatório `partial` sem inventar arquivos.
- Smoke tests técnicos, sem pesquisa do piloto comercial, execução de LLM ou
  publicação. O serviço SearXNG ficou disponível em `127.0.0.1:8080`.

Próxima tarefa: T04N, navegação e jornadas. A coleta atual ainda não é o fluxo
completo por projeto: histórico de evidências, análise por LLM, outlines,
revisão editorial e agendamento permanecem pendentes.

Signed-by: ai-codex (GPT-6 Astra Ultra)
