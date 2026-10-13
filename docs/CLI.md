# Configuração e preparação de execuções

A CLI implementa T02 do [processo de desenvolvimento](EXECUCAO.md).
Execute os comandos na raiz do repositório com Python 3.11 ou superior
(testado com 3.14.4). Usa apenas a biblioteca padrão, sem instalação de pacotes.

## Comandos disponíveis

```bash
# Validar a entrada sem gravar uma execução
python3 -m seo_agent validate --project examples/projeto.json

# Registrar uma execução preparada e seu contexto
python3 -m seo_agent prepare --project examples/projeto.json

# Recuperar as execuções desse projeto, em ordem de registro
python3 -m seo_agent history --project-id horta-local
```

`prepare` e `history` aceitam `--store <arquivo.sqlite3>` para escolher o
armazenamento. O padrão é `data/seo-agent.sqlite3`, relativo ao diretório atual,
ignorado pelo Git. Use o mesmo arquivo para consultar as execuções registradas.
Uma consulta sem histórico devolve lista vazia e não cria o banco.

Sucesso produz JSON em stdout e código de saída 0. Entrada inválida ou falha de
leitura/escrita produz mensagem em stderr e saída 2, sem traceback esperado.
`validate` verifica a estrutura local; não verifica sites ou disponibilidade de
fontes. Falha na validação acontece antes de abrir o banco.

## Contrato JSON do projeto

Copie [examples/projeto.json](../examples/projeto.json) e adapte seus valores.

| Campo | Formato | Regra |
|---|---|---|
| `id` | texto | Identificador estável: letras minúsculas sem acento, números e hífens entre palavras. |
| `business_context` | texto | Contexto do negócio. |
| `audience` | texto | Público que o conteúdo deve atender. |
| `language` | texto | Idioma desejado, por exemplo `pt-BR`. |
| `geography` | texto | Recorte geográfico, inclusive nacional ou global quando aplicável. |
| `keywords` | lista de textos | Pelo menos uma palavra-chave. |
| `content_goal` | texto | Resultado pretendido com o conteúdo. |
| `domains` | lista de textos, opcional | Domínios próprios, caso já existam. |
| `competitors` | lista de textos, opcional | Referências de concorrentes indicados. |
| `sources` | lista de textos, opcional | Fontes sementes indicadas. |

Textos vazios ou só com espaços são rejeitados. Listas opcionais podem ser
vazias; seus itens, quando presentes, precisam de texto. Campos desconhecidos
são rejeitados para tornar erros de digitação visíveis. Nesta etapa os valores
opcionais são metadados, sem resolução de domínio ou acesso a URLs.

O `id` distingue os históricos. Reutilizá-lo significa continuar o mesmo
projeto; trocar o contexto não modifica os snapshots das execuções anteriores.
Esta separação é organizacional em uma ferramenta local, não controle de acesso
entre usuários de um serviço multiusuário.

## Registro inicial

`prepare` gera `run_id`, `project_id`, `created_at` em UTC, `project` com o
snapshot da configuração, `status: "prepared"` e `result: null`.

O estado preparado significa que a entrada foi validada e registrada. Busca,
leitura, análise, outline e revisão ainda serão implementados em T03–T04.
Nenhum comando desta etapa executa pesquisa, modelo ou publicação.

## Verificação

```bash
python3 -B -m unittest discover -s tests -v
```

Os testes usam a CLI em novos processos e bancos temporários. Verificam negócios
diferentes, entrada inválida, persistência, preservação de snapshots e separação
por projeto, sem rede ou LLM.

Signed-by: ai-codex (GPT-6 Astra Ultra)
