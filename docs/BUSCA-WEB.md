# Busca web local e coleta de páginas

O SearXNG fornece resultados de busca pela API JSON em `http://127.0.0.1:8080`.
A publicação Docker aceita conexões somente pelo loopback do host. A busca
consulta mecanismos externos e precisa de internet; o serviço local não torna
a pesquisa offline.

## Preparar e iniciar

Execute os comandos na raiz deste repositório. Docker e Docker Compose precisam
estar disponíveis. O projeto Compose `seo-agent-web` identifica esta instância;
verifique se a porta 8080 está livre antes de iniciá-la.

Crie a chave somente quando `.env` ainda não existir. O comando usa criação
exclusiva, permissão `0600` e não imprime a chave:

```bash
python3 - <<'PY'
import os
import secrets

try:
    descriptor = os.open('.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print('.env existente preservado; confirme que SEARXNG_SECRET esta definido.')
else:
    with os.fdopen(descriptor, 'w') as target:
        target.write('SEARXNG_SECRET=' + secrets.token_hex(32) + '\n')
    print('.env criado sem exibir a chave.')
PY
docker compose -p seo-agent-web config --quiet
docker compose -p seo-agent-web up -d searxng
docker compose -p seo-agent-web ps
```

`.env` é ignorado pelo Git. `.env.example` contém os campos de configuração,
sem valores reais; [CHAVES-BUSCADORES.md](CHAVES-BUSCADORES.md) explica como obter
as credenciais, carregar o ambiente e distinguir integrações prontas das futuras.
Uma chave ausente ou vazia impede o Compose de iniciar. Use `config --quiet`;
a saída completa de `docker compose config` expõe valores interpolados.

O arquivo `searxng/settings.yml` usa os defaults oficiais, habilita HTML/JSON
e desliga o limiter para esta instância local. O limiter exigiria Valkey.
A variável suportada para `server.secret_key` é `SEARXNG_SECRET`.
A imagem atual usa Granian: `GRANIAN_HOST=0.0.0.0` permite a conexão dentro
do container; o mapeamento `127.0.0.1:8080:8080` limita o acesso pelo host.
`server.bind_address` não configura o listener Granian.

O settings é montado somente para leitura e já deve existir. O entrypoint
oficial só gera settings quando o arquivo está ausente. `FORCE_OWNERSHIP=false`
evita alterar a propriedade desse arquivo; o volume de cache continua gravável.

## Verificar a API

Primeiro, verifique o serviço sem fazer buscas externas:

```bash
curl --fail --silent --show-error http://127.0.0.1:8080/healthz
curl --silent --show-error --include \
  'http://127.0.0.1:8080/search?format=json'
```

O primeiro retorna HTTP 200 e `OK`. O segundo retorna HTTP 400 com
`Content-Type: application/json` e `{"error":"No query"}`. O erro esperado
confirma que JSON está habilitado; HTTP 403 pode indicar formato desabilitado.
Health aprovado não comprova que os mecanismos externos estão disponíveis.

Para executar uma busca neutra real, quando a pesquisa estiver autorizada:

```bash
curl --fail --silent --show-error --get \
  'http://127.0.0.1:8080/search' \
  --data-urlencode 'q=OpenCode' \
  --data-urlencode 'format=json' \
  --data-urlencode 'pageno=1' \
  --output /tmp/seo-agent-search-smoke.json
python3 - <<'PY'
import json
from pathlib import Path

result = json.loads(Path('/tmp/seo-agent-search-smoke.json').read_text())
print('Resultados:', len(result.get('results', [])))
print('Mecanismos indisponiveis:', result.get('unresponsive_engines', []))
PY
```

HTTP 200 e JSON válido não garantem resultados: registre também a quantidade
e os mecanismos indisponíveis. `q` é obrigatório; `categories`, `language`,
`pageno`, `time_range` e `safesearch` dependem das opções da instância e do
suporte de cada mecanismo. A API aceita GET e POST form-urlencoded.

## Operação e limites

