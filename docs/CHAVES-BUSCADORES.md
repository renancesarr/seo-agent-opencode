# Configuração e chaves dos buscadores

Verificado em 13/10/2026. Este guia cobre descoberta de URLs e resultados web
para SEO. O inventário não significa que todos os adaptadores já estejam prontos.
A CLI `search-batch` usa SearXNG e seleciona automaticamente as APIs da tabela
abaixo quando suas credenciais estão preenchidas. Adaptadores foram verificados
com respostas HTTP controladas; aceite real de cada serviço depende de adicionar
credenciais elegíveis e executar seu smoke test. [.env.example](../.env.example)
contém todos os campos, vazios por padrão.

| API | Campos obrigatórios para entrar no ciclo |
|---|---|
| Brave | `BRAVE_SEARCH_API_KEY` |
| Google CSE | `GOOGLE_SEARCH_API_KEY` e `GOOGLE_SEARCH_ENGINE_ID` |
| Yandex | `YANDEX_SEARCH_API_KEY` e `YANDEX_FOLDER_ID` |
| Mojeek | `MOJEEK_API_KEY` |
| Kagi | `KAGI_API_KEY` |
| You.com | `YDC_API_KEY` |
| SerpApi | `SERPAPI_API_KEY` |
| Serper | `SERPER_API_KEY` |
| DataForSEO | `DATAFORSEO_LOGIN` e `DATAFORSEO_PASSWORD` |

Campo vazio ou só com espaços deixa o provedor fora da lista antes de iniciar
as consultas. Uma credencial presente é tentada; falhas são registradas, e as
demais APIs continuam. SearXNG não exige chave externa e pode ser excluído com
`--no-searxng`. Sem qualquer provedor disponível, o lote para antes de esperar.

## Preparar o ambiente

O `.env` local guarda valores reais e está ignorado pelo Git. O `.env.example`
é versionado, contém campos vazios e explica quais já são usados. Preserve
qualquer `.env` existente e suas chaves. Para uma instalação nova:

```bash
python3 - <<'PY'
import os
from pathlib import Path
import secrets

template = Path('.env.example').read_text(encoding='utf-8')
try:
    fd = os.open('.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print('.env existente preservado; acrescente somente campos ausentes.')
else:
    with os.fdopen(fd, 'w') as output:
        output.write(template.replace('SEARXNG_SECRET=\n',
                                      'SEARXNG_SECRET=' + secrets.token_hex(32) + '\n', 1))
    print('.env criado sem exibir valores.')
PY
```

Edite `.env` localmente. Não envie chaves em mensagens, commits ou screenshots.
Use aspas simples em valores com espaços, `$`, `#` ou outros caracteres especiais.
O Docker Compose e `search-batch` leem `.env` automaticamente. No lote, variáveis
exportadas têm prioridade, inclusive valores vazios. `--env-file` escolhe outro
arquivo. O parser aceita atribuições simples, comentários e aspas; não executa
comandos, não interpola `$VAR` e não aceita valores multiline. Não precisa usar
`source` nem exportar as chaves manualmente:

```bash
docker compose -p seo-agent-web config --quiet
python3 -m seo_agent search --query "consulta de teste" --limit 3
# Usa automaticamente as APIs com credenciais preenchidas, além do SearXNG:
python3 -m seo_agent search-batch --queries-file data/consultas.json \
  --output data/resultados.json
# Somente APIs configuradas, sem a instância SearXNG:
python3 -m seo_agent search-batch --queries-file data/consultas.json \
  --output data/resultados.json --no-searxng
```

O último comando consulta os provedores e lê páginas; pode consumir a franquia
da API. Confira o arquivo de consultas antes de rodar. Use `config --quiet`:
a configuração completa do Compose pode exibir o segredo interpolado.

## Buscadores relevantes para o Brasil

