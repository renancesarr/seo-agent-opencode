# Ownership da revisão cruzada

status: accepted

PRs `zcode-ai → dev-ai` são revisados pelo `ai-codex`; PRs `codex-ai → dev-ai` são revisados pelo `ai-zcode`. O agente autor não revisa nem aprova o próprio trabalho, e cada novo Head SHA invalida o veredito anterior. Essa separação mantém a revisão independente sem impedir a integração contínua em `dev-ai`.
