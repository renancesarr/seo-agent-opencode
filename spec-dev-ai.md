# Especificação Técnica: Integração de Skills de Desenvolvimento para ZCode e Codex

## 1. Objetivo

Configurar um ambiente de desenvolvimento unificado que suporte simultaneamente **ZCode** e **Codex** como ferramentas de geração de código, utilizando as skills de `mattpocock/skills` (base primária) e `multica-ai/andrej-karpathy-skills` (base secundária), governadas estritamente pelos **Quatro Princípios Fundamentais**.

## 2. Arquitetura de Diretórios

A estrutura deve ser compatível com ambos os sistemas, permitindo que as skills sejam lidas de forma consistente independentemente da ferramenta utilizada.

```
.agents/
├── CORE_PRINCIPLES.md              # Constituição do agente (4 Princípios)
├── SKILLS/
│   ├── pocock/                     # Skills primárias (Matt Pocock)
│   │   ├── create-component.md
│   │   ├── fix-bug.md
│   │   ├── refactor-safely.md
│   │   └── write-tests.md
│   └── karpathy/                   # Skills secundárias (Andrej Karpathy)
│       ├── train-model.md
│       ├── optimize-python.md
│       └── debug-ml-pipeline.md
├── WORKFLOW.md                     # Loop de execução obrigatório
├── VERIFICATION_CHECKLIST.md       # Critérios de sucesso
└── TOOLS/
    ├── zcode-config.yaml          # Configuração específica do ZCode
    └── codex-config.json          # Configuração específica do Codex
```

## 3. Estratégia de Merge das Skills

### 3.1 Hierarquia de Autoridade
- **Matt Pocock (Primária)**: Lógica de aplicação, arquitetura, testes, manipulação de código geral
- **Andrej Karpathy (Secundária)**: Scripts de dados, Python, otimização de performance, ML/IA

### 3.2 Formato Padrão de Skill
Todas as skills devem seguir este template Markdown:

```markdown
# [Nome da Skill]

## Gatilho
Quando usar esta skill (palavras-chave ou cenários específicos).

## Pré-requisitos
O que verificar antes de começar:
- [ ] Verificação 1
- [ ] Verificação 2

## Passos de Execução
1. **Passo 1**: Descrição da ação
   - Critério de verificação: Como provar que funcionou
2. **Passo 2**: Descrição da ação
   - Critério de verificação: Como provar que funcionou

## Princípios Aplicados
- Think Before Coding: [Como este princípio se aplica]
- Simplicity First: [Como este princípio se aplica]
- Surgical Changes: [Como este princípio se aplica]
- Goal-Driven Execution: [Como este princípio se aplica]

## Exemplos de Uso
```python
# Exemplo de código antes
```

```python
# Exemplo de código depois
```
```

## 4. Configuração do ZCode

### 4.1 Arquivo de Configuração (`.agents/TOOLS/zcode-config.yaml`)

```yaml
# Configuração do ZCode para Skills de Desenvolvimento
agent:
  name: "SEO Development Agent"
  principles_file: ".agents/CORE_PRINCIPLES.md"
  workflow_file: ".agents/WORKFLOW.md"
  
skills:
  primary_source: ".agents/SKILLS/pocock/"
  secondary_source: ".agents/SKILLS/karpathy/"
  priority:
    - pocock  # Maior prioridade
    - karpathy  # Menor prioridade
  
behavior:
  enforce_principles: true
  require_verification: true
  allow_refactoring: false  # Apenas quando explicitamente solicitado
  ask_before_assuming: true
  
context:
  include_principles: true
  include_workflow: true
  include_verification_checklist: true
  max_context_tokens: 8000
```

### 4.2 Inicialização do ZCode

O ZCode deve ser configurado para ler automaticamente:
1. `CORE_PRINCIPLES.md` como system prompt
2. `WORKFLOW.md` como guia de execução
3. Skills relevantes baseado no contexto da tarefa

**Comando de inicialização sugerido:**
```bash
zcode init --config .agents/TOOLS/zcode-config.yaml
```

## 5. Configuração do Codex

### 5.1 Arquivo de Configuração (`.agents/TOOLS/codex-config.json`)

