# Mapeamento de Criação e Consumo de Skills

> Para cada skill: quem cria, quem consome (papéis humanos), quais agentes consomem, e frequência de uso estimada ao longo do projeto.

---

## Tabela completa

| Skill | Papel que cria | Papéis que consomem | Agentes que consomem | Frequência |
|---|---|---|---|---|
| `foundation/typescript-conventions` | Tech Lead | Dev Pleno, Dev Sênior, QA | Copilot, Claude Code | **Toda geração de `.ts`** — base implícita de tudo |
| `foundation/error-handling` | Tech Lead | Dev Pleno, Dev Sênior | Copilot, Claude Code | Toda função que chama Azure Search ou OpenAI |
| `foundation/project-structure` | Tech Lead | Dev Pleno, Dev Sênior, Product Specialist, Delivery Manager | Copilot, Claude Code | Onboarding + criação de qualquer artefato novo |
| `domain/azure-functions-endpoint` | Dev Sênior | Dev Pleno, Dev Sênior | Copilot | A cada novo endpoint (~5 no projeto: query, feedback, health + expansões) |
| `domain/azure-ai-search-integration` | Dev Sênior | Dev Pleno, Dev Sênior | Copilot | Módulos `query/` e `pipeline/` |
| `domain/react-components` | Dev Pleno | Dev Pleno | Copilot | Painel web: cards de resposta, formulários de feedback |
| `domain/testing-patterns` | QA + Dev Sênior | Dev Pleno, Dev Sênior, QA | Copilot, Claude Code | Todo PR que adiciona ou modifica lógica |
| `artifact/create-rag-endpoint` | Dev Sênior (aprovado pelo TL) | Dev Pleno, Dev Sênior | Copilot | ~5x no projeto (1 por endpoint RAG) |
| `artifact/create-integration-test` | QA | Dev Pleno, Dev Sênior, QA | Copilot | 1 por endpoint criado (~5x) |
| `artifact/create-react-card` | Dev Pleno | Dev Pleno | Copilot | Painel web + Teams cards (~3-4x) |

---

## Visão por papel de time

### Tech Lead
- **Cria:** todas as `foundation/` (3 skills)
- **Consome:** revisa todas; usa `project-structure` para orientar o time
- **Responsabilidade:** manter skills Foundation atualizadas conforme o projeto evolui

### Dev Sênior
- **Cria:** `domain/azure-functions-endpoint`, `domain/azure-ai-search-integration`, `domain/testing-patterns` (co-autor com QA), `artifact/create-rag-endpoint`
- **Consome:** todas as `foundation/` + skills de domínio que co-cria
- **Responsabilidade:** garantir que as skills de domínio reflitam o que foi implementado, não o que foi planejado

### Dev Pleno
- **Cria:** `domain/react-components`, `artifact/create-react-card`
- **Consome:** `foundation/*` + `domain/azure-functions-endpoint` + `artifact/create-rag-endpoint` + `artifact/create-integration-test`
- **Responsabilidade:** principal consumidor — geração diária de código com Copilot

### QA
- **Cria:** `artifact/create-integration-test` (autoria principal), co-autor de `domain/testing-patterns`
- **Consome:** `domain/testing-patterns`, `foundation/typescript-conventions`
- **Responsabilidade:** garantir que os artefatos de teste gerados pelo Copilot cubram os cenários de falha mapeados

### Product Specialist
- **Cria:** nenhuma skill técnica
- **Consome:** `foundation/project-structure` (para saber onde ficam specs e como está organizado o repositório)
- **Nota:** consome skills indiretamente via documentação — entende a estrutura sem precisar gerar código

### Delivery Manager
- **Cria:** nenhuma skill técnica
- **Consome:** `foundation/project-structure` (onboarding, visibilidade do progresso)
- **Nota:** mesma skill que o Product Specialist usa, serve como mapa do repositório

---

## Visão por agente de IA

### GitHub Copilot (inline + Chat)
- Consome: todas as skills
- Ponto de entrada preferencial: `foundation/typescript-conventions` → skill de domínio relevante → skill de artefato
- Contexto de ativação: developer abre um arquivo `.ts` e pede geração inline, ou usa Copilot Chat com frase-ativação

### Claude Code
- Consome: `foundation/*` + `domain/testing-patterns` + skills de artefato ao executar tarefas de scaffolding
- Ponto de entrada preferencial: carrega Foundation antes de qualquer geração de arquivo
- Contexto de ativação: tarefas maiores de criação de módulo, refactoring orientado a convenção, geração de testes em lote

---

## Notas de manutenção

| Situação | Ação |
|---|---|
| Mudança no tsconfig (ex: adicionar `paths`) | Tech Lead atualiza `typescript-conventions.md` + PR de revisão |
| Novo padrão de endpoint aprovado pelo time | Dev Sênior atualiza `azure-functions-endpoint.md` + `create-rag-endpoint.md` |
| QA identifica padrão de teste não coberto | QA abre PR para `testing-patterns.md` + `create-integration-test.md` |
| Nova camada no projeto (ex: WebSocket) | Tech Lead cria nova skill `domain/` antes do primeiro PR da camada |
