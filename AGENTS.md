# AGENTS.md — Executor de Possibilidades (seo-agent-opencode)

Regras vinculantes para todos os agentes (ZCode/GLM-5.3, Codex/GPT-6 Astra Ultra, OpenCode).
Os Quatro Princípios Fundamentais (Think Before Coding, Simplicity First, Surgical Changes,
Goal-Driven Execution) vêm das instruções globais do usuário e continuam valendo aqui.

## Desenvolvimento do produto

Ao implementar ou retomar o agente SEO, leia [docs/SEO-AGENT-MVP.md](docs/SEO-AGENT-MVP.md)
e execute a primeira tarefa disponível de [docs/EXECUCAO.md](docs/EXECUCAO.md).
Registre verificação e estado da tarefa antes de avançar.

## Agent skills

### Issue tracker

Especificações e tickets vivem no GitHub Issues de `renancesarr/seo-agent-opencode`.
Veja [configuração do tracker](docs/agents/issue-tracker.md).

### Triage labels

Usar `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human` e `wontfix`.
Veja [vocabulário de triagem](docs/agents/triage-labels.md).

### Domain docs

Domínio único: leia GLOSSARY.md, o contrato do MVP e os ADRs pertinentes antes
de escrever specs ou tickets. Veja [documentos do domínio](docs/agents/domain.md).

## Identidade e assinatura

Cada agente assina tudo o que produz (commits, PRs, issues, reviews) e empurra
pela própria conta GitHub:

| Agente | Identidade git (commits) | Assinatura | Conta GitHub / transporte |
|---|---|---|---|
| ZCode | `-c user.name=ai-zcode -c user.email=ai-zcode@users.noreply.github.com` | `Signed-by: ai-zcode (GLM-5.3)` | `origin` (conta `renancesarr`, chave padrão) |
| Codex | `-c user.name=ai-codex -c user.email=261107596+Fencing3422@users.noreply.github.com` | `Signed-by: ai-codex (GPT-6 Astra Ultra)` | conta bot `Fencing3422`, via `origin-codex` (chave `~/.ssh/id_ed25519_ai_codex`; `branch.codex-ai.pushRemote` já configurado) |

O hook `pre-commit` **exige** a identidade correta na branch correspondente.
Empurre sempre com `git push` (sem nomear o remote): o git já roteia cada branch
para a conta certa. A separação de contas é o que permite ao GitHub **exigir 1
aprovação** em `dev-ai` — o autor do PR nunca é quem aprova.

**Conta do `gh` CLI**: a conta ativa é `renancesarr` (identidade do ZCode).
O Codex roda comandos `gh` como a conta bot **sem trocar a conta ativa**:

```bash
GH_TOKEN="$(gh auth token --user Fencing3422)" gh <comando>
```

Nunca use `gh auth switch` durante tarefas: cada agente opera com sua conta
via `GH_TOKEN`, e a ativa permanece `renancesarr`.

## Modelo de branches e review

| Branch | Papel | Quem escreve |
|---|---|---|
| `main` | Estável, verificada por humano | **Somente humano** (merge de `dev-ai` após verificação) |
| `dev-ai` | Integração contínua das IAs | **Somente via PR aprovado** pelo agente oposto (ou humano) |
| `zcode-ai` | Workspace de desenvolvimento do ZCode | ZCode |
| `codex-ai` | Workspace de desenvolvimento do Codex | Codex |

O review acontece em **Pull Requests no GitHub** (`zcode-ai`/`codex-ai` → `dev-ai`).
O número do PR é o identificador do review (substituiu as antigas branches `code-review/<id>`).

## Fluxo obrigatório

1. **Sincronize** antes de começar qualquer tarefa — a identidade do agente
   assina também o commit de merge (quando não for fast-forward):
   ```bash
   git checkout <sua-branch>
   git -c user.name=ai-zcode -c user.email=ai-zcode@users.noreply.github.com \
     merge origin/dev-ai --no-edit
   ```
   (Codex usa a própria identidade nos flags `-c`.)
2. **Desenvolva** somente na sua branch, com commits no padrão abaixo e assinados
   com a sua identidade (`-c user.name=... -c user.email=...`).
3. **Abra o PR** para `dev-ai` (pela sua própria conta):
   ```bash
   git push                    # roteia para a conta certa da branch
   gh pr create --base dev-ai --head <sua-branch> \
     --title "[ai-zcode] resumo curto" \
     --body-file .github/PULL_REQUEST_TEMPLATE.md
   ```
   (Codex usa `[ai-codex]`; complete o corpo do template com o que fez e como verificou.)
