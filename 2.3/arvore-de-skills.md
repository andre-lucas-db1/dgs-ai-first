# Árvore de Skills — Projeto NovaTech Assistant

> Hierarquia: Foundation → Domain → Artifact  
> Cada skill é um arquivo `.md` independente em `/skills/`.

---

## Visão geral da hierarquia

```
skills/
├── foundation/                         ← Lidas por TODAS as outras skills e por todo agente antes de gerar código
│   ├── typescript-conventions.md       ← BASE ZERO — governa todo artefato TypeScript do projeto
│   ├── error-handling.md               ← Padrão de erros customizados e propagação
│   └── project-structure.md            ← Onde cada tipo de artefato vive no repositório
│
├── domain/                             ← Lidas ao gerar artefatos de uma camada técnica específica
│   ├── azure-functions-endpoint.md     ← Estrutura padrão de um HTTP trigger no projeto
│   ├── azure-ai-search-integration.md  ← Como chamar o Azure AI Search (index, query, scoring)
│   ├── react-components.md             ← Convenções de componentes React do painel web
│   └── testing-patterns.md             ← Como escrever testes (unit, integration, e2e) no projeto
│
└── artifact/                           ← Receitas de geração — input do agente → artefato completo
    ├── create-rag-endpoint.md          ← Checklist para criar endpoint RAG do zero
    ├── create-integration-test.md      ← Checklist para criar teste de integração de endpoint
    └── create-react-card.md            ← Checklist para criar card React de resposta/feedback
```

---

## Descrição de cada skill

### Foundation

| Arquivo | Nome | Frase-ativação |
|---|---|---|
| `typescript-conventions.md` | **TypeScript Conventions** | *"gere código TypeScript para este projeto"* / qualquer geração de arquivo `.ts` |
| `error-handling.md` | **Error Handling** | *"adicione tratamento de erro"* / *"crie um handler"* / *"o que fazer se a chamada falhar"* |
| `project-structure.md` | **Project Structure** | *"onde devo criar este arquivo?"* / *"qual pasta para..."* / onboarding de novo membro |

### Domain

| Arquivo | Nome | Frase-ativação |
|---|---|---|
| `azure-functions-endpoint.md` | **Azure Functions Endpoint** | *"crie um endpoint"* / *"novo Azure Function"* / *"HTTP trigger"* |
| `azure-ai-search-integration.md` | **Azure AI Search Integration** | *"integre com o search"* / *"busca semântica"* / *"recuperar chunks"* |
| `react-components.md` | **React Components** | *"crie um componente"* / *"card de resposta"* / *"formulário de feedback"* |
| `testing-patterns.md` | **Testing Patterns** | *"escreva testes para"* / *"adicione cobertura"* / *"mock do Azure Search"* |

### Artifact

| Arquivo | Nome | Frase-ativação |
|---|---|---|
| `create-rag-endpoint.md` | **Create RAG Endpoint** | *"crie o endpoint RAG para [funcionalidade]"* |
| `create-integration-test.md` | **Create Integration Test** | *"crie testes de integração para [endpoint/serviço]"* |
| `create-react-card.md` | **Create React Card** | *"crie um card de [tipo] para o painel web"* |

---

## Dependências entre skills

```
artifact/create-rag-endpoint
    └── domain/azure-functions-endpoint
    │       └── foundation/typescript-conventions  ← RAIZ
    │       └── foundation/error-handling
    └── domain/azure-ai-search-integration
    │       └── foundation/typescript-conventions
    └── foundation/project-structure

artifact/create-integration-test
    └── domain/testing-patterns
            └── foundation/typescript-conventions

artifact/create-react-card
    └── domain/react-components
            └── foundation/typescript-conventions
```

**Regra de carregamento:** Agentes devem ler Foundation antes de Domain, Domain antes de Artifact. `typescript-conventions.md` é pré-condição de todas as outras.

---

## Skills ausentes (identificadas, fora do escopo v1)

| Skill ausente | Justificativa para inclusão futura |
|---|---|
| `domain/ingestion-pipeline.md` | O pipeline de ingestão (`extractor.ts`, `chunker.ts`, `embedder.ts`, `indexer.ts`) tem padrões próprios de chunking e não tem cobertura de skill |
| `foundation/logging.md` | A convenção de uso do logger pino (structured fields, levels) merece skill própria quando `logger.ts` for implementado |
