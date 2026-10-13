# HANDOFF — Orientação do Codex (ai-codex)

Bem-vindo ao projeto. Este documento te orienta: quem você é aqui, o que ler,
como agir e qual é a sua primeira tarefa. Leia até o fim antes de executar algo.

## 1. O projeto em um parágrafo

**Executor de Possibilidades** (`seo-agent-opencode`): sistema multiagente
**open source** de **SEO de ponta a ponta** e engenharia de software assistida
por IA. O produto final roda no **OpenCode** (subagentes, skills, MCP); o
desenvolvimento é feito por **dois agentes de IA com review cruzado
obrigatório**: você (`ai-codex`, GPT-6 Astra Ultra) e o `ai-zcode`
(GLM-5.3). Código seu é revisado pelo ZCode; código do ZCode é revisado por
você. A branch `main` é exclusivamente humana.

## 2. Arquivos para ler (nesta ordem)

| Arquivo | Por quê |
|---|---|
| [AGENTS.md](AGENTS.md) | **Regras vinculantes do workflow** — fluxo, identidade, padrão de commit, checklist de review. É a sua lei aqui. |
| [README.md](README.md) | Visão geral do projeto e do modelo de branches |
| [IDEIA.md](IDEIA.md) | Spec completa do produto: camadas, subagentes de SEO, stack, fases, critérios de sucesso |
| [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) | Checklist que você usa como autor e como revisor de PRs |
| `spec-dev-ai.md` | ⚠️ **Histórico, NÃO usar**: spec antiga com mecanismos inválidos (zcode-config.yaml, codex-config.json etc.). Foi substituída pelo AGENTS.md + IDEIA.md. |

Os **Quatro Princípios Fundamentais** (Think Before Coding, Simplicity First,
Surgical Changes, Goal-Driven Execution) já estão nas suas instruções globais
(`~/.codex/AGENTS.md`) e regem todo o trabalho aqui.

## 3. Sua identidade (obrigatória, enforceada por hooks)

- **Commits** (sempre com estas flags, na branch `codex-ai`):
  ```bash
  git -c user.name=ai-codex -c user.email=261107596+Fencing3422@users.noreply.github.com commit -m "..."
  ```
- **Push**: `git push` simples, já estando em `codex-ai` — o transporte roteia
  pela sua conta bot (remote `origin-codex`, chave `~/.ssh/id_ed25519_ai_codex`).
  Não nomeie o remote no push.
- **GitHub CLI**: rode como sua conta bot, sem trocar a conta ativa:
  ```bash
  GH_TOKEN="$(gh auth token --user Fencing3422)" gh <comando>
  ```
  A conta ativa do `gh` é `renancesarr` (do ZCode) — **nunca** use
  `gh auth switch`, nunca faça login/logout.
- **Assinatura** em PRs, issues e reviews:
  `Signed-by: ai-codex (GPT-6 Astra Ultra)`

## 4. Regras de ouro

1. **Nunca** commita, mergeia ou reescreve `main` (branch humana).
2. `dev-ai` só recebe **merge de PR aprovado** por você ou pelo ZCode —
   nunca commit direto.
3. Você desenvolve **somente na `codex-ai`**; sincronize antes de cada tarefa:
   `git checkout codex-ai && git merge origin/dev-ai`
4. **Quem codou não revisa**: você revisa PRs do ZCode; o ZCode revisa os seus.
5. Nunca `--no-verify`, nunca desativar hooks, nunca force-push em branches
   compartilhadas.
6. Padrão de commit: `<tipo>(<escopo>?): <descrição>` —
   tipos `feat fix docs style refactor perf test build ci chore seo`.
7. Os hooks do repo (`commit-msg`, `pre-commit`) bloqueiam violações — se um
   hook te barrar, ele está certo; corrija a ação, não o hook.

## 5. Fluxo de trabalho (ciclo completo)

```
1. git checkout codex-ai && git merge origin/dev-ai     # sincroniza
2. desenvolve; commits assinados                         # sua branch
3. git push                                               # vai como Fencing3422
4. GH_TOKEN=... gh pr create --base dev-ai --head codex-ai \
     --title "[ai-codex] resumo" --body-file .github/PULL_REQUEST_TEMPLATE.md
5. ZCode revisa (conta renancesarr)                       # review cruzado
6. aprovado → quem revisou executa: gh pr merge <n> --merge
7. humano homologa dev-ai → main
```

## 6. Estado atual do projeto (out/2026)

- **Infra de workflow pronta e testada**: branches (`main`, `dev-ai`,
  `zcode-ai`, `codex-ai`), hooks locais, contas separadas, PR template,
  MIT license, README.
- **PR #1 aberto** (6 commits, autor `ai-zcode`): todo o workflow de review
  via PR + assinaturas + contas GitHub separadas. Aguardando **a sua revisão**.
- **Proteção de branch no GitHub pendente**: o token do humano ainda não tem
  permissão Administration; quando ativar, `dev-ai` exigirá 1 aprovação
  (a sua, em PRs do ZCode) e `main` só aceitará PR.
- **Produto em Fase 1** (ver IDEIA.md §7): `docker-compose.yml` com SearXNG
  existe, mas falta `searxng/settings.yml` (habilitar API JSON) e subir;
  Ollama já roda com deepseek-r1:32b e Qwen 27B; container `crawl4ai-mcp`
  existe parado.
- **Skills locais** em `~/.agents/src/` (mattpocock + karpathy), ligadas em
  `~/.agents/skills/` e `~/.codex/skills/` — disponíveis para você.

## 7. Sua tarefa imediata

**Revise o PR #1** seguindo o checklist do template:

```bash
git fetch origin
GH_TOKEN="$(gh auth token --user Fencing3422)" gh pr diff 1 --repo renancesarr/seo-agent-opencode
```

Verifique: regras do AGENTS.md coerentes e executáveis, mensagens de commit no
padrão, hooks corretos, sem overengineering. Se aprovado:

```bash
GH_TOKEN="$(gh auth token --user Fencing3422)" gh pr review 1 --approve \
  --body "Aprovado: <resumo da verificação>. Signed-by: ai-codex (GPT-6 Astra Ultra)"
GH_TOKEN="$(gh auth token --user Fencing3422)" gh pr merge 1 --merge
```

Se reprovar: `--request-changes` com problemas concretos e acionáveis.
Documente decisões duvidosas como issues (`gh issue create`, com `Signed-by`).
