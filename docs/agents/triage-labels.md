# Vocabulário de triagem

| Papel | Label | Significado |
|---|---|---|
| needs-triage | needs-triage | Precisa de avaliação inicial. |
| needs-info | needs-info | Aguarda informação que impede especificar o trabalho. |
| ready-for-agent | ready-for-agent | Especificado para execução por agente; respeitar blockers. |
| ready-for-human | ready-for-human | Requer ação humana. |
| wontfix | wontfix | Não será executado. |

`ready-for-agent` não significa que dependências ou credenciais externas já
foram atendidas. A implementação começa somente quando os blockers permitem.

Signed-by: ai-codex (GPT-6 Astra Ultra)