O recorte [StatCounter Brasil, desktop e mobile, setembro de 2026](https://gs.statcounter.com/search-engine-market-share/desktop-mobile/brazil/)
mostra Google (88,38%), Bing (9,64%), Yahoo (1,56%), DuckDuckGo (0,20%),
Yandex (0,18%) e Ecosia (0,03%). É uma medição amostral de uso, não cobertura
de páginas nem qualidade dos resultados. Brave e as alternativas abaixo entram
por disponibilidade de API/diversidade; não se atribui a elas participação
brasileira não demonstrada nessa fonte.

| Buscador | Acesso e credencial | Estado no agente |
|---|---|---|
| Google | Custom Search JSON API para clientes existentes; chave e ID `cx`. Para novas contas, avaliar SERP de terceiros. | Adaptador implementado; elegibilidade continua obrigatória. |
| Bing | [Bing Search APIs aposentadas em 11/08/2025](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement). Grounding com Bing pertence ao fluxo Azure/LLM e não substitui uma API de SERP bruta. | Sem chave Bing Search nova. |
| Yahoo | [Yahoo informa que seus resultados são gerados pelo Bing](https://en-maktoob.help.yahoo.com/kb/SLN35619.html). Não foi encontrado cadastro público de API própria de SERP. | Via mecanismos disponíveis no SearXNG ou futuro provedor terceiro. |
| DuckDuckGo | [Combina fontes, incluindo Bing](https://duckduckgo.com/duckduckgo-help-pages/results/sources). Instant Answers não entrega uma SERP web completa; não foi encontrada API pública oficial equivalente com chave. | Via mecanismos disponíveis no SearXNG. |
| Yandex | API oficial com conta de serviço, API key e identificação de folder; cobrança por uso. | Implementado: busca internacional/XML. |
| Ecosia | [Usa fornecedores de resultados conforme região/disponibilidade](https://support.ecosia.org/article/579-search-results-providers). Não foi encontrado cadastro público de chave de SERP própria. | Inventariado; sem adaptador próprio. |
| Brave | API oficial, índice independente, chave no painel Brave. | Implementado: seleção por chave. |
| Startpage | [Buscador alternativo](https://support.startpage.com/hc/en-us); não foi encontrada oferta pública documentada de API de SERP com chave. | Inventariado; sem adaptador próprio. |
| Qwant | [Termos da API exigem acordo para uso fora dos serviços Qwant](https://about.qwant.com/en/legal/qwant-search/). Endpoint usado pelo site não equivale a API pública autorizada. | Inventariado; sem adaptador próprio. |
| Mojeek | API oficial de índice próprio; chave contratada com o fornecedor. | Adaptador implementado. |
| Kagi | API oficial de busca, credencial no portal de APIs e cobrança separada conforme plano. | Adaptador v1 implementado. |
| You.com | API oficial de Web Search; chave no portal You.com. | Adaptador POST v1 implementado. |

Não criar variáveis fictícias `BING_API_KEY`, `YAHOO_API_KEY` ou `DUCKDUCKGO_API_KEY`.
SearXNG é um agregador: mecanismos podem falhar, exigir CAPTCHA ou não estar
habilitados. Acesso pela API JSON local não torna cada mecanismo uma API oficial
do buscador. `buscador` registra os mecanismos efetivamente informados na resposta.

## Obter as credenciais oficiais

### SearXNG local — `SEARXNG_SECRET`

Não exige conta externa nem chave de Google/Bing. Gere o segredo local pelo
procedimento acima e suba a instância conforme [BUSCA-WEB.md](BUSCA-WEB.md).
O segredo protege a aplicação SearXNG; não compra acesso a mecanismos externos.

### Brave — `BRAVE_SEARCH_API_KEY`

1. Crie a conta no [painel Brave](https://api-dashboard.search.brave.com/).
2. Em Plans, ative o plano Search; o [quickstart](https://api-dashboard.search.brave.com/documentation/quickstart) exige cartão.
3. Em API Keys, escolha Add API Key, dê um nome e copie o token para `.env`.
4. Use `search-batch`; a chave preenchida habilita o adaptador automaticamente.

A [página de preços](https://brave.com/search/api/) informa US$5 por mil chamadas
Search e US$5 de crédito mensal. Crédito não significa uso ilimitado: confira
limites de cobrança e condições do plano antes de ativar. A [autenticação oficial](https://api-dashboard.search.brave.com/documentation/guides/authentication)
usa `X-Subscription-Token`, já enviado pelo adaptador.

### Google — `GOOGLE_SEARCH_API_KEY` e `GOOGLE_SEARCH_ENGINE_ID`

A [Custom Search JSON API](https://developers.google.com/custom-search/v1/overview)
está fechada para novos clientes; clientes existentes devem migrar até 01/01/2027.
Uma chave Google Cloud recém-criada não garante elegibilidade. Para uma conta
já habilitada:

1. Selecione o projeto existente no [Google Cloud Credentials](https://console.cloud.google.com/apis/credentials).
2. Crie ou reutilize a API key e restrinja-a à Custom Search API e ao uso previsto,
   conforme [gerenciamento de chaves](https://docs.cloud.google.com/docs/authentication/api-keys).
3. Abra o [Programmable Search Engine](https://programmablesearchengine.google.com/),
   selecione o mecanismo e copie o Search engine ID para `GOOGLE_SEARCH_ENGINE_ID`.
4. Salve a chave em `GOOGLE_SEARCH_API_KEY`; o ID será o parâmetro `cx` da
   [requisição REST](https://developers.google.com/custom-search/v1/using_rest).

A franquia publicada de 100 consultas/dia aplica-se aos clientes existentes
elegíveis. O adaptador consulta a primeira página, até dez resultados.

### Yandex — `YANDEX_SEARCH_API_KEY` e `YANDEX_FOLDER_ID`

Siga o [quickstart oficial](https://aistudio.yandex.ru/en/docs/search-api/quickstart/):
crie/configure a conta de cobrança e o folder no Yandex Cloud/AI Studio, crie
a conta de serviço e gere a API key. Pela [autenticação oficial](https://aistudio.yandex.ru/en/docs/search-api/api-ref/authentication),
a conta de serviço precisa da função `search-api.webSearch.user` no folder.
Salve a key e o ID desse folder nos campos correspondentes. A API usa
`Authorization: Api-Key ...`; o folder pode ser inferido na autenticação de
conta de serviço conforme o método. Confira [preços e regiões suportadas](https://aistudio.yandex.ru/en/docs/search-api/pricing)
antes de escolher esta fonte para pesquisas brasileiras. O adaptador usa busca
internacional e decodifica os resultados XML; não simula localização portuguesa
em parâmetros de idioma de notificações que não oferecem português.

### Mojeek — `MOJEEK_API_KEY`

Na [página da Search API](https://www.mojeek.com/services/search/web-search-api/),
use Contact/Enquire Now para solicitar acesso, plano ou avaliação. Copie a chave
fornecida para `.env`; o [quickstart](https://www.mojeek.com/support/api/search/quickstart.html)
explica o uso. Há planos pagos e avaliação limitada sob contato, sem promessa
de franquia permanente gratuita. Confirme os direitos de armazenamento do plano
antes de preservar resultados históricos. O adaptador utiliza preferência Brasil
e português no endpoint de busca.

### Kagi — `KAGI_API_KEY`; You.com — `YDC_API_KEY`

No Kagi, entre no [portal de APIs](https://help.kagi.com/kagi/api/overview.html),
configure acesso/faturamento e gere uma chave. A [Search API](https://kagi.com/products/api)
usa Bearer token. No You.com, crie a conta e obtenha a chave em
[you.com/platform](https://you.com/platform), conforme o [quickstart](https://you.com/docs/quickstart).
Use o produto Web Search para URLs e resultados. Consulte o plano do produto;
assinatura do buscador ou teste promocional não implica API gratuita ilimitada.
Ambos têm adaptadores implementados. Kagi usa POST v1 com Bearer token, conforme
o [cliente OpenAPI oficial](https://github.com/kagisearch/kagi-openapi-python/blob/main/docs/SearchApi.md).
You.com usa [POST /v1/search](https://you.com/docs/api-reference/search/v1-search)
com `country: BR` e `language: pt-BR`. Kagi herda preferências da conta.

## Provedores terceiros para SERPs

São fornecedores de dados de resultados dos buscadores, não APIs oficiais
Google/Bing/Yahoo. As credenciais são do fornecedor. Os três abaixo foram
incluídos como alternativas de acesso e têm adaptadores para Google orgânico.

| Fornecedor | Como obter a credencial | Campo no `.env` |
|---|---|---|
| SerpApi | Crie conta, escolha um plano e copie a chave em [Manage API Key](https://serpapi.com/manage-api-key). Confira [mecanismos/documentação](https://serpapi.com/search-api) e [franquia atual](https://serpapi.com/pricing). | `SERPAPI_API_KEY` |
| Serper | Cadastre-se em [serper.dev](https://serper.dev/), abra o dashboard e copie sua API key. Oferece dados Google; a página anuncia teste de 2.500 consultas sem cartão, não uma franquia mensal permanente. | `SERPER_API_KEY` |
| DataForSEO | Crie conta e abra [API Access](https://app.dataforseo.com/api-access). Copie o login e a senha **da API**, diferente da senha da conta, conforme [autenticação](https://docs.dataforseo.com/v3/auth/). Selecione SERP API e confira cobrança/cobertura do mecanismo. | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` |

Para buscas regionais, inclua cidade/estado na consulta. Onde suportado, os
adaptadores também configuram Brasil/português; Yandex usa busca internacional,
e Kagi herda as preferências da conta. `buscador` conserva o mecanismo de origem:
os três fornecedores de SERP acima registram `google`, não três índices diferentes.
Cada credencial completa habilita sua API, portanto preencher várias chaves pode
consumir várias franquias em uma mesma consulta. Mantenha vazias as que não deseja
usar. Ter uma chave válida não prova precisão regional nem acesso HTTP 200 às
páginas. Resultados ficam no arquivo solicitado e falhas em `.errors.json`,
conforme [CLI.md](CLI.md). Corpos remotos e chaves não são gravados nos erros.

Contratos técnicos usados: [Google cse.list](https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list),
[Yandex WebSearch](https://aistudio.yandex.ru/en/docs/search-api/api-ref/WebSearch/search),
[Mojeek JSON](https://www.mojeek.com/support/api/search/json_response.html),
[SerpApi Google](https://serpapi.com/search-api),
[integração Serper documentada pelo CrewAI](https://docs.crewai.com/en/tools/search-research/serperdevtool)
e [DataForSEO Google orgânico live](https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/).

Signed-by: ai-codex (GPT-6 Astra Ultra)