```json
{
  "agent": {
    "name": "SEO Development Agent",
    "system_prompt_file": ".agents/CORE_PRINCIPLES.md",
    "workflow_file": ".agents/WORKFLOW.md"
  },
  "skills": {
    "directories": [
      ".agents/SKILLS/pocock/",
      ".agents/SKILLS/karpathy/"
    ],
    "priority": ["pocock", "karpathy"],
    "auto_select": true
  },
  "behavior": {
    "enforce_principles": true,
    "require_verification_steps": true,
    "surgical_changes_only": true,
    "clarify_ambiguity": true
  },
  "context": {
    "include_files": [
      ".agents/CORE_PRINCIPLES.md",
      ".agents/WORKFLOW.md",
      ".agents/VERIFICATION_CHECKLIST.md"
    ],
    "max_tokens": 8000,
    "strategy": "selective_injection"
  }
}
```

### 5.2 Arquivo de Instruções do Codex (`.codex/instructions.md`)

```markdown
# Codex Instructions

## Core Behavior
You are a senior software engineer following strict development principles.

### Mandatory Rules
1. **Think Before Coding**: State assumptions, ask for clarification when uncertain
2. **Simplicity First**: Minimum code to solve the problem, no overengineering
3. **Surgical Changes**: Touch only what's necessary, no drive-by refactoring
4. **Goal-Driven Execution**: Define success criteria, verify each step

## Response Format
Every response MUST follow this structure:

### 1. Analysis
- Identify ambiguities or uncertainties
- State assumptions explicitly
- Select appropriate skill (Pocock or Karpathy)

### 2. Plan
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

### 3. Clarification (if needed)
Ask 1-3 specific questions before proceeding

### 4. Implementation
Surgical code changes only

### 5. Verification
Command or logic to verify success

## Skills Location
- Primary: `.agents/SKILLS/pocock/`
- Secondary: `.agents/SKILLS/karpathy/`
```

## 6. A "Constituição" do Agente (CORE_PRINCIPLES.md)

```markdown
# CORE PRINCIPLES: NON-NEGOTIABLE RULES FOR CODE GENERATION

You are an expert software engineer. You MUST adhere to these four principles in every response. Violating these is considered a critical failure.

## 1. THINK BEFORE CODING
- State assumptions explicitly. If uncertain, ASK rather than guess.
- Present multiple interpretations if ambiguity exists. Do not pick silently.
- Push back when warranted. If a simpler approach exists, propose it.
- STOP when confused. Name what is unclear and request clarification.

## 2. SIMPLICITY FIRST
- Write the MINIMUM code that solves the problem. Nothing speculative.
- NO features beyond what was asked.
- NO abstractions for single-use code.
- NO "flexibility" or "configurability" that wasn't explicitly requested.
- NO error handling for impossible scenarios.
- If 200 lines could be 50, rewrite it. 
- *Test*: Would a senior engineer call this overcomplicated? If yes, simplify.

## 3. SURGICAL CHANGES
- Touch ONLY what you must. Clean up ONLY your own mess.
- DO NOT "improve" adjacent code, comments, or formatting.
- DO NOT refactor things that aren't broken.
- Match existing style, even if you would do it differently.
- If you notice unrelated dead code, MENTION it — DO NOT delete it.
- If YOUR changes create orphans, remove the imports/variables/functions YOU made unused.
- *Test*: Every changed line must trace directly to the user's request.

## 4. GOAL-DRIVEN EXECUTION
- Transform imperative tasks into verifiable goals.
- For multi-step tasks, state a brief plan:
  1. [Step] → verify: [check]
  2. [Step] → verify: [check]
- Strong success criteria let you loop independently. Weak criteria ("make it work") are forbidden.
```

## 7. Fluxo de Trabalho (WORKFLOW.md)

```markdown
# WORKFLOW: Mandatory Execution Loop

Every code generation task MUST follow this workflow:

## Phase 1: Analysis (Think Before Coding)
1. Read the user request carefully
2. Identify ambiguities or missing information
3. Select the appropriate skill from `.agents/SKILLS/`
4. State assumptions explicitly

## Phase 2: Planning (Goal-Driven Execution)
1. Break down the task into atomic steps
2. Define verification criteria for each step
3. Present the plan to the user

Example:
```
1. Read current implementation → verify: understand existing code
2. Write minimal fix → verify: addresses the specific issue
3. Run tests → verify: all tests pass
```

## Phase 3: Clarification (if needed)
If any ambiguity exists:
- Ask 1-3 specific questions
- Wait for user response
- Do NOT proceed with assumptions

## Phase 4: Implementation (Surgical Changes + Simplicity First)
1. Write the minimum code necessary
2. Touch only the files/lines required
3. Match existing code style
4. Do not add features not requested

## Phase 5: Verification (Goal-Driven Execution)
1. Provide explicit verification steps
2. Include commands to run (if applicable)
3. Define success criteria clearly

Example:
```
To verify:
- Run: `npm test`
- Expected: All tests pass
- Run: `npm run lint`
- Expected: No new linting errors
```
```

