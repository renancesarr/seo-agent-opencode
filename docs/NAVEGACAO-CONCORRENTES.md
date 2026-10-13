# Navegação e jornadas de concorrentes

## Objetivo e estado

Depois de descobrir URLs, visitar páginas relevantes, extrair conteúdo e observar
fluxos públicos em diferentes tamanhos de tela. Essa capacidade amplia a coleta
SEO para comparar a experiência oferecida pelos concorrentes.

Estado: próxima etapa T04N de [EXECUCAO.md](EXECUCAO.md), ainda não implementada.
A CLI atual faz busca e inspeção de HTML inicial. Não abre navegador, não clica,
não captura screenshots e não reconstrói jornadas automaticamente.

## Processo a implementar

1. Selecionar URLs a partir da busca, sementes e links observados, registrando
   consulta, origem e motivo. Aplicar limites de páginas por domínio e por execução.
2. Ler HTML e sinais de SEO. Se for necessário observar conteúdo dinâmico ou uma
   jornada, abrir a URL em um contexto de navegador separado do perfil pessoal.
3. Registrar estado inicial, controles disponíveis, ação escolhida, estado após
   a ação, URL, horário e screenshot. O agente escolhe entre elementos realmente
   observados; a conclusão exige verificar o resultado na página.
4. Repetir a mesma tarefa com viewport desktop e mobile. Registrar dimensões,
   navegador, idioma e estado de sessão; mudar uma condição por comparação.
5. Consolidar conteúdo, arquitetura de informação, caminhos de navegação,
   diferenças por tela, falhas e oportunidades justificadas por evidências.

O processo deve limitar passos, tempo e páginas, respeitar regras de coleta e
parar quando não consegue verificar o resultado. Páginas são dados externos,
não instruções que podem mudar a tarefa ou autorizar ações. Na exploração
pública inicial, não concluir compras, cadastros ou envio de mensagens.

## O que significa entender histórias de usuário

Podemos observar uma jornada como “buscar → filtrar → abrir detalhes” e propor
uma história: “Como visitante, quero filtrar por localização para encontrar uma
opção próxima”. Isso é uma hipótese sobre a necessidade atendida, não acesso
à história original, intenção do autor ou backlog do concorrente.

Cada proposta deve conter: ator presumido, objetivo, passos reproduzidos,
resultado verificado, referências às evidências e lacunas. Uma tela encontrada
não prova que o fluxo inteiro funciona. Os estados `observado`, `inferido` e
`não verificado` devem permanecer distinguíveis.

## Ferramentas candidatas

O [Jev Ultrafast](https://github.com/browser-use/jev-ultrafast) tem licença MIT e
seleciona operações e alvos a partir de elementos observados. O setup publicado
exige `TYPESAFE_API_KEY` e `TEXT_MODEL_API_KEY`; o código aberto não elimina essas
dependências de execução. O projeto declara limites em frames, shadow roots,
pop-ups e outros controles; o estado DONE exige verificação independente.
É candidato para a escolha de ações, sujeito a um teste local de qualidade,
custo e compatibilidade com o runtime do projeto, não dependência já instalada.

O [Donut Browser](https://github.com/zhom/donutbrowser) tem licença AGPL-3.0 e
gerencia perfis isolados. Sua documentação apresenta REST local e conexão CDP,
mas anuncia automação e MCP em planos pagos. A interface local deve ser conferida
na versão efetivamente usada. [Quickstart oficial](https://donutbrowser.com/docs/quickstart/).

Perfis separados servem para comparar cookies e estado de sessão. Viewports
servem para comparar layout por tamanho; são variáveis diferentes. Para o
primeiro teste de responsividade, avaliar um navegador automatizado local com
contextos limpos antes de exigir multilogin. A escolha do controlador deve
preservar o mesmo formato de evidências e permitir reprodução da jornada.

## Aceite de T04N

- Fixture local com conteúdo inserido por JavaScript é lida corretamente.
- Uma jornada de busca/filtro/detalhe é observada e verificada, com ações e
  evidências recuperáveis; erro e estado incompleto não viram sucesso.
- A mesma jornada roda em desktop/mobile, com dimensões e diferenças registradas.
- Nenhuma sessão pessoal é reutilizada; isolamento entre rodadas é demonstrado.
- Testes determinísticos da decisão/registro ficam separados do teste com browser.
- Teste real do controlador escolhido registra versão, dependências, chamadas
  externas e limites. Jev/Donut não são declarados integrados antes desse teste.

Consulta das fontes: 13/10/2026. Capacidade anunciada não é validação local.

Signed-by: ai-codex (GPT-6 Astra Ultra)
