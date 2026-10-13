# AGENTS.md — Executor de Possibilidades (seo-agent-opencode)

Regras vinculantes para todos os agentes (ZCode/GLM-5.3, Codex/GPT-6 Astra Ultra, OpenCode).
Os Quatro Princípios Fundamentais (Think Before Coding, Simplicity First, Surgical Changes,
Goal-Driven Execution) vêm das instruções globais do usuário e continuam valendo aqui.

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

1. **Sincronize** antes de começar qualquer tarefa:
   `git checkout <sua-branch> && git merge origin/dev-ai`
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
4. **Review cruzado — quem codou não revisa.** O agente oposto revisa o PR:
   ```bash
   gh pr diff <n>            # ler a mudança
   gh pr review <n> --request-changes --body "problemas encontrados... Signed-by: ..."
   gh pr review <n> --approve --body "LGTM. Signed-by: ai-codex (GPT-6 Astra Ultra)"
   ```
   Use o checklist do template; register reprovações concretas e acionáveis.
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

## Enforcement

- Hook `pre-commit`: bloqueia agente em `main`, commit não-merge em `dev-ai`, e
  commits sem a identidade assinada correta em `zcode-ai`/`codex-ai`.
  Humano: prefixe `GIT_HUMAN=1` quando precisar escrever nessas branches.
- Hook `commit-msg`: valida o padrão de mensagem (merges são isentos).
- GitHub: proteção de branch em `main`/`dev-ai` (a configurar quando houver token).
