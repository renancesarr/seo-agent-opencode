# Contrato da primeira versão do agente SEO

## Objetivo e precedência

Construir uma ferramenta genérica de SEO nativa do OpenCode. Um projeto fornece
palavras-chave e contexto; o agente pesquisa, lê páginas e entrega outlines com
fontes e oportunidades justificadas. A ferramenta atende negócios de diferentes
setores e projetos que ainda não possuem site publicado.

Este documento consolida o escopo decidido na conversa de 13/10/2026.
[IDEIA.md](../IDEIA.md) preserva a visão de longo prazo; a primeira entrega segue
este contrato. [EXECUCAO.md](EXECUCAO.md) define a ordem de desenvolvimento.
[AGENTS.md](../AGENTS.md) rege autoria, revisão e integração do código.

## Decisões confirmadas

| ID | Decisão do usuário |
|---|---|
| D01 | O produto é um agente SEO para OpenCode, aplicável a diferentes negócios. |
| D02 | A entrada inicial é palavra-chave e contexto do negócio. |
| D03 | O agente busca resultados, lê páginas relevantes e entrega outline com fontes e oportunidades justificadas. |
| D04 | Acompanha concorrentes indicados e descobre outras páginas, registrando o motivo da seleção. |
| D05 | Executa diariamente, com execução manual disponível. |
| D06 | Preserva histórico; uma mudança relevante pode originar nova versão do outline. |
| D07 | Avisa sobre mudanças relevantes e falhas que precisem de intervenção. |
| D08 | Pesquisa, oportunidades e outlines passam por aprovação humana; publicação automática fica fora desta versão. |
| D09 | O portal de igrejas é um futuro caso de validação. A tarefa atual é desenvolver a ferramenta e seu processo. |

## Entrada e saída do processo

O contrato lógico abaixo orienta a implementação. O formato de configuração e
os nomes dos comandos serão definidos após verificar a instalação do OpenCode.

**Entrada por projeto:** identificador, contexto do negócio, público, idioma,
recorte geográfico, palavras-chave e objetivo do conteúdo. Domínios próprios
são opcionais; concorrentes e fontes podem ser informados como sementes.
Configurações e histórico pertencem ao projeto correspondente.

**Saída por execução:**

- Consultas utilizadas e páginas selecionadas, com motivo da seleção.
- Evidências das páginas efetivamente lidas: URL, momento da coleta e trechos
  ou fatos que sustentam a análise; falhas de leitura ficam identificadas.
- Oportunidades com justificativa, referências e distinção entre evidência e
  hipótese. Uma ausência no conjunto lido não prova ausência em toda a web.
- Outline: intenção de busca, público, título proposto, hierarquia de seções,
  conteúdo esperado em cada seção e fontes relacionadas.
- Pendências de informação e estado da revisão humana da versão produzida.
- Comparação com a execução anterior, quando existir.

Datas de publicação, de coleta e do evento são informações diferentes.
Horários, locais e datas sem confirmação permanecem como pendência.
Resultados de busca, páginas lidas e posição observada na resposta devem ser
distinguíveis; a ferramenta não apresenta a ordenação de um metabuscador como
posição comprovada no Google, nem inventa volume de busca ou dificuldade.

## Procedimento de execução

Estas são convenções operacionais propostas para implementar D01–D09.

| Etapa | Ação | Condição de conclusão |
|---|---|---|
| 1. Preparar | Carregar o projeto e validar entrada e limites de execução. | Contexto suficiente; campos ausentes explicados antes da consulta. |
| 2. Descobrir | Consultar palavras-chave e combinar resultados com fontes indicadas. | Lista de candidatos com consulta, URL e motivo de seleção. |
| 3. Ler | Extrair conteúdo das páginas selecionadas. | Evidências acessíveis registradas; páginas indisponíveis identificadas. |
| 4. Analisar | Relacionar intenção, assuntos cobertos e oportunidades ao contexto. | Observações rastreáveis às evidências; hipóteses sinalizadas. |
| 5. Propor | Produzir outline a partir da análise. | Cada oportunidade tem justificativa e fonte, ou é marcada como hipótese. |
| 6. Registrar | Salvar entrada, evidências, resultado e diferença em relação ao histórico. | A execução anterior continua recuperável. |
| 7. Revisar | Apresentar a versão para aprovação ou pedido de ajuste humano. | Decisão vinculada à versão; uma alteração posterior volta à revisão. |

Uma execução sem evidências suficientes termina com pendências explícitas,
sem fabricar um outline fundamentado. A aprovação editorial autoriza considerar
aquela versão revisada; a primeira entrega termina antes da publicação.

## Monitoramento diário

O disparo diário e o manual usam o mesmo processo e a mesma configuração.
Cada execução compara as fontes com o histórico do próprio projeto:

- Mudança relevante: registrar a evidência e propor atualização para revisão.
- Sem mudança relevante: registrar a execução, preservando o outline anterior.
- Falha que exige intervenção: preservar o último resultado válido e avisar.

Mudanças em assuntos cobertos, informações factuais, novos candidatos relevantes
ou informações de eventos são candidatos à análise. Ruído de apresentação,
como contadores e rodapés, não deve sozinho criar uma nova proposta.
A regra de comparação deve ser demonstrada com exemplos alterados e inalterados.

## Limites e decisões técnicas pendentes

A visão existente prevê OpenCode, Ollama e SearXNG. Suas interfaces, versões e
disponibilidade precisam de verificação local antes da integração. Redis,
Qdrant, FalkorDB, Graphiti e Langfuse pertencem à arquitetura pretendida em
IDEIA.md; sua instalação não é um pré-requisito automático deste incremento.
A implementação deve justificar cada dependência pelo critério que ela atende.

Antes de ativar o monitoramento, definir: horário e fuso, limites de consultas,
páginas e tempo por execução, comportamento quando a máquina estiver desligada,
canal de aviso e local de revisão. A frequência diária já está decidida.

O desenvolvedor deve registrar a escolha de persistência, leitor de páginas,
integração com OpenCode e regra de comparação junto à tarefa que os implementa.
Questões técnicas verificáveis são investigadas no ambiente; preferências do
operador ainda não informadas são solicitadas quando bloquearem a tarefa.

Geração de páginas, publicação, venda de publicidade e construção do portal
ficam em etapas futuras. Nesta tarefa de organização, usa-se a conversa e o
repositório; pesquisas comerciais e coleta real do piloto ficam para execução
da ferramenta quando solicitadas.

## Contexto do futuro piloto

O cenário informado pelo usuário é um diretório de igrejas com localização,
horários, eventos e ações comunitárias. Igrejas Brasil reúne busca e resumos;
as fichas completas pertencem aos subportais católico e evangélico/protestante,
com cadastro compartilhado e organização por estado e cidade.

O recorte inicial é Morrinhos-GO e outras duas cidades goianas com menos de
60 mil habitantes. A seleção das demais cidades não bloqueia o desenvolvimento
do agente. O objetivo futuro do portal inclui publicidade para igrejas e membros.
Esses dados pertencem à configuração do piloto, nunca a regras fixas do agente.

## Critério de entrega

O MVP estará pronto quando os testes e evidências de T01–T06 em
[EXECUCAO.md](EXECUCAO.md) demonstrarem o fluxo manual, a integração com OpenCode,
histórico, revisão e execução diária. A existência desta documentação não
significa que essas capacidades estejam implementadas.

Signed-by: ai-codex (GPT-6 Astra Ultra)
