# Executor de Possibilidades — seo-agent-opencode

Sistema multiagente **open source** de SEO de ponta a ponta e engenharia de software
assistida por IA. **Nativo do OpenCode** (runtime), **desenvolvido por dois agentes de
IA com review cruzado obrigatório**: código do `ai-zcode` (ZCode/GLM-5.3) é revisado
pelo `ai-codex` (Codex/GPT-6 Astra Ultra), e vice-versa. `main` é branch humana.

## O que faz

A visão do produto cobre todas as fases de SEO com subagentes especializados:

- **Inteligência de concorrentes** — quem disputa a SERP, o que fazem, quais gaps deixaram
- **Keyword research & clustering**
- **Arquitetura de página AI-readable** — seções claras e navegáveis que LLMs e buscadores entendem
- **Desenvolvimento front-end** (HTML/CSS/JS) das páginas
- **Copywriting humanizado practice-first** — caso de uso real antes de explicação
- Refatoração de código assistida por memória de longo prazo e debugging recursivo

A visão completa, arquitetura e roadmap estão no [IDEIA.md](IDEIA.md).

## Desenvolvimento da primeira versão

O [contrato do MVP](docs/SEO-AGENT-MVP.md) registra as decisões atuais.
Para implementar ou retomar uma tarefa, siga o [processo de execução](docs/EXECUCAO.md):
entrada por projeto → pesquisa → leitura → análise → outline → revisão humana,
com histórico e monitoramento diário. A primeira CLI valida projetos e prepara execuções com histórico local; veja
os [comandos e a configuração](docs/CLI.md). Também oferece busca via
[SearXNG local](docs/BUSCA-WEB.md) e inspeção de conteúdo/sinais SEO de páginas.
Para configurar `.env` e obter credenciais dos provedores, veja
[chaves e buscadores](docs/CHAVES-BUSCADORES.md).
O lote seleciona as APIs com credenciais completas automaticamente.
O [backlog de experimentos](docs/BACKLOG.md) inclui a avaliação do Kitesurf.
[Navegação por jornadas e telas](docs/NAVEGACAO-CONCORRENTES.md) está implementada;
análise por modelo e geração de outlines continuam nas próximas tarefas do roteiro.

## Workflow de desenvolvimento (o diferente deste repo)

```
main (humana)  ←  dev-ai (integração)  ←  zcode-ai / codex-ai
                        ↑
              PR + review cruzado obrigatório
     (quem codou nunca revisa; aprovação cruzada exigida)
```

- Commits assinados por agente: `ai-zcode` / `ai-codex`
- Review acontece em **Pull Requests**, com checklist e assinatura `Signed-by`
- Hooks locais (`pre-commit`, `commit-msg`, `pre-push`) impõem as regras,
  incluindo identidade efetiva do autor; a proteção remota no GitHub
  (aprovação obrigatória em `dev-ai`) está em ativação

As regras completas (fluxo, padrão de commit, checklist de review) estão no
[AGENTS.md](AGENTS.md) — agents e humanos devem lê-lo antes de contribuir.

## Stack (resumo)

OpenCode (runtime) · Ollama com LLMs locais · SearXNG (busca) · Qdrant (vetorial) ·
FalkorDB (grafo) · Redis (cache) · LangChain · Langfuse (observabilidade) · Docker Compose.

## Como contribuir

1. Leia o [AGENTS.md](AGENTS.md) (regras de workflow e padrão de commit)
2. Abra uma issue descrevendo o problema/proposta
3. Branch a partir de `dev-ai` → commits no padrão → PR para `dev-ai`

## Licença

[MIT](LICENSE) © 2026 Renan Rabelo
