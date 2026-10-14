# Navegação e jornadas de concorrentes

## Objetivo e estado

Depois de descobrir URLs, visitar páginas relevantes, extrair conteúdo e observar
fluxos públicos em diferentes tamanhos de tela. Essa capacidade amplia a coleta
SEO para comparar a experiência oferecida pelos concorrentes.

Estado: T04N implementada e verificada localmente na branch `codex-ai`; ainda
aguarda PR e revisão cruzada para integrar em `dev-ai`.
Playwright e Chromium são dependências opcionais declaradas em
[requirements-browser.txt](../requirements-browser.txt).

## Processo implementado em `crawl`

1. Selecionar URLs a partir da busca e links visíveis observados, registrando
   consulta, origem e motivo. Aplicar limites de páginas por domínio e por execução.
2. Ler HTML e sinais de SEO. Para conteúdo dinâmico, abrir a URL em um contexto
   Chromium separado, sem o perfil/cookies de quem executa a ferramenta.
3. Registrar controles visíveis. Para links descobertos na origem, clicar o
   elemento, verificar a URL destino e guardar o screenshot do resultado.
4. Repetir a mesma tarefa com viewport desktop e mobile. Registrar dimensões,
   navegador, idioma e estado de sessão; mudar uma condição por comparação.
5. Consolidar conteúdo, arquitetura de informação, caminhos de navegação,
   diferenças por tela, falhas e oportunidades justificadas por evidências.

O processo limita consultas e páginas, verifica robots.txt antes de cada página
e para quando não consegue confirmar o resultado. Páginas são dados externos,
não instruções que podem mudar a tarefa ou autorizar ações. Na exploração
pública inicial, não concluir compras, cadastros ou envio de mensagens.
O Chromium é restringido à origem e ao IP público validados. Requests externos,
WebSockets e POST são bloqueados e registrados. Assets de CDN podem não carregar
e gerar uma renderização incompleta.

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
Não foi integrado nesta entrega. Pode ser avaliado contra o controle por links
que já existe e o modelo local disponível em uma etapa posterior.

O [Donut Browser](https://github.com/zhom/donutbrowser) tem licença AGPL-3.0 e
gerencia perfis isolados. Sua documentação apresenta REST local e conexão CDP,
mas anuncia automação e MCP em planos pagos. A interface local deve ser conferida
na versão efetivamente usada. [Quickstart oficial](https://donutbrowser.com/docs/quickstart/).

Perfis separados servem para comparar cookies e estado de sessão. Viewports
servem para comparar layout por tamanho; são variáveis diferentes. O crawler usa
contextos limpos em 1365×900 e 390×844, registra screenshots e compara texto,
headings, links e controles. Não calcula diferença visual entre pixels.

## Aceite de T04N

- Fixture local com conteúdo inserido por JavaScript é lida corretamente.
- Um link interno é clicado e a URL final verificada; links ausentes e erro não
  viram jornadas concluídas.
- A mesma jornada roda em desktop/mobile, com dimensões e diferenças registradas.
- Contextos sem dados da sessão pessoal; POST, WebSockets e requests externos
  bloqueados durante a renderização.
- Testes determinísticos da decisão/registro ficam separados do teste com browser.
- Teste real do controlador escolhido registra versão, dependências, chamadas
  externas e limites. Jev/Donut não são declarados integrados antes desse teste.

Consulta das fontes: 13/10/2026. Jev e Donut são referências avaliadas; Chromium
é o navegador validado localmente. O resultado contém jornadas públicas
reproduzidas, não históricos reais ou analytics de visitantes.

Signed-by: ai-codex (GPT-6 Astra Ultra)
