# Processo de desenvolvimento do agente SEO

## Ponto de partida

Objetivo: implementar o [contrato do MVP](SEO-AGENT-MVP.md). Cada tarefa abaixo
entrega uma capacidade verificável da ferramenta genérica.

Estado em 13/10/2026: T00–T02 integradas em dev-ai pelo PR #5. A CLI valida
projetos e preserva execuções preparadas. T04A acrescenta busca real e inspeção
SEO; sua verificação está abaixo. T04N foi integrada pelo PR #7. Integração por
modelo/OpenCode, outlines e agendador foram verificados localmente nesta
implementação, aguardando revisão cruzada e integração. Aceite operacional
completo e ativação permanente continuam pendentes.

O watcher de PRs pertence ao desenvolvimento. O agendador diário do produto
SEO é uma capacidade separada, implementada localmente em T05 e ainda não ativada.

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
| T04A | Busca web, leitura de HTML e inspeção SEO | T02 | integrada |
| T04N | Navegação, jornadas observadas e comparação por tela | T04A | integrada |
| T04P | Busca batch com APIs selecionadas por credenciais | T04A | integrada |
| T03 | Fluxo manual completo com fontes simuladas, histórico e revisão | T04A | verificada localmente |
| T04B | Integrar coleta e geração de outlines pelo OpenCode | T03 (ticket #11) | verificada localmente |
| T05 | Monitoramento diário, comparação e avisos | T03 (#11); ver bloqueios de #14–#16 | verificada localmente; ativação pendente |
| T06 | Validar o MVP completo e documentar instalação/operação | T05 (ticket #16) | pendente |

### Tickets aprovados da próxima fase

Especificação: [#9](https://github.com/renancesarr/seo-agent-opencode/issues/9).
Divisão aprovada pelo usuário em 13/10/2026, publicada com `ready-for-agent` e
dependências nativas no GitHub. A label indica trabalho especificado; iniciar
somente tickets cujos bloqueios foram concluídos. Estes bloqueios detalham as
macros acima: OpenCode não depende da implementação da revisão humana, e a
comparação pode avançar antes da integração real do modelo. Uma macro só termina
quando seus critérios de aceite completos forem demonstrados.

| Ticket | Entrega | Blocked by | Macro |
|---|---|---|---|
| [#10](https://github.com/renancesarr/seo-agent-opencode/issues/10) | Pesquisa por projeto e histórico de fontes | — | T03 |
| [#11](https://github.com/renancesarr/seo-agent-opencode/issues/11) | Outline versionado com justificativas e fontes | #10 | T03 |
| [#12](https://github.com/renancesarr/seo-agent-opencode/issues/12) | Aprovação/pedido de ajuste da versão | #11 | T03 |
| [#13](https://github.com/renancesarr/seo-agent-opencode/issues/13) | Fluxo real pelo OpenCode | #11 | T04B |
| [#14](https://github.com/renancesarr/seo-agent-opencode/issues/14) | Comparação e atualização por evidência | #11 | T05 |
| [#15](https://github.com/renancesarr/seo-agent-opencode/issues/15) | Avisos locais acionáveis | #12, #14 | T05 |
| [#16](https://github.com/renancesarr/seo-agent-opencode/issues/16) | Execução diária com limites/exclusão por projeto | #13, #15 | T05 |
| [#17](https://github.com/renancesarr/seo-agent-opencode/issues/17) | Aceite operacional do MVP | #16 | T06 |
| [#18](https://github.com/renancesarr/seo-agent-opencode/issues/18) | Captura DOM Kitesurf versus Chromium | — | B01 |
| [#19](https://github.com/renancesarr/seo-agent-opencode/issues/19) | Busca Kitesurf e fallback | #18 | B01 |
| [#24](https://github.com/renancesarr/seo-agent-opencode/issues/24) | Extração total e determinística das URLs coletadas | — | T07 |
| [#25](https://github.com/renancesarr/seo-agent-opencode/issues/25) | Rede de conhecimento consultável offline | #24 | T07 |
| [#26](https://github.com/renancesarr/seo-agent-opencode/issues/26) | Descoberta de palavras-chave com fonte | #24 | T07 |
| [#27](https://github.com/renancesarr/seo-agent-opencode/issues/27) | Classificação de tipos por ML clássico | #24 | T07 |
| [#28](https://github.com/renancesarr/seo-agent-opencode/issues/28) | Score de relevância por ML clássico | #24 | T07 |
| [#29](https://github.com/renancesarr/seo-agent-opencode/issues/29) | Insights por LLM sobre a rede compacta | #25, #26, #27, #28 | T07 |

Fronteira inicial: #10 e #18. Prioridade do produto: #10. B01 é experimental e
não bloqueia o MVP. Os tickets não foram implementados nesta publicação.

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

Executado manualmente por `crawl` conforme
[NAVEGACAO-CONCORRENTES.md](NAVEGACAO-CONCORRENTES.md): busca, leitura dinâmica,
cliques em links visíveis, verificação de destino e comparação desktop/mobile.
Jev/Donut são candidatos, não integrações prontas. O agendamento segue em T05.
Verificação: fixture local com JS e fluxo reproduzível, evidências de desktop e
mobile e smoke real com o Chromium local.

### T04P — Busca batch com APIs por credenciais

O incremento T04P foi priorizado pelo usuário antes de T03: adaptar Brave,
Google CSE, Yandex, Mojeek, Kagi, You.com, SerpApi, Serper e DataForSEO. Aceite:
credenciais ausentes/incompletas não entram no ciclo; configuradas fazem a
requisição correta; falha não impede as demais; manter apenas páginas HTTP 200
e URLs únicas, com consultas e buscadores, esperando cinco minutos entre
consultas completas. Verificação: adaptadores com HTTP controlado, agendador
com espera injetada e CLI com arquivos temporários; smoke real após chaves
elegíveis. O [backlog B01](BACKLOG.md) registra o experimento futuro Kitesurf.

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

T04A — integrada em `dev-ai` pelo
[PR #6](https://github.com/renancesarr/seo-agent-opencode/pull/6), em 13/10/2026:

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

T04N — integrada em `dev-ai` pelo
[PR #7](https://github.com/renancesarr/seo-agent-opencode/pull/7), merge `027c646`;
verificada localmente em 13/10/2026 na branch `codex-ai`, commit `1fdc8ca`:

- Suíte completa: 48 testes passaram, incluindo fixture local com conteúdo
  dinâmico, clique e validação do link interno, bloqueio de POST e origem externa.
- Smoke real da busca e do Chromium em `opencode.ai`: a busca encontrou páginas,
  o crawler abriu o resultado e clicou em “Docs” no desktop para chegar a
  `/v2/docs`. O menu móvel não expôs esse link, então a navegação mobile foi
  marcada como falha e a página como parcial, sem declarar jornada mobile.
- A renderização usa apenas links visíveis do DOM hidratado quando o Chromium
  funciona; evita seguir hrefs obsoletos do HTML inicial. Se a renderização falha,
  mantém os links estáticos como fallback e mostra estado parcial.
- Não acessa sessões, analytics ou histórias reais de usuários. T05 ainda cobre
  execução diária; fluxo por projeto, análise por LLM e outlines continuam pendentes.

Configuração de provedores — verificada localmente em 13/10/2026, por
solicitação do usuário antes de T03:

- `.env.example` contém 13 campos vazios; `.env` local atualizado com campos
  ausentes, preservando valores existentes, permissão `0600` e exclusão do Git.
- [CHAVES-BUSCADORES.md](CHAVES-BUSCADORES.md) documenta credenciais, cobertura
  brasileira, disponibilidade das APIs e adaptadores ainda pendentes.
- `bash -n .env` e `bash -n .env.example` passaram; campos, ausência de valores
  reais no exemplo, links locais e `git diff --check` verificados.
- Nenhuma chave externa obtida ou validada com chamada real nesta configuração.

T04P — integrada em `dev-ai` pelo
[PR #8](https://github.com/renancesarr/seo-agent-opencode/pull/8), merge `30d92ab`;
verificada localmente em 13/10/2026 na branch `codex-ai`, commit `fca3ee8`:

- `python3 -B -m unittest discover -s tests -v`: 72 testes, 71 aprovados e
  um smoke opcional de Chromium pulado nesta execução por dependência ausente.
- Ciclos red→green para seleção por credenciais, nove contratos HTTP de APIs,
  POST autenticado, carregamento de `.env`, continuidade após falha e
  deduplicação de redirecionamentos entre consultas.
- CLI verificada com chaves fictícias e HTTP controlado: saída JSON com apenas
  páginas HTTP 200; erros preservados em arquivo auxiliar sem credenciais.
  Sem provedores/chaves, saída 2 antes do ciclo. Espera padrão de 300 segundos
  entre consultas completas, com relógio/espera substituídos nos testes.
- Sintaxe Python, arquivos de ambiente, links locais e `git diff --check`
  aprovados; `.env` permanece ignorado e com permissão `0600`.
- Nenhuma consulta real às nove APIs nem execução remota Kitesurf nesta etapa.
  Chaves e elegibilidade ainda serão configuradas; registrar smoke por provedor
  depois disso. B01 permanece pendente no [BACKLOG.md](BACKLOG.md).
- PR #8 aberto pela conta `Fencing3422` e integrado em `dev-ai` em 13/10/2026.

Referência de planejamento antes desta implementação: T03, fluxo manual com
evidências controladas. A fase
está especificada na [issue #9](https://github.com/renancesarr/seo-agent-opencode/issues/9),
publicada por `to-spec` com `ready-for-agent`. A divisão de T03–T06 e B01 foi
aprovada e publicada por `to-tickets` nas issues #10–#19. Labels, assinaturas,
vínculos à especificação e dependências nativas foram conferidos no GitHub.
A especificação #9 permanece aberta. O experimento Kitesurf não bloqueia T03.

Implementação local de #10–#16 em 13/10/2026, ainda sujeita a review cruzado:

- CLI conecta coleta, histórico, outline versionado, decisões humanas e avisos.
  Testes controlam busca, HTTP e geração; exercitam ausência de evidências,
  referência inventada, nova fonte, mudança factual, CSS/espaços, erro parcial,
  recuperação em novo processo e lock do mesmo projeto/store.
- Smoke real: OpenCode 1.18.35 e Ollama 0.34.2, modelo `ollama/gemma4:e4b`,
  URL pública de exemplo. Outline JSON validado, versão pendente de revisão.
  Qwen 27B excedeu 300 segundos; Dolphin gerou texto/Markdown inválido. Ambos
  preservaram falhas sem gerar falsa proposta. Configuração temporária, sem
  ferramentas ou alteração dos modelos globais.
- Agendamento usa o mesmo `run`, horários persistidos, limites, recuperação
  explícita e encerramento do grupo de processos. Horários escolhidos: 8h/20h.
  Smoke real único em configuração temporária: horário `2026-10-13T18:01:00-03:00`,
  execução `5c007d32-d15b-48d6-bf94-24c578d7dc28`, `run_status=collected`,
  gerador validado com Gemma. Repetição retornou `already_claimed`.
  Monitoramento permanente não ativado. Projeto operacional escolhido:
  `examples/igrejas-go.json`. Confirmados: America/Sao_Paulo, 10 consultas, 20 páginas,
  900 segundos, intervalo de 60 segundos e `skip` para horários perdidos.
- #18 parcialmente implementado: cinco capturas por cenário/motor, HTML/SEO,
  tempo e status separados. Baseline inicial é Chromium remoto, não equivalência
  comprovada com o crawler local. Cloudflare sem conta/token; aceite remoto e
  recomendação pendentes. #19 permanece bloqueado por esse aceite.
- #17 tem instruções em [FLUXO-PROJETO.md](FLUXO-PROJETO.md), mas aceite por outro
  operador e monitoramento permanente ainda não concluídos. Não fechar #9.
- Verificação inicial completa: `python3 -B -m unittest discover -s tests -v`:
  89 testes, 88 aprovados e um smoke opcional Chromium pulado por dependência ausente.
  Sintaxe Python por AST, `bash -n .env.example` e `git diff --check` aprovados.
  Não há typechecker configurado. Nenhuma chamada real à Cloudflare.
- Review contra `bb19c7e`: três falhas funcionais corrigidas — recuperação após
  coleta parcial compara com fontes da versão original; pedido humano de ajustes
  permite regeneração com fontes inalteradas; falha parcial SearXNG é preservada.
  Estados do resumo/tabela também corrigidos. Eventos OpenCode malformados viram
  falha persistida. Suíte após correções: 92 testes, 91 aprovados, um skip opcional.
- Smoke de limite real: scheduler com `max_seconds=1` encerrou a rodada no horário
  `2026-10-13T18:10:00-03:00`, gravou falha `1f478977-2982-4805-b7dc-f45b6413c4e8`
  e conservou a proposta válida anterior no mesmo histórico. Configuração temporária,
  sem ativação permanente e sem credenciais Cloudflare.

- Ticket #24 implementado na zcode-ai (spec #23, T07): comando `extract` com
  condição de entrada (sem fontes → `no_sources` sem registrar nada), extração
  determinística sem LLM das páginas preservadas (datas/autores de meta/time/
  JSON-LD com origem por sinal), falhas por estágio (`page`, `structured_data`),
  ausência ≠ erro e reexecução idêntica. Code review dois eixos: DDL/INSERT
  unificado em helper de store; página vazia vira falha; docs atualizados.
  Verificação: `python3 -m unittest discover -s tests -q` → 101 OK (1 skip),
  sem rede/LLM. PR único da spec #23 para dev-ai ao concluir #24–#29.
- Ticket #25 implementado na zcode-t25 (spec #23, T07): comandos `network
  build`/`network query` derivam a rede de conhecimento da extração registrada
  mais recente e a preservam como execução no mesmo store (padrão runs, sem
  tabelas novas). Modelagem mínima: entidades `page`/`term` e relações
  `has_term`/`links_to`, cada fato com `sources` (URLs do corpus). URL com
  falha na extração fica fora com a falha em `excluded`; sem extração → erro
  acionável apontando `extract`; sem fontes válidas → `status: empty`.
  `query --compact` devolve contagens e principais termos/links com fontes,
  menor que a soma do texto bruto (verificado com fixtures reais). Suíte:
  `python -m unittest discover -s tests -q` → 110 OK (1 skip), sem rede/LLM.
- Ticket #26 implementado na zcode-t26 (spec #23, T07): comando `keywords`
  descobre palavras-chave sobre o texto preservado pela extração mais recente,
  sem LLM e com Python stdlib: n-gramas de cauda longa (bi/trigramas com bordas
  de conteúdo, lista mínima de stopwords pt-BR só de palavras gramaticais),
  pares de termos coorrentes em >= 2 páginas (`a + b` alfabético) e perguntas
  do texto (headings incluídos no texto preservado). Cada termo sai com
  `sources` (URLs) e o registro referencia `extraction_run_id`; keywords do
  projeto derivadas do snapshot mais recente marcam `is_new` por igualdade
  normalizada. Condição de entrada igual ao `network build` (sem URLs → `run`;
  com URLs sem extração → `extract`, nada registrado); falha parcial exclui a
  URL com a falha em `excluded`; ordenação por frequência decrescente e
  alfabética, `--limit` padrão 50; reexecução idêntica. Suíte:
  `python -m unittest discover -s tests -q` → 124 OK (1 skip), sem rede/LLM.
- Ticket #27 implementado na zcode-t27 (spec #23, T07): comando `classify`
  rotula cada fonte da extração mais recente em `article`/`listing`/`profile`
  por classificador linear de pontuação — ML clássico local, pesos fixos
  auditáveis em `WEIGHTS`, determinístico sem semente — sobre indicadores dos
  sinais já extraídos (prosa >= 300 palavras, >= 3 headings, autoria/datas,
  >= 12 links, >= 50% do texto em âncoras, esparsidade, @type do JSON-LD);
  vence a maior pontuação, empate em ordem alfabética. Cada rótulo sai com
  `signals` (valores observados) e `scores` por tipo (justificativa
  inspecionável); página sem texto ou sem indicador vira pendência
  `unclassified` com motivo e status `partial`, não erro; condição de entrada,
  `excluded` e `empty` iguais ao `network build`/`keywords`; registro via
  save_run com `extraction_run_id`, saída ordenada por URL, reexecução
  idêntica. Evidência do método: fixtures de tipo conhecido classificam
  corretamente (guia 364 palavras/4 headings/BlogPosting → article 10;
  diretório 15 links/razão de âncoras 0,91/ItemList → listing 8; ficha 29
  palavras/Organization → profile 6). Suíte:
  `python -m unittest discover -s tests -q` → 134 OK (1 skip), sem rede/LLM.
- Ticket #28 implementado na zcode-t28 (spec #23, T07): comando `rank` pontua a
  relevância de cada fonte e tema da extração mais recente com ranking linear
  determinístico — ML clássico local, pesos fixos auditáveis em `WEIGHTS`
  (autor 1, datas 1, texto >= 300 palavras 3, >= 3 headings 2, JSON-LD
  presente 2, links recebidos 1 por página distinta do corpus com teto de 3),
  sem aleatoriedade nem semente. O sinal de rede deriva do próprio conjunto
  válido da extração (mesma semântica deduplicada de `links_to`), não da rede
  persistida: `rank` roda logo após `extract`, sempre coerente com o
  `extraction_run_id` pontuado. Cada fonte sai com `factors`
  {signal, value, weight, points} cuja soma é o score; cada tema (heading
  normalizado, critério de `term` da rede) soma os scores das fontes que o
  cobrem com as URLs-fonte. Ordenações determinísticas (score decrescente,
  depois alfabético); pendência explícita com motivo para fonte sem texto
  (status `partial`, não erro); falha parcial em `excluded`; só falhas →
  `empty`; reexecução idêntica. Evidência do método: fixtures de relevância
  conhecida ranqueiam na ordem esperada (guia 364 palavras/4 headings/
  BlogPosting/2 links recebidos → 11; ficha Organization com 1 link recebido
  → 3; colega autor+data → 2; hub ItemList → 2 com empate desempatado por URL;
  tema "pragas comuns" 13 = 11 + 2 agregando guia e colega). Suíte:
  `python -m unittest discover -s tests -q` → 146 OK (1 skip), sem rede/LLM.
- Ticket #29 implementado na zcode-t29 (spec #23, T07): comando `insights`
  gera insights por LLM sobre o conhecimento compacto, reutilizando o
  contrato de geração do `run` (gerador injetável na seam da CLI;
  `--insights-file` controlado sem modelo; `--model` via OpenCode com
  deny-all/--pure/JSON — `OpenCodeGenerator` parametrizado por
  agente/prompt/título com `message` extraído, contrato do outline
  inalterado). Payload = rede compacta + keywords/classify/rank da MESMA
  extração da rede (época coerente; análises de outra extração não se
  misturam), nunca page.text (invariante testado no payload recebido pelo
  gerador e no prompt do model_runner). Anti-invenção adaptada do
  validate_proposal: referências só páginas da rede, termos só da rede ou da
  descoberta, observation exige âncora, rejeições registradas (status
  `invalid_insights`, erro estágio `generation`) sem derrubar a execução.
  Sem gerador: agregados entregues + `no_model` com mensagem explícita —
  não é erro. Entrada: sem URLs → `run`; sem extração → `extract`; sem rede
  → `network build`; rede vazia → reconstruir corpus; keywords/classify/rank
  recomendadas — ausências viram pendências informadas em
  `missing_analyses`. Persistência via save_run com extraction/network/
  keywords/classify/rank run_ids (`null` quando ausentes). Smoke real em
  processos separados: no_model entrega conhecimento; `--insights-file`
  gera; histórico consultável. Suíte:
  `python -m unittest discover -s tests -q` → 165 OK (1 skip), sem rede/LLM.

- Correções do review do PR #30 (ai-codex, head 0c0ec47): (1) P1 — extract
  lê apenas fontes de coleta preservadas (entradas com page/id); resultados
  derivados como o ranking não substituem o conteúdo original — regressão do
  ciclo run→extract→rank→extract→network build added; (2) P2 — coocorrência
  em duas fases (candidatos = termos em >=2 páginas) com teto de 100.000
  pares distintos; página única de 1.500 termos não materializa pares
  (pico de memória < 80 MiB verificado por tracemalloc no teste).
  Verificação: `python3 -m unittest discover -s tests -q` → 167 OK (1 skip).

- Segunda rodada do review do PR #30 (ai-codex, head 7dc31e7): teto da
  coocorrência separado da contagem — admissão limitada a 100 mil pares em
  ordem determinística, e pares admitidos recebem frequência/fontes exatas
  pela interseção do índice termo → páginas (par novo no teto não reduz os
  admitidos; regressão com teto reduzido via patch cobre pares novos antes
  de existentes em página posterior); `is_new` das coocorrências agora
  compara normalizado dos dois lados (keyword 'Alface + Beterraba!' marca
  'alface + beterraba' como não-nova). Verificação: suíte → 169 OK (1 skip).

- Terceira rodada do review do PR #30 (ai-codex, 3 P2): (1) fragmento de
  link desconsiderado na rede e no ranking — `pagina#secao` gera `links_to`
  e voto de inbound para a página coletada (testes na rede e no rank);
  (2) identificação de perguntas linear (split em vez de regex com
  retrocesso — 60 mil caracteres sem pontuação em < 2 s, suíte do arquivo
  caiu de ~8 s para ~1 s); (3) pergunta de heading extraída do próprio
  heading, descartando a variante com prefixo de navegação/título do texto
  corrido. Verificação: suíte → 173 OK (1 skip).

Próximo passo operacional: publicar a configuração escolhida, ativar o
monitoramento após integração aprovada e reproduzir o aceite
de #17; para #18, fornecer credenciais locais e hospedar fixtures controladas.
Issues implementadas só são integradas após PR aprovado pelo agente oposto.

Signed-by: ai-codex (GPT-6 Astra Ultra)
