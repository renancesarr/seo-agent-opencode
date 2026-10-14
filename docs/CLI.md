# Projetos, busca web e inspeção SEO

A CLI implementa T02, coleta T04A e navegação T04N do [processo de desenvolvimento](EXECUCAO.md).
Execute os comandos na raiz do repositório com Python 3.11 ou superior
(testado com 3.14.4). Os comandos básicos usam a biblioteca padrão; `crawl`
requer Playwright e Chromium, conforme as instruções abaixo.

## Comandos disponíveis

```bash
# Validar a entrada sem gravar uma execução
python3 -m seo_agent validate --project examples/projeto.json

# Registrar uma execução preparada e seu contexto
python3 -m seo_agent prepare --project examples/projeto.json

# Recuperar as execuções desse projeto, em ordem de registro
python3 -m seo_agent history --project-id horta-local

# Extrair de forma determinística as URLs já coletadas do projeto
python3 -m seo_agent extract --project-id horta-local
```

`prepare` e `history` aceitam `--store <arquivo.sqlite3>` para escolher o
armazenamento. O padrão é `data/seo-agent.sqlite3`, relativo ao diretório atual,
ignorado pelo Git. Use o mesmo arquivo para consultar as execuções registradas.
Uma consulta sem histórico devolve lista vazia e não cria o banco.

Sucesso produz JSON em stdout e código de saída 0. Entrada inválida ou falha de
leitura/escrita produz mensagem em stderr e saída 2, sem traceback esperado.
`validate` verifica a estrutura local; não verifica sites ou disponibilidade de
fontes. Falha na validação acontece antes de abrir o banco.

## Contrato JSON do projeto

Copie [examples/projeto.json](../examples/projeto.json) e adapte seus valores.

| Campo | Formato | Regra |
|---|---|---|
| `id` | texto | Identificador estável: letras minúsculas sem acento, números e hífens entre palavras. |
| `business_context` | texto | Contexto do negócio. |
| `audience` | texto | Público que o conteúdo deve atender. |
| `language` | texto | Idioma desejado, por exemplo `pt-BR`. |
| `geography` | texto | Recorte geográfico, inclusive nacional ou global quando aplicável. |
| `keywords` | lista de textos | Pelo menos uma palavra-chave. |
| `content_goal` | texto | Resultado pretendido com o conteúdo. |
| `domains` | lista de textos, opcional | Domínios próprios, caso já existam. |
| `competitors` | lista de textos, opcional | Referências de concorrentes indicados. |
| `sources` | lista de textos, opcional | Fontes sementes indicadas. |

Textos vazios ou só com espaços são rejeitados. Listas opcionais podem ser
vazias; seus itens, quando presentes, precisam de texto. Campos desconhecidos
são rejeitados para tornar erros de digitação visíveis. Nesta etapa os valores
opcionais são metadados, sem resolução de domínio ou acesso a URLs.

O `id` distingue os históricos. Reutilizá-lo significa continuar o mesmo
projeto; trocar o contexto não modifica os snapshots das execuções anteriores.
Esta separação é organizacional em uma ferramenta local, não controle de acesso
entre usuários de um serviço multiusuário.

## Registro inicial

`prepare` gera `run_id`, `project_id`, `created_at` em UTC, `project` com o
snapshot da configuração, `status: "prepared"` e `result: null`.

O estado preparado significa que a entrada foi validada e registrada. Busca,
leitura e inspeção podem ser executadas separadamente com os comandos abaixo.
O fluxo por projeto, a análise por modelo, o outline e a revisão permanecem
pendentes. `prepare` não dispara essas etapas.

## Extração determinística das fontes coletadas

