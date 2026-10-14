# Workflow de branches e revisão

Termos canônicos do fluxo de integração entre agentes e promoção humana.

## Linguagem

**Agente autor**:
Agente responsável pelos commits de uma branch de desenvolvimento e pelo conteúdo de um pull request.
_Evitar_: agente que revisa, revisor do próprio código

**Agente revisor**:
Agente autorizado a avaliar o pull request produzido pelo agente autor da direção oposta.
_Evitar_: aprovador automático, autor-revisor

**Branch de integração**:
`dev-ai`, branch que recebe somente pull requests revisados e aprovados.
_Evitar_: branch de produção, branch final

**Branch humana**:
`main`, branch promovida somente por decisão humana.
_Evitar_: branch dos agentes, branch automática

**Head SHA**:
Identificador do commit mais recente do pull request; qualquer novo head exige nova revisão.
_Evitar_: data do push, versão aproximada

**Veredito**:
Review `APPROVED` ou `CHANGES_REQUESTED` associado ao Head SHA atual.
_Evitar_: comentário, reação, review antigo

**Exceção humana**:
Autorização explícita e limitada a um pull request e ação concretos, sem alterar as regras permanentes do workflow.
_Evitar_: bypass permanente, aprovação implícita
