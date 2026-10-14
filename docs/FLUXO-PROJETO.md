# Pesquisa, outline e revisão por projeto

Implementação da [especificação #9](https://github.com/renancesarr/seo-agent-opencode/issues/9).
Não há publicação automática. Execute pela raiz do repositório:

```bash
python3 -B -m seo_agent run --project examples/projeto.json --store data/seo-agent.sqlite3
python3 -B -m seo_agent history --project-id horta-local --store data/seo-agent.sqlite3
python3 -B -m seo_agent notices --project-id horta-local --store data/seo-agent.sqlite3
```

`run` combina palavras-chave e localização, APIs com credenciais completas e
SearXNG local por padrão. `--no-searxng` desliga essa fonte; URLs em `sources` e
`competitors` permitem coleta sem buscadores. `--max-pages` limita tentativas
de leitura e `--max-queries` consultas completas, ambos com padrão 10.
O intervalo de 300 segundos é entre consultas completas. Entrada inválida falha
antes da busca. Execuções do mesmo projeto/store não se sobrepõem.

Cada execução guarda contexto, candidatos, motivos, consultas/provedores,
fontes HTML HTTP 200, URL inicial/final, momento da leitura, texto, sinais SEO
e falhas. Frequência de aparição não prova volume ou dificuldade SEO.
O leitor inicial não executa JavaScript nem comprova conteúdo dinâmico completo:
fontes mostram `javascript_rendered: false`.

```bash
python3 -B -m seo_agent run --project examples/projeto.json --model ollama/gemma4:e4b
```

O modelo é explícito. A configuração global é consultada somente para o provedor;
o Ollama utiliza `127.0.0.1:11434/v1`. OpenCode executa em diretório/configuração
temporários, com `--pure`, compartilhamento desligado e todas as permissões
negadas. Páginas são dados, não instruções para ferramentas. Limite do gerador:
300 segundos; contexto anunciado 8192 e saída 2048 tokens. Isso não muda o
`num_ctx` do servidor, não baixa modelos nem altera a configuração global.

O smoke real de 13/10/2026 leu uma página pública e gerou JSON válido com
`ollama/gemma4:e4b` (OpenCode 1.18.35, Ollama 0.34.2). O modelo originalmente
configurado, Qwen 27B, excedeu 300 segundos. Dolphin retornou texto/Markdown
e foi rejeitado. Essas falhas permaneceram no histórico, sem falsa versão válida.
Este smoke técnico não é aceite editorial nem prova de qualidade em todo negócio.

Para testar um gerador controlado, `--proposal-file proposta.json` importa JSON
para validação. Esse modo não executa LLM. Contrato:

```json
{
  "title": "Título proposto",
  "audience": "Público definido",
  "search_intent": "Intenção de busca",
  "sections": [{"heading": "Seção", "content": "Conteúdo esperado", "references": ["https://fonte-real-lida.example/pagina"]}],
  "opportunities": [{"description": "Oportunidade", "justification": "Por que investigar", "kind": "hypothesis", "references": []}],
  "pending": ["O que ainda precisa ser confirmado"]
}
```

Use URLs realmente lidas naquela execução. Seções e oportunidades `observation`
exigem fontes; `hypothesis` distingue sugestões não comprovadas. Sem fonte HTML
HTTP 200 não há geração. Referência válida comprova origem, não a adequação da
afirmação: isso exige revisão humana. JSON inválido, fonte inventada ou erro do
modelo ficam como falha/pendência e conservam versões anteriores.

```bash
python3 -B -m seo_agent outline --project-id PROJETO --version-id VERSAO
python3 -B -m seo_agent review --project-id PROJETO --version-id VERSAO --decision approve
python3 -B -m seo_agent review --project-id PROJETO --version-id VERSAO --decision request-changes --reason 'Detalhar fontes e conteúdo'
```

Use o mesmo `--store` se alterou o padrão. `version_id` e `created_run_id`
identificam proposta e origem. Decisões são acrescentadas sem modificar snapshots.
`outline` mostra a última decisão e todas as anteriores; `history` preserva o
estado original da execução. Uma nova versão sempre começa `pending`.

Comparação usa texto normalizado, título, descrição, headings, JSON-LD e contexto
do projeto. CSS/espaços sem alterar esses sinais conservam a versão e dispensam
geração. Fonte nova lida ou mudança nesses sinais justifica nova proposta para
revisão, sem provar relevância editorial. Falhas/fontes indisponíveis não provam
remoção factual. Versão conservada aponta a execução e fontes originais.
Após pedido de ajustes, a justificativa humana também autoriza nova geração
com fontes inalteradas; ela é entregue ao gerador e a nova versão volta a `pending`.
Recuperação de fonte compara com a execução original da versão, sem criar
atualização falsa depois de uma rodada parcial.
Avisos locais distinguem versão e falha, com identificadores para consulta.
O mesmo fato inalterado não é avisado novamente. Não há envio externo.

## Agendamento explícito

O usuário definiu 8h e 20h, fuso `America/Sao_Paulo`, 10 consultas, 20 páginas,
15 minutos, intervalo de um minuto entre consultas e descarte dos horários perdidos. O projeto escolhido é
`examples/igrejas-go.json`: nove consultas, três tipos de igrejas nas três cidades.
A configuração correspondente está em `examples/schedule-igrejas-go.json`.
Nenhum serviço permanente foi instalado nesta entrega. Configuração confirmada:

```json
{
  "project": "../examples/projeto.json",
  "store": "../data/seo-agent.sqlite3",
  "hours": ["08:00", "20:00"],
  "timezone": "America/Sao_Paulo",
  "max_queries": 10,
  "max_pages": 20,
  "max_seconds": 900,
  "interval_seconds": 60,
  "recovery": "skip",
  "model": "ollama/gemma4:e4b",
  "env_file": "../.env",
  "no_searxng": false
}
```

Salve em `data/schedule.json`; caminhos são relativos a esse arquivo.
`once` recupera somente o horário mais recente perdido; `skip` executa apenas
no minuto exato do horário, sem recuperação. Uma tentativa por horário fica
persistida; falha/interrupção não autoriza repetição automática naquele horário.
Uma execução manual permanece disponível para investigar/repetir.

```bash
python3 -B -m seo_agent schedule-tick --config data/schedule.json
python3 -B -m seo_agent monitor --config data/schedule.json
```

`schedule-tick` executa o horário devido ou informa `already_claimed`/`not_due`.
`monitor` verifica a cada minuto e termina com Ctrl-C, interrompendo seu worker.
Worker chama a mesma CLI `run`; o limite de tempo encerra o grupo de processos
e registra falha. SQLite mantém horários e o histórico. O lock é por projeto e
store: use um único store operacional para não separar o controle de concorrência.
Após encerramento abrupto do monitor, o horário pode permanecer reclamado;
investigue pelo histórico e repita manualmente, sem apagar o controle de horários.
Não houve instalação de serviço nem ativação permanente nesta implementação.

### Projeto escolhido: igrejas em Goiás

```bash
python3 -B -m seo_agent validate --project examples/igrejas-go.json
python3 -B -m seo_agent run --project examples/igrejas-go.json --store data/igrejas-go.sqlite3 --model ollama/gemma4:e4b --max-pages 20 --max-queries 10 --interval-seconds 60
python3 -B -m seo_agent monitor --config examples/schedule-igrejas-go.json
```

Morrinhos, Piracanjuba e Goiatuba recebem consultas gerais, evangélicas e
católicas. Os quatro domínios são contexto do projeto, não fontes já publicadas.
Busca e leitura descobrem candidatos; eventos só entram quando houver evidência.
O usuário reduziu o intervalo deste projeto para um minuto: as nove consultas
têm oito minutos de espera, mantendo 15 minutos de teto. Coleta e modelo ainda
podem exceder o restante; nesse caso o scheduler registra falha e conserva a
versão anterior, sem prometer conclusão de toda rodada. Sem configuração de
intervalo, outros agendamentos preservam o padrão anterior de 300 segundos.

Contrato técnico do OpenCode conferido nas docs de
[configuração](https://opencode.ai/docs/config/),
[agentes](https://opencode.ai/docs/agents/) e
[Ollama](https://opencode.ai/docs/providers/#ollama).

Signed-by: ai-codex (GPT-6 Astra Ultra)