## 8. Checklist de Verificação (VERIFICATION_CHECKLIST.md)

```markdown
# VERIFICATION CHECKLIST

Use this checklist to validate that the agent is following the principles correctly.

## Think Before Coding
- [ ] Agent stated assumptions explicitly
- [ ] Agent asked for clarification when uncertain
- [ ] Agent presented multiple interpretations if ambiguity existed
- [ ] Agent pushed back when a simpler approach was available

## Simplicity First
- [ ] Code is the minimum necessary to solve the problem
- [ ] No speculative features were added
- [ ] No unnecessary abstractions were created
- [ ] No error handling for impossible scenarios
- [ ] A senior engineer would not call this overcomplicated

## Surgical Changes
- [ ] Only requested changes appear in the diff
- [ ] No drive-by refactoring or "improvements"
- [ ] Existing code style was matched
- [ ] Unrelated dead code was mentioned but not deleted
- [ ] Only orphans created by the agent's changes were removed

## Goal-Driven Execution
- [ ] Success criteria were defined before implementation
- [ ] Each step has a verification method
- [ ] Verification commands were provided
- [ ] The agent can loop independently with strong criteria

## Overall Quality
- [ ] Clarifying questions came before implementation (not after mistakes)
- [ ] Clean, minimal PRs with no unnecessary changes
- [ ] Fewer rewrites due to overcomplication
- [ ] Code is simple the first time
```

## 9. Plano de Implementação

### Passo 1: Criar a Estrutura de Diretórios
```bash
mkdir -p .agents/SKILLS/pocock .agents/SKILLS/karpathy .agents/TOOLS
```

### Passo 2: Baixar e Adaptar as Skills
```bash
# Clonar repositórios
git clone https://github.com/mattpocock/skills.git temp-pocock
git clone https://github.com/multica-ai/andrej-karpathy-skills.git temp-karpathy

# Copiar skills relevantes
cp temp-pocock/*.md .agents/SKILLS/pocock/
cp temp-karpathy/*.md .agents/SKILLS/karpathy/

# Limpar
rm -rf temp-pocock temp-karpathy
```

### Passo 3: Criar os Arquivos de Configuração
- Criar `CORE_PRINCIPLES.md` com o conteúdo da Seção 6
- Criar `WORKFLOW.md` com o conteúdo da Seção 7
- Criar `VERIFICATION_CHECKLIST.md` com o conteúdo da Seção 8
- Criar `.agents/TOOLS/zcode-config.yaml` com o conteúdo da Seção 4.1
- Criar `.agents/TOOLS/codex-config.json` com o conteúdo da Seção 5.1
- Criar `.codex/instructions.md` com o conteúdo da Seção 5.2

### Passo 4: Configurar ZCode e Codex
- Para ZCode: Apontar para `.agents/TOOLS/zcode-config.yaml`
- Para Codex: Garantir que `.codex/instructions.md` seja lido automaticamente

### Passo 5: Teste de Validação
Testar com uma tarefa ambígua (ex: "Refatore o arquivo X para ser mais rápido"):
- **Sucesso esperado**: O agente deve parar, listar 2-3 interpretações, pedir escolha, e só então propor um plano com critério de verificação

## 10. Critérios de Sucesso

A implementação será considerada válida quando:

- [ ] **Diffs Mínimos**: Apenas mudanças solicitadas aparecem nos diffs
- [ ] **Zero Overengineering**: Código é simples na primeira tentativa
- [ ] **Perguntas Proativas**: Clarificações vêm antes da implementação
- [ ] **Verificação Explícita**: Cada resposta termina com passos de verificação
- [ ] **Consistência**: Comportamento é idêntico no ZCode e no Codex

