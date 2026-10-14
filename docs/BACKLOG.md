# Backlog de experimentos

Itens solicitados além da fila principal de [EXECUCAO.md](EXECUCAO.md).
Estar neste backlog não significa estar implementado, contratado ou ativado.

## B01 — Testar Cloudflare Browser Run com Kitesurf para coleta e buscas

Solicitado pelo usuário em 13/10/2026. Estado: **adiado para o backlog** por
decisão do usuário em 14/10/2026; não está na fila de execução atual. Executar
após a verificação local do lote de APIs T04P; não bloqueia o fluxo de produto T03.

Evidência parcial já coletada (14/10/2026, credenciais validadas e 50 capturas
em URLs reais dos pilotos): ver comentário em
[#18](https://github.com/renancesarr/seo-agent-opencode/issues/18). O aceite
formal dos 6 cenários controlados continua exigindo fixtures públicas.

Decomposto, com aprovação do usuário, em
[#18 — captura DOM e comparação](https://github.com/renancesarr/seo-agent-opencode/issues/18)
e [#19 — busca e fallback](https://github.com/renancesarr/seo-agent-opencode/issues/19),
sob a especificação [#9](https://github.com/renancesarr/seo-agent-opencode/issues/9).
#19 depende de #18; ambos continuam pendentes de implementação/aceite.

Objetivo: avaliar se Kitesurf consegue capturar o DOM renderizado necessário
à análise SEO de páginas e extrair resultados de buscas em sites compatíveis,
comparando qualidade, tempo e consumo com Chromium. O desejo de obter “todo o
DOM do site” vira critérios verificáveis por página e por recurso, e não uma
garantia prévia de cobertura universal.

### O que a documentação estabelece

- [Browser Run](https://developers.cloudflare.com/browser-run/) oferece Quick
  Actions REST/Workers, CDP, Puppeteer e Playwright, além de navegação por agentes.
  O [índice da documentação](https://developers.cloudflare.com/browser-run/llms.txt)
  aponta as interfaces e referências a consultar durante a implementação.
- [Kitesurf](https://developers.cloudflare.com/browser-run/kitesurf/) é um motor
  stateless em beta. Quick Actions e CDP aceitam `browser=kitesurf`; o padrão
  usa Chromium. Há limites por conta; não assumir acesso ilimitado.
- [`/content`](https://developers.cloudflare.com/browser-run/quick-actions/content-endpoint/)
  retorna HTML renderizado da página, incluindo `head`, após JavaScript. Não
  descreve uma captura de todas as páginas de um domínio ou uma serialização
  universal de iframes, Shadow DOM e estado interno das aplicações.
- Para SPA, a espera padrão pode devolver conteúdo incompleto. Testar
  `gotoOptions.waitUntil` e `waitForSelector`, com
  [timeout explícito](https://developers.cloudflare.com/browser-run/reference/timeouts/).
- [`/snapshot`](https://developers.cloudflare.com/browser-run/quick-actions/snapshot/)
  combina HTML, screenshot, Markdown e árvore de acessibilidade em uma captura;
  pode ajudar a comparar o DOM com o conteúdo realmente apresentado.
- REST requer account ID e token com `Browser Run - Edit`. Workers usa binding
  `BROWSER` sem token; Quick Actions exige data de compatibilidade suportada
  e desenvolvimento remoto, conforme [Quick Actions](https://developers.cloudflare.com/browser-run/quick-actions/).
- Kitesurf ainda limita desafios de bot que dependem de TLS real e sessões
  autenticadas persistentes. A compatibilidade deve ser medida por site;
  os números de Web Platform Tests não demonstram cobertura do nosso corpus.

### Experimento a implementar

1. Criar um cliente experimental isolado da coleta padrão. REST:
   `POST https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/browser-run/content?browser=kitesurf`,
   com `Authorization: Bearer <API_TOKEN>` e corpo `{"url":"<URL pública>"}`.
   Sem credenciais, pular a integração sem chamada remota.
2. Preparar páginas controladas acessíveis pelo serviço remoto: HTML estático
   com metadados/JSON-LD, SPA com conteúdo atrasado, lazy loading, iframe e
   Shadow DOM aberto/fechado. Definir previamente os elementos/textos esperados.
   Uma fixture em localhost não é acessível pela Cloudflare por padrão.
3. Rodar a mesma captura em Kitesurf e Chromium, com os mesmos limites,
   viewports e condição de espera. Preservar HTML original/renderizado,
   URL inicial/final, status do destino quando observável e metadados da API.
   HTTP 200 da API não prova HTTP 200 da página alvo.
4. Passar o HTML capturado pelo extrator SEO existente. Conferir título,
   descrição, canonical, headings, texto, links, JSON-LD e conteúdo dinâmico
   esperado. Registrar quais estruturas ficaram fora da captura, sem declarar
   “DOM completo” se os critérios não forem satisfeitos.
5. Testar uso como busca: primeiro uma página de resultados controlada,
   depois um buscador público compatível. Extrair título/URL, origem e consulta,
   normalizando pelo contrato dos adaptadores. Não tratar SERP renderizada como
   API oficial. CAPTCHA, bloqueio ou timeout são falhas registradas; não há
   contorno automático. Não clicar anúncios nem enviar formulários de terceiros.
6. Medir latência total, tamanho da saída, completude, falhas e consumo
   reportado em `X-Browser-Ms-Used`, com pelo menos cinco capturas por cenário.
   Esse header mede tempo de browser, não CPU/RAM nem cobrança completa.
7. Testar fallback explícito para Chromium em caso incompatível e conferir
   limites de destinos públicos, métodos HTTP e dados de sessão antes de
   conectar o serviço remoto ao fluxo atual.

### Aceite

- [ ] Credenciais ausentes não geram chamadas; token não entra nos artefatos.
- [ ] Elementos definidos nas fixtures encontrados ou ausência explicada,
  incluindo limites de iframe, Shadow DOM e conteúdo após interação.
- [ ] Status da API e do destino distinguidos; coleta incompleta fica explícita.
- [ ] Comparação reproduzível Kitesurf/Chromium, com métricas e HTML preservados.
- [ ] Extração de busca mantém consulta, origem e URLs únicas no contrato atual.
- [ ] Falhas, limites da beta e fallback demonstrados; sem substituir o crawler
  padrão antes da decisão baseada no experimento.
- [ ] Registrar conclusão e recomendação em `docs/experimentos/kitesurf.md`
  quando o teste for executado; no momento esse relatório ainda não existe.

Dependências externas do teste futuro: conta Cloudflare elegível, account ID,
token/binding, fixtures públicas e conferência de
[limites](https://developers.cloudflare.com/browser-run/limits/),
[preços](https://developers.cloudflare.com/browser-run/pricing/) e
[política de robots/sitemaps](https://developers.cloudflare.com/browser-run/reference/robots-txt/)
da operação selecionada. Nenhum teste remoto Kitesurf foi executado nesta etapa.

Signed-by: ai-codex (GPT-6 Astra Ultra)

## B02 — Usar Kitesurf no fluxo real de coleta do produto

Solicitado pelo usuário em 14/10/2026 (junto com o adiamento de B01). Estado:
**backlog**; não iniciar antes do aceite formal de B01.

Objetivo: se B01 aprovar o motor, avaliar o uso de Kitesurf (e do Chromium remoto
do Browser Run como fallback) na coleta real do fluxo de produto (`run`/`crawl`),
não apenas em experimento isolado. A adoção depende de:

- B01 aceito com evidência de cobertura igual ou superior ao Chromium nos
  cenários controlados e no corpus real dos pilotos.
- Contrato respeitado: sem chamada sem credenciais completas, status da API e do
  destino distinguidos, falhas preservadas sem destruir versões válidas.
- Limites/preços da conta conferidos; nenhum uso ilimitado presumido.
- Decisão explícita do operador substituindo o adaptador padrão atual.

Sem pré-requisito atendido, este item permanece parado; não há código de
integração escrito antecipadamente.

Signed-by: ai-zcode (GLM-5.3)