```bash
docker compose -p seo-agent-web logs --tail=80 searxng
docker compose -p seo-agent-web images
docker image inspect searxng/searxng:latest --format '{{json .RepoDigests}}'
docker compose -p seo-agent-web stop searxng
```

O digest identifica a imagem efetivamente testada, pois `latest` pode mudar.
`stop` interrompe esta instância sem remover seu cache. Para atualizar, faça
pull explicitamente e repita as verificações antes de registrar novo aceite.

Busca, leitura e análise são etapas distintas. Um resultado de busca não
comprova que a página foi lida. A ordenação do SearXNG não representa posição
comprovada no Google; não fornece volume de busca ou dificuldade de keyword.

O incremento de coleta SEO registra evidências de HTML, robots, sitemap,
HTTPS e redirecionamentos. Coleta de HTML inicial não equivale a renderização
JavaScript, sitemap não comprova indexação e links extraídos não são backlinks.
Não é uma reprodução completa do Web Check: não atribui pontuação Lighthouse,
Core Web Vitals, ranking Tranco ou resultado de auditoria sem executar a
respectiva medição. Falhas, limites de coleta e páginas não lidas devem ficar
explícitos no resultado.

## Busca batch e provedores

`search-batch` executa consultas completas em sequência, espera 300 segundos
entre elas (configurável) e grava grupos por domínio com `urli`, `searches` e
`buscador`. Ele visita cada URL única uma vez, ignora fragmentos e normaliza
`www.` somente para agrupamento por domínio. URLs finais repetidas também são
deduplicadas. Só páginas com status HTTP 200 entram no JSON; falhas
de rede e demais status são omitidos. Essa execução não usa robots.txt, conforme
o escopo explícito deste lote. Para nove consultas, há oito esperas, totalizando
40 minutos, além do tempo de busca e leitura.

O lote seleciona automaticamente os adaptadores de Brave, Google CSE, Yandex,
Mojeek, Kagi, You.com, SerpApi, Serper e DataForSEO cujas credenciais estão
completas no `.env`/ambiente. Campos ausentes não geram chamadas. APIs falhas
são registradas em um arquivo auxiliar e as demais continuam. Consulte a
[configuração de credenciais](CHAVES-BUSCADORES.md) e os [comandos](CLI.md).
DDG Instant Answers não equivale a uma API
de resultados completos; o Bing Search API foi aposentado em 2025; o Google
Custom Search JSON API não aceita novos clientes; e a API de busca do Yandex é
paga. Portanto, esses serviços não são apresentados como integrações gratuitas
genéricas. O SearXNG segue como opção principal e informa os mecanismos que
forneceram cada resultado. A chave da Brave nunca é gravada na saída.

Fontes oficiais sobre disponibilidade e custos dos provedores:
[Brave Search API](https://brave.com/search/api/), [Brave quickstart](https://api-dashboard.search.brave.com/documentation/quickstart),
[aposentadoria do Bing Search API](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement),
[Google Custom Search JSON API](https://developers.google.com/custom-search/v1/overview),
[preços da Yandex Search API](https://aistudio.yandex.ru/en/docs/search-api/pricing) e
[DuckDuckGo Instant Answers](https://duckduckgo.com/duckduckgo-help-pages/features/instant-answers-and-other-features).

## Fontes oficiais

- [Instalação da imagem e volumes](https://docs.searxng.org/admin/installation-docker.html)
- [Configuração server e variáveis suportadas](https://docs.searxng.org/admin/settings/settings_server.html)
- [Configuração herdada](https://docs.searxng.org/admin/settings/settings.html)
- [API de busca](https://docs.searxng.org/dev/search_api.html)
- [Entrypoint da imagem](https://github.com/searxng/searxng/blob/master/container/entrypoint.sh)
- [Rotas healthz e search](https://github.com/searxng/searxng/blob/master/searx/webapp.py)
- [Granian e variáveis do servidor](https://github.com/emmett-framework/granian#options)
- [Escopo SEO do Web Check](https://web-check.xyz/seo)

Signed-by: ai-codex (GPT-6 Astra Ultra)