4. **Review cruzado — quem codou não revisa.** O agente oposto revisa o PR
   (Codex revisa via conta bot; ZCode revisa com a conta ativa `renancesarr`):
   ```bash
   # ler a mudança
   GH_TOKEN="$(gh auth token --user Fencing3422)" gh pr diff <n>
   # reprovar (problemas concretos e acionáveis)
   GH_TOKEN="$(gh auth token --user Fencing3422)" gh pr review <n> --request-changes --body "problemas... Signed-by: ai-codex (GPT-6 Astra Ultra)"
   # aprovar
   GH_TOKEN="$(gh auth token --user Fencing3422)" gh pr review <n> --approve --body "LGTM. Signed-by: ai-codex (GPT-6 Astra Ultra)"
   ```
   Use o checklist do template; registre reprovações concretas e acionáveis.
5. **Aprovado → merge** (o revisor executa):
   `gh pr merge <n> --merge`
   Reprovado → o autor corrige na sua branch, push, e o PR reentra para novo review.
6. **Issues**: criar com `gh issue create`, título claro e corpo com contexto +
   rodapé `Signed-by: <agente> (modelo)`.
7. **Nunca**: commitar/mergear em `main` (agente), usar `--no-verify`, desativar
   hooks, ou fazer push --force em branches compartilhadas.

## Padrão de commit

```
<tipo>(<escopo>-opcional): <descrição curta, imperativo>

[corpo opcional: o quê e por quê]

[rodapé opcional: Refs: #<nº do PR>]
```

Tipos: `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `seo`

Exemplos:
- `feat(scraper): adicionar cliente da API JSON do SearXNG`
- `fix(compose): corrigir porta do FalkorDB`
- `seo(blog): reescrever introdução da home em practice-first`

## Checklist de code review (revisor deve verificar tudo)

- [ ] Commits assinados com a identidade correta (ai-zcode / ai-codex)
- [ ] Mensagens seguem o padrão
- [ ] Diff mínimo e cirúrgico: toda linha mudada traça diretamente à tarefa
- [ ] Sem overengineering: nada especulativo, sem abstração para uso único (Simplicity First)
- [ ] Nenhuma "melhoria" em código adjacente não solicitada (Surgical Changes)
- [ ] Verificação explícita do resultado: comando/teste executado e reportado (Goal-Driven)
- [ ] Documentação atualizada quando o comportamento muda

## Automação do review cruzado (event-driven)

O review é disparado automaticamente por um observador local (polling de 2 min,
indistinguível de webhook na prática para este fim):

- **`scripts/pr-watcher.sh`** (systemd user timer `seo-pr-watcher.timer`): quando um
  PR da `zcode-ai` para `dev-ai` não tem review do bot posterior ao último push,
  executa `codex exec` headless como `ai-codex` (com `GH_TOKEN` do `Fencing3422`),
  que publica o veredito e, se aprovar, faz o merge. PR da `codex-ai` notifica o
  humano (a automação do ZCode cobre o review desse lado).
- **Automação do ZCode** (cron do workspace, a cada 15 min): revisa PRs da
  `codex-ai` pendentes como `ai-zcode` e publica o veredito assinado.
- Estado e logs: `~/.local/state/pr-watcher/` (`watcher.log`, `codex-pr<N>-*.log`).
- Máximo de 3 tentativas automáticas por push; depois, notifica o humano.
- Comandos úteis: `systemctl --user list-timers seo-pr-watcher.timer`,
  `journalctl --user -u seo-pr-watcher.service` e rodar `./scripts/pr-watcher.sh`
  manualmente para uma passada imediata.

## Enforcement

- Hook `pre-commit`: bloqueia agente em `main` e commit não-merge em `dev-ai`.
- Hook `commit-msg`: valida o padrão de mensagem e a **identidade efetiva**
  (autor E committer — cobre `--author` e `GIT_AUTHOR_*`/`GIT_COMMITTER_*`),
  inclusive em merges (o `pre-commit` não roda neles); bloqueia merges de
  agente em `main`.
- Hook `pre-push`: backstop final — valida autor e committer dos **objetos
  reais** empurrados para `zcode-ai`/`codex-ai`; commits já presentes no
  remoto (herdados de `dev-ai` em merge de sincronização) são isentos.
- Humano: prefixe `GIT_HUMAN=1` quando precisar escrever nessas branches.
- GitHub: proteção de branch em `main`/`dev-ai` (a configurar quando houver token).
