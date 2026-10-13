# Experimento Browser Run — ticket #18

O comando mede Kitesurf e Chromium remotos com o mesmo endpoint e fixtures.
É uma primeira medição; não comprova equivalência com o crawler Chromium local
nem conclui #18. #19 continua dependente dos resultados reais.

1. Obtenha o Account ID no painel Cloudflare. Crie um API Token com permissão
   `Browser Run - Edit` para essa conta. Configure `CLOUDFLARE_ACCOUNT_ID` e
   `CLOUDFLARE_API_TOKEN` no `.env` ignorado. Ambiente exportado tem prioridade.
2. Hospede `examples/browser-fixtures/` em um destino público controlado por você.
   Edite uma cópia do manifest com suas URLs reais. `fixtures.example.org` é
   placeholder: substitua antes de usar credenciais. Nenhuma hospedagem foi feita.
3. Execute:

```bash
python3 -B -m seo_agent browser-experiment --fixtures /caminho/manifest-real.json --output data/browser-experiment
```

Sem ambas as credenciais, retorna `credentials_missing`, sem chamadas/capturas.
Com elas, faz cinco tentativas por cenário e motor: seis cenários geram 60 chamadas,
sujeitas às cotas da conta. Chromium remoto pode ser cobrado. Não substitui
adaptadores de busca ou crawler. Preserve o JSON de saída além dos artefatos.

Relatório conserva HTML, SEO, textos esperados ausentes, HTTP da API/destino,
tempo de parede e `X-Browser-Ms-Used` quando informado. API HTTP 200 com destino
404 ou status ausente nunca comprova página HTTP 200. `expected_text_complete`
cobre apenas textos predefinidos, não DOM universalmente completo. Tempo de
navegador não mede CPU/RAM nem custo total.

Fixtures: estático, SPA atrasada, lazy por visibilidade, iframe, Shadow DOM aberto
e fechado. `networkidle0` não garante temporizadores, scroll ou serialização dos
DOMs internos. Ausência permanece no relatório e deve orientar outra medição
com ações controladas antes da adoção. Falhas não autorizam contornar desafios.

Contrato conferido em 13/10/2026:
[Kitesurf](https://developers.cloudflare.com/browser-run/kitesurf/),
[snapshot/metadados](https://developers.cloudflare.com/browser-run/quick-actions/snapshot/),
[content após JavaScript](https://developers.cloudflare.com/browser-run/quick-actions/content-endpoint/).
Aceite remoto pendente: conta/token e fixtures públicas não configurados.

Signed-by: ai-codex (GPT-6 Astra Ultra)
