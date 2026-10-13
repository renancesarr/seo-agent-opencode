# AGENTS.md — Executor de Possibilidades (seo-agent-infra)

Regras vinculantes para todos os agentes (ZCode/GLM-5.3, Codex/GPT-6 Astra Ultra, OpenCode).
Os Quatro Princípios Fundamentais (Think Before Coding, Simplicity First, Surgical Changes,
Goal-Driven Execution) vêm das instruções globais do usuário e continuam valendo aqui.

## Modelo de branches

| Branch | Papel | Quem escreve |
|---|---|---|
| `main` | Estável, verificada por humano | **Somente humano** (merge de `dev-ai` após verificação humana) |
| `dev-ai` | Integração contínua das IAs | Somente **merges de review aprovado** (ou humano) |
| `zcode-ai` | Workspace de desenvolvimento do ZCode | ZCode |
| `codex-ai` | Workspace de desenvolvimento do Codex | Codex |
| `code-review/<id>-<codou>-<revisor>` | Branch de review cruzado | Criada sob demanda |

> Nota: `:` é caractere inválido em nomes de branch do git, por isso o separador é `/`.
> Exemplo: `code-review/007-zcode-codex` = trabalho codado por **zcode**, revisado por **codex**.

## Regras obrigatórias para agentes

1. **Nunca** commitar, mergear ou reescrever `main`. O merge `dev-ai` → `main` é humano.
2. Trabalhe **somente na sua branch**: `zcode-ai` (ZCode) ou `codex-ai` (Codex).
3. Antes de começar qualquer tarefa, sincronize com `dev-ai`:
   `git checkout <sua-branch> && git merge dev-ai`
4. Todo commit segue o padrão abaixo e leva o rodapé `Agent: zcode-ai` ou `Agent: codex-ai`.
5. Para integrar trabalho em `dev-ai`, abra uma branch de review a partir da sua branch:
   `git checkout -b code-review/<id>-<codou>-<revisor>`
   `<id>` é sequencial (001, 002, ...) ou o número da tarefa/issue.
6. **Quem codou não revisa.** O agente oposto faz o code review na branch de review,
   usando o checklist abaixo, e registra o veredito (aprovado / reprovações) no corpo
   do merge ou em `docs/reviews/<id>.md`.
7. Review **aprovado** → o revisor mergeia em `dev-ai`:
   `git checkout dev-ai && git merge --no-ff code-review/<id>-<codou>-<revisor>`
   Review **reprovado** → revisor documenta os problemas; o autor corrige na branch de
   origem e reabre (novo id ou mesmo id com sufixo `-r2`).
8. Nunca use `--no-verify`, nunca desative hooks, nunca faça push --force em branches compartilhadas.

## Padrão de commit

```
<tipo>(<escopo>-opcional): <descrição curta, imperativo>

[corpo opcional: o quê e por quê]

[rodapés]
Agent: zcode-ai | codex-ai
Refs: code-review/<id> (quando houver)
```

Tipos: `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `seo`

Exemplos:
- `feat(scraper): adicionar cliente da API JSON do SearXNG`
- `fix(compose): corrigir porta do FalkorDB`
- `seo(blog): reescrever introdução da home em practice-first`

## Checklist de code review (revisor deve verificar tudo)

- [ ] Commits seguem o padrão e trazem o rodapé `Agent:` correto
- [ ] Diff mínimo e cirúrgico: toda linha mudada traça diretamente à tarefa
- [ ] Sem overengineering: nada especulativo, sem abstração para uso único (Simplicity First)
- [ ] Nenhuma "melhoria" em código adjacente não solicitada (Surgical Changes)
- [ ] Verificação explícita do resultado: comando/teste executado e reportado (Goal-Driven)
- [ ] Documentação atualizada quando o comportamento muda

## Enforcement

- Hook `commit-msg` valida o padrão de mensagem (merges são isentos).
- Hook `pre-commit` bloqueia commits de agente em `main` e commits não-merge em `dev-ai`.
  Humano: use `GIT_HUMAN=1 git commit ...` quando precisar escrever nessas branches.
