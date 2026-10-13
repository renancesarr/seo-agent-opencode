# T01 — Interfaces locais e decisões técnicas

Inspeção realizada em 13/10/2026. Estes resultados descrevem o ambiente
inspecionado; uma instalação nova deve repetir os comandos.

| Comando local executado | Resultado observado |
|---|---|
| `opencode --version` | 1.18.35 |
| `opencode run --help` | Execução sem interação por padrão; opções `--agent`, `--model`, `--dir`, `--format json`. |
| `opencode agent create --help` | Modos `all`, `primary`, `subagent`; ferramentas incluem `bash`, `read`, `webfetch` e `websearch`. |
| `opencode mcp --help` | Interface para gerenciar servidores MCP disponível. |
| `opencode debug paths` | Diretório global de configuração identificado; seu conteúdo não foi lido. |
| `ollama --version` | 0.34.2 |
| `python3 --version` | 3.14.4 |
| `node --version` | 24.21.0 |
| `python3 -c 'import sqlite3; print(sqlite3.sqlite_version)'` | 3.46.1 |
| `OLLAMA_HOST=http://127.0.0.1:11434 ollama list` | Serviço respondeu; seis modelos instalados, incluindo `deepseek-r1:32b` e `qwen27b-direto:latest`. |
| `OLLAMA_HOST=http://127.0.0.1:11434 ollama ps` | Serviço respondeu; nenhum modelo carregado na inspeção. |

## Invocação sustentada pela ajuda

```bash
opencode run --dir <repo> --agent <agente-configurado> \
  --model <provider>/<model> --format json "<instrução>"
```

Este é o formato observado, não um smoke test de inferência executado.
`--format json` produz eventos do OpenCode; não garante o formato do conteúdo
SEO. Agente, provedor, permissões efetivas e resposta do modelo serão verificados
em T04. Nenhum prompt foi enviado ao modelo durante T01.

## Decisões para o primeiro incremento

- **Python stdlib:** a ferramenta `bash` do OpenCode permite chamar uma CLI;
  validar configuração e registrar execuções não exige SDK ou plugin novo.
  O funcionamento da invocação pelo agente será demonstrado em T04.
- **JSON:** entrada editável e saída estruturada para o chamador, sem parser extra.
- **SQLite:** registro transacional local com snapshots por execução e filtro
  por projeto. Não exige serviço de banco para atender T02.
- **CLI pública:** `validate`, `prepare` e `history`, descritos em [CLI.md](CLI.md).
  Os testes observam os comandos, sem depender do esquema interno do banco.

Essas são escolhas técnicas deste incremento, não mudanças nas decisões de
produto. [IDEIA.md](../IDEIA.md) mantém a visão futura de memória e observabilidade.
A configuração JSON do SearXNG e o leitor de páginas pertencem a T04; esta
inspeção não atesta seus serviços nem configura uma integração MCP.

Signed-by: ai-codex (GPT-6 Astra Ultra)
