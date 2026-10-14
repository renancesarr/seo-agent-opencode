# Workflow operacional de revisão

## Direções obrigatórias

| Origem | Destino | Revisor | Assinatura |
|---|---|---|---|
| `zcode-ai` | `dev-ai` | `ai-codex` / `Fencing3422` | `Signed-by: ai-codex (GPT-6 Astra Ultra)` |
| `codex-ai` | `dev-ai` | `ai-zcode` / `renancesarr` | `Signed-by: ai-zcode (GLM-5.3)` |
| `dev-ai` | `main` | humano | decisão humana |

## Verificação de um PR

```bash
gh pr view <n> --repo renancesarr/seo-agent-opencode \
  --json state,baseRefName,headRefName,headRefOid,reviews
gh pr diff <n> --repo renancesarr/seo-agent-opencode
git diff origin/dev-ai...origin/<branch> --check
```

O revisor deve comparar o veredito com o `headRefOid` atual. `COMMENTED`, `PENDING`, ausência de review ou review de SHA anterior não encerram a revisão.

## Aprovação e merge

```bash
gh pr review <n> --repo renancesarr/seo-agent-opencode \
  --approve --body "Verificação concluída. Signed-by: <revisor>"
gh pr merge <n> --repo renancesarr/seo-agent-opencode --merge
```

O merge em `dev-ai` só ocorre após aprovação do revisor da direção correta. Depois de três falhas automáticas, o PR permanece aberto e é notificado ao humano.

## Promoção para `main`

Agentes não fazem promoção automática para `main`. Um humano deve revisar o PR `dev-ai → main` e executar a decisão de merge conforme a proteção da branch.

## Exceção humana

Uma solicitação explícita pode autorizar uma ação concreta em um PR concreto. A justificativa deve ser registrada no commit ou review; a exceção não muda a propriedade das branches nem autoriza bypass geral.