`extract` implementa a extração do [ticket #24](https://github.com/renancesarr/seo-agent-opencode/issues/24)
e consome somente o histórico local: sem LLM, rede ou serviço externo. Sem URLs
coletadas no histórico do projeto, devolve `status: no_sources` com mensagem
orientando executar a busca antes, sem registrar execução. Com fontes, extrai de
cada URL o máximo possível do conteúdo já preservado pela coleta: texto,
título/descrição, idioma, headings, links, imagens/alt, JSON-LD, metadados
(robots, social, hreflang, canonical) e, com a origem registrada por sinal,
datas (meta `article:published_time`/`article:modified_time`, atributo
`datetime` de `time` e `datePublished`/`dateModified`/`dateCreated` do JSON-LD,
inclusive em `@graph`) e autores (meta `author` e `author` do JSON-LD).

O resultado por URL — `source_id`, `retrieved_at`, `page` e `failures` — é
preservado como nova execução no histórico, sem destruir as anteriores. Para
URLs recoletadas vale a página preservada mais recente; a saída lista as
extrações em ordem alfabética de URL. Falha de uma URL (página preservada
ilegível) fica registrada em `failures` com o estágio, sem derrubar as demais;
ausência de sinal (por exemplo, página sem autor) não é erro. Reexecutar sobre
as mesmas fontes produz a mesma extração: apenas `run_id` e `created_at` mudam.

## Busca e inspeção

Prepare o SearXNG conforme [BUSCA-WEB.md](BUSCA-WEB.md). Depois:

```bash
python3 -m seo_agent search --query "OpenCode" --language pt-BR --limit 3
python3 -m seo_agent inspect --url https://example.com
```

`search` aceita `--endpoint` (padrão `http://127.0.0.1:8080`) e `--limit`
(de 1 a 20, padrão 5). A URL base da instância pode incluir um prefixo de caminho,
mas não query, fragmento ou credenciais. O endpoint é configuração confiada ao
operador: pode ser local; redirecionamentos são rejeitados.

O JSON contém consulta, idioma, URL da API, horário de coleta, resultados com
URL/título/snippet/mecanismos e posição observada no SearXNG. URLs repetidas,
desconsiderando fragmento, são removidas. `unresponsive_engines` conserva falhas
informadas pelo provedor. Lista vazia não comprova ausência de concorrência.
`--limit` limita a saída; não limita quantos mecanismos o SearXNG consulta.

Para executar várias consultas e salvar os resultados acessíveis HTTP 200,
crie um JSON com uma lista de textos e rode:

```bash
python3 -m seo_agent search-batch \
  --queries-file data/consultas.json \
  --output data/resultados.json \
  --interval-seconds 300
```

Cada item agrupa `domain`, `urli` (título e URL), `searches` e `buscador`.
URLs repetidas são coletadas uma vez; URLs finais de redirecionamento também são
deduplicadas. `www.` é removido somente no agrupamento por domínio, sem supor
que dois hosts respondam da mesma forma. O intervalo
ocorre entre consultas completas, após a primeira e sem espera depois da última.
O padrão de 300 segundos significa 40 minutos de espera para nove consultas.
O lote consulta SearXNG e lê as URLs públicas; páginas com status diferente de
200 ou falha de leitura são descartadas. Esta coleta não consulta `robots.txt`.

`search-batch` lê `.env` automaticamente (`--env-file` escolhe outro arquivo);
variáveis exportadas têm prioridade, inclusive valores vazios. Não executa o
arquivo como shell nem expande `$VAR`. Campos vazios ou credenciais incompletas
deixam a API fora do ciclo de consultas. Brave, Google CSE, Yandex, Mojeek,
Kagi, You.com, SerpApi, Serper e DataForSEO têm adaptadores. A seleção é feita
uma vez, antes da primeira consulta; não é necessário `--brave`.

O SearXNG continua habilitado sem chave externa. Use `--no-searxng` para executar
somente APIs configuradas. Sem nenhum provedor, a CLI retorna saída 2 antes de
consultar ou esperar. Os campos obrigatórios estão em
[CHAVES-BUSCADORES.md](CHAVES-BUSCADORES.md). Ter uma chave preenchida não garante
elegibilidade, saldo ou acesso à API: uma chave inválida é tentada e reportada.

SerpApi, Serper e DataForSEO consultam Google neste incremento; `buscador`
registra `google`, enquanto o nome do fornecedor identifica eventuais falhas.
Yandex usa busca internacional; Kagi herda preferências da conta. Os demais
configuram Brasil/português conforme o contrato da API. Uma consulta deve citar
cidade/estado para o recorte regional.

Falha de uma API não interrompe as demais. O lote registra consulta, provedor
e mensagem controlada em stderr e em `<arquivo de saída>.errors.json`, sem
chaves ou corpo remoto. O arquivo principal conserva o contrato dos grupos.
Havendo falhas e nenhuma página HTTP 200, a CLI salva ambos os arquivos e sai 2;
resultados parciais ou busca válida sem resultados saem 0. Confira sempre o
arquivo de erros. SearXNG reporta os mecanismos retornados em `buscador`.

`inspect` faz uma auditoria de URL explícita: lê a página e consulta robots.txt
mais um sitemap do host final. Não segue links encontrados. O relatório inclui:

- `http`: URL final, status, redirecionamentos, tamanho e headers selecionados.
- `domain`: hostname, endereços resolvidos A/AAAA e expiração do certificado TLS
  verificado quando HTTPS; não é inventário DNS, WHOIS ou data de expiração do domínio.
- `page`: texto, título, descrição, idioma, headings, canonical, robots,
  hreflang, social tags, links internos/externos, imagens/alt, datas, autores
  e JSON-LD.
- `robots`: regras recebidas, sitemaps declarados e permissão observada para
  SEOAgent. É uma observação posterior à auditoria explícita, não aplicação de
  política de um crawler automático. A avaliação usa urllib.robotparser e não é uma implementação completa do
  protocolo robots. Regras indisponíveis ou padrões com * e $ ficam como
  desconhecidos; preserve o texto para uma decisão posterior de rastreamento.
- `sitemap`: primeiro sitemap declarado na mesma origem, ou `/sitemap.xml`;
  distingue urlset de índice, limita saída a 500 entradas e não segue filhos.
- `issues`: observações com evidências; ausência de metadados não é uma nota de SEO
  e noindex pode ser intencional. JSON-LD parseado não implica validade no Schema.org.

`status: partial` indica HTML não analisado ou falha em arquivos auxiliares;
conteúdo válido já lido é preservado. HTTP 404, HTML em lugar de robots e sitemap
inválido não se tornam evidências positivas. Um relatório parcial ainda retorna
saída 0; o consumidor deve conferir `status` e os erros. Falha ao buscar a URL
principal retorna saída 2. Os resultados desses comandos não são gravados no
histórico SQLite; podem ser preservados redirecionando stdout para um arquivo.
A integração das evidências ao histórico do projeto pertence a T03.

A coleta aceita apenas HTTP/HTTPS público, valida DNS em cada redirecionamento
e conecta ao endereço validado. Usa até cinco redirecionamentos, 2 MiB por
resposta e timeout de 15 segundos por operação de socket. Isso não representa
um prazo global de execução: resolução DNS e tentativas entre IPs somam tempo.
Respostas comprimidas são recusadas quando o servidor ignora Accept-Encoding
identity; não há execução de JavaScript ou CSS nem autenticação/cookies.

## Execução automática de páginas e jornadas

`crawl` encadeia busca, inspeção, descoberta de links e Chromium. Ele percorre
até três páginas por host e até o total de `--max-pages`, verifica robots.txt
antes de cada página e segue links da mesma origem. Cada destino é renderizado
em contexto descartável desktop (1365×900) e mobile (390×844); screenshots
são gravados sob `--evidence-dir`.

Links visíveis geram passos reproduzíveis: o Chromium clica o link na origem,
verifica se chegou à URL esperada e registra a ação. Se o link não está visível
ou leva a outra URL, o passo fica como falha. A descoberta inclui links exibidos
por JavaScript na renderização desktop. Botões, filtros, formulários e cadastros
são registrados como controles, mas não são acionados.

```bash
# Dependência de navegador opcional, instalar uma vez
python3 -m pip install -r requirements-browser.txt
python3 -m playwright install chromium

# Busca e rastreamento automáticos, com relatório e screenshots locais
python3 -m seo_agent crawl \
  --query "palavra-chave e contexto" \
  --limit 5 --max-pages 6 \
  --evidence-dir data/browser-evidence > data/crawl-latest.json
```

`--limit` limita candidatos da busca (1–20, padrão 5). `--max-pages` limita
resultados e links percorridos somados (1–20, padrão 6). O teto de três páginas
por host continua valendo. Os arquivos em `data/` são locais e ignorados pelo
Git. Cada execução cria contextos sem perfil ou cookies da pessoa que executa
a ferramenta. O navegador resolve o host para o IP público já validado pela
coleta HTTP, aceita pedidos apenas dessa origem e bloqueia requests externos,
WebSockets e POST. CDNs/API externas podem ficar ausentes da renderização; os
pedidos bloqueados aparecem no resultado.

Um `journey` é uma sequência de links reproduzida pelo crawler, não histórico
real de visitantes ou analytics do concorrente. O relatório registra controles
disponíveis sem enviar dados a formulários. `crawl` é manual; o agendamento
diário segue pendente em T05. Resultado da coleta é evidência para análise, não
story aprovada pelo negócio.

Para limites e significado das jornadas observadas, veja
[NAVEGACAO-CONCORRENTES.md](NAVEGACAO-CONCORRENTES.md).

## Verificação

Os novos comandos `run`, `outline`, `review`, `notices`, `schedule-tick` e `monitor`
estão descritos no [fluxo por projeto](FLUXO-PROJETO.md).
`browser-experiment` tem procedimento e limites no
[experimento Kitesurf](EXPERIMENTO-KITESURF.md).

```bash
python3 -B -m unittest discover -s tests -v
```

Os testes usam a CLI em novos processos e bancos temporários. Verificam negócios
diferentes, entrada inválida, persistência, preservação de snapshots e separação
por projeto. A coleta usa respostas HTTP controladas para metadados, falhas,
redirecionamentos, endereços privados e limites; sem rede ou LLM na suíte.
Os smoke tests reais ficam registrados em [EXECUCAO.md](EXECUCAO.md).

Signed-by: ai-codex (GPT-6 Astra Ultra)
