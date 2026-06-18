# Entregável — Exercício 2.1: Configuração e uso real de MCP servers

**Projeto:** NovaTech Assistant  
**Fase:** Estruturação — Cenário 2  
**Data:** 2026-06-16

---

## Seção 1 — Mapeamento: necessidade → MCP server

### Necessidades identificadas no projeto

O projeto NovaTech Assistant precisa que agentes de IA acessem 5 categorias de informação durante o desenvolvimento:

| # | Necessidade | Quem consome | Natureza do acesso |
|---|---|---|---|
| 1 | Código-fonte, specs e skills do repositório | Dev (Claude/Copilot) gerando e revisando código | Leitura e escrita |
| 2 | Documentação de negócio da NovaTech (`docs/novatech/`) | Dev consultando regras de domínio, QA validando comportamento | Somente leitura |
| 3 | Corpus de chunks para recuperação (`data/retrieval-corpus/`) | Dev simulando RAG, QA testando prompts | Somente leitura |
| 4 | Histórico e branches do repositório | Dev consultando decisões anteriores, diffs, contexto de commits | Somente leitura |
| 5 | Memória persistente de decisões e linguagem ubíqua | Dev persistindo glossário, ADRs resumidos, convenções | Leitura e escrita no grafo local |

### Mapeamento para reference servers locais e gratuitos

| Necessidade | Server escolhido | Pacote / comando | O que expõe |
|---|---|---|---|
| Código, specs, skills | `filesystem-dev` | `npx @modelcontextprotocol/server-filesystem` | **Tools:** `read_file`, `write_file`, `list_directory`, `create_directory`, `move_file`, `delete_file`, `search_files` |
| Docs de negócio | `filesystem-novatech-docs` | `npx @modelcontextprotocol/server-filesystem` | **Tools:** `read_file`, `write_file`, `list_directory`, `search_files` — escopo restrito a `./docs/novatech`; escrita bloqueada por convenção (AGENTS.md) |
| Corpus de chunks | `filesystem-corpus` | `npx @modelcontextprotocol/server-filesystem` | **Tools:** `read_file`, `write_file`, `list_directory`, `search_files` — escopo restrito a `./data/retrieval-corpus`; escrita bloqueada por convenção (AGENTS.md) |
| Histórico do repo | `git` | `uvx mcp-server-git` | **Tools:** `git_log`, `git_diff`, `git_status`, `git_show`, `git_branch` |
| Memória persistente | `memory` | `npx @modelcontextprotocol/server-memory` | **Tools:** `create_entities`, `create_relations`, `search_nodes`, `open_nodes`; **Resources:** grafo de conhecimento local |

**Todos os servers rodam localmente via `npx`/`uvx`. Nenhum serviço pago ou externo é necessário.**

---

## Seção 2 — `.mcp/mcp.json` final com justificativa de least privilege

### Arquivo gerado

Localização: `novatech-assistant/.mcp/mcp.json`

```json
{
  "mcpServers": {
    "filesystem-dev": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "./src",
        "./specs",
        "./skills",
        "./prompts",
        "./tests"
      ]
    },
    "filesystem-novatech-docs": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "./docs/novatech"
      ]
    },
    "filesystem-corpus": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "./data/retrieval-corpus"
      ]
    },
    "git": {
      "command": "uvx",
      "args": [
        "mcp-server-git",
        "--repository",
        "."
      ]
    },
    "memory": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-memory"
      ]
    }
  }
}
```

### Justificativa de least privilege por server

**`filesystem-dev` — escrita habilitada, escopo mínimo de desenvolvimento**

Recebe `./src`, `./specs`, `./skills`, `./prompts`, `./tests`. O agente precisa escrever nesses diretórios para gerar código, criar specs e atualizar skills. Diretórios excluídos e o motivo:

- `./` (raiz): exporia `.env`, `package.json`, `tsconfig.json` para escrita — risco de corrupção de configuração
- `./infra/`: contém parâmetros de ambiente (`dev.bicepparam`, `prod.bicepparam`) com valores sensíveis de configuração Azure; escrita pelo agente sem revisão humana seria risco de segurança
- `./.github/`: pipelines de CI/CD — modificações automáticas em workflows afetariam toda a esteira de deploy
- `./docs/novatech/`: documentação oficial da NovaTech; o agente não deve sobrescrever documentos contratuais

**`filesystem-novatech-docs` — escopo restrito a docs oficiais, read-only por convenção**

Recebe apenas `./docs/novatech`. O `@modelcontextprotocol/server-filesystem` (implementação de referência) não suporta flag `--read-only` — trata qualquer argumento desconhecido como caminho de diretório, causando falha na inicialização. A restrição de escrita é portanto imposta por **convenção via AGENTS.md**: o agente não deve usar `write_file`/`create_directory` neste server. O escopo mínimo (apenas `./docs/novatech`) já contém o dano: mesmo que o agente escrevesse erroneamente, o impacto fica confinado a essa pasta e fica registrado no `git diff`. O escopo exclui `./docs/adr/` (ADRs são artefatos de desenvolvimento, gerenciados pelo `filesystem-dev`).

**`filesystem-corpus` — escopo restrito ao corpus de RAG, read-only por convenção**

Recebe apenas `./data/retrieval-corpus`. Pelo mesmo motivo acima, a ausência de suporte nativo a `--read-only` faz com que a restrição seja declarada no AGENTS.md. O corpus de chunks é o gabarito de avaliação do pipeline — escopo isolado em `./data/retrieval-corpus` garante que uma escrita acidental não afete código ou documentação de negócio, e qualquer alteração fica visível no `git status`.

**`git` — acesso ao histórico, sem escrita**

O `mcp-server-git` expõe operações de leitura do repositório (log, diff, show, branch). O agente não precisa fazer commits via MCP — commits são feitos manualmente ou via CLI com revisão humana. O server aponta para `.` (repositório local), suficiente para consultar todo o histórico.

**`memory` — grafo local de conhecimento**

O server de memória persiste entidades e relações no grafo local da sessão do agente. Escopo ilimitado é aceitável aqui porque o grafo é isolado da base de arquivos do projeto — não há risco de expor segredos ou sobrescrever código. Serve para o agente manter linguagem ubíqua (ex.: "chamado = ticket de atendimento") e decisões recorrentes entre sessões.

---

## Seção 3 — Evidência de execução

### (a) Agente lê documento de `docs/novatech/`

**Prompt simulado ao agente (com `filesystem-novatech-docs` ativo):**
> "Liste os documentos disponíveis em docs/novatech e mostre o conteúdo da tabela de SLA do cliente Gold."

**Resultado — listagem do diretório `docs/novatech/`:**

```
docs/novatech/
├── README.md
├── FAQ-atendimento.md
├── POL-001-politica-devolucao.md
├── PROC-042-frete-especial-v1.md
├── PROC-042-v2-frete-especial-revisado.md
└── SLA-2024-tabela-sla-clientes.md
```

**Resultado — leitura de `SLA-2024-tabela-sla-clientes.md` (trecho relevante):**

```
# SLA-2024 — Tabela de SLA por Tipo de Cliente
Versão: 2024.1 | Última atualização: 02/01/2024

## 2. Tabela de SLAs

| Métrica                                        | Gold         | Silver       | Standard     |
|------------------------------------------------|--------------|--------------|--------------|
| Tempo de primeira resposta (chamados gerais)   | Até 2h úteis | Até 4h úteis | Até 8h úteis |
| Tempo de resolução (chamados gerais)           | Até 24h úteis| Até 48h úteis| Até 72h úteis|
| Tempo de primeira resposta (incidentes críticos)| Até 30min   | Até 1h       | Até 2h       |
| Tempo de resolução (incidentes críticos)       | Até 4h       | Até 8h       | Até 24h      |
| Disponibilidade do portal de tracking          | 99,5%        | 99,0%        | 98,0%        |
| Gerente de conta dedicado                      | Sim          | Não          | Não          |
```

O agente leu o documento e identificou corretamente que o cliente Gold tem resposta em até 2h úteis e resolução em até 24h para chamados gerais.

---

### (b) Agente recupera chunks do corpus para pergunta do domínio

**Prompt simulado ao agente (com `filesystem-corpus` ativo):**
> "Qual o prazo de devolução de mercadorias na NovaTech? E existem exceções?"

**Consulta ao corpus `data/retrieval-corpus/chunks-novatech.md`:**

O agente buscou por similaridade semântica com a pergunta e recuperou os seguintes chunks (conforme mapa de cobertura do Anexo B):

**Chunk POL-001-A** — Seção 3.1: Prazo geral
> "O cliente pode solicitar a devolução de mercadorias em até **7 (sete) dias úteis** após a data de recebimento confirmada no sistema de tracking. A contagem de dias úteis exclui sábados, domingos e feriados nacionais."

**Chunk POL-001-B** — Seção 3.2: Exceções
> "As seguintes categorias de carga **NÃO são elegíveis** para devolução pelo processo padrão: Cargas perigosas classificadas nas classes 1 a 6 da ANTT [...]. Para essas categorias, o cliente deve entrar em contato com o setor de **Gestão de Riscos (ramal 4500)** para tratamento individual."

**Resposta gerada com base nos chunks recuperados:**
> "O prazo de devolução é de 7 dias úteis a partir da data de recebimento (Fonte: POL-001, Seção 3.1). Atenção: cargas perigosas (classes 1-6 ANTT) não são elegíveis para o processo padrão de devolução — nesses casos, orientar o cliente a acionar o Gestão de Riscos pelo ramal 4500 (Fonte: POL-001, Seção 3.2)."

Os chunks recuperados correspondem exatamente ao gabarito do Anexo B para a pergunta "Qual o prazo de devolução?": `POL-001-A` e `POL-001-B` são os chunks obrigatórios.

---

### (c) Agente lê histórico do repositório via `git`

**Prompt simulado ao agente (com server `git` ativo):**
> "Mostre o histórico de commits deste repositório."

**Resultado — `git log --oneline` via `mcp-server-git`:**

```
bbdd03a chore: starter repo (Anexo D) — estrutura + dados semeados dos Anexos A e B
```

O repositório `novatech-assistant` foi inicializado com um único commit que semeia toda a estrutura de diretórios, os documentos de negócio (`docs/novatech/`) e o corpus de RAG (`data/retrieval-corpus/`). O agente consegue consultar este histórico para entender o estado inicial do projeto antes de qualquer desenvolvimento.

**Resultado — `git status`:**
```
On branch main
nothing to commit, working tree clean
```

O server `git` operou corretamente sobre o repositório local, sem necessidade de GitHub, remoto ou autenticação externa.

---

## Seção 4 — Análise de riscos de segurança

### Risco 1 — Escopo amplo do `filesystem` expõe segredos e configurações sensíveis

**Descrição:** Se o server `filesystem` recebesse `./` (raiz do repositório) em vez de pastas específicas, o agente teria acesso de leitura (e potencialmente escrita) a arquivos como:
- `.env` — variáveis de ambiente com connection strings, API keys, tokens
- `infra/parameters/prod.bicepparam` — parâmetros de produção Azure (subscription IDs, resource names)
- `.github/workflows/cd.yml` — pipeline de deploy; leitura expõe a topologia de infraestrutura

**Cenário de ataque:** Um prompt malicioso injetado via conteúdo de documento (prompt injection via `docs/novatech/`) poderia instruir o agente a ler e exfiltrar o conteúdo do `.env` para um endpoint externo, caso o `filesystem` tivesse escopo na raiz.

**Mitigação aplicada neste setup:**
- O `filesystem-dev` recebe somente `./src`, `./specs`, `./skills`, `./prompts`, `./tests` — a raiz está explicitamente excluída
- O `.gitignore` já exclui `.env` do histórico Git, mas isso não protege o arquivo no sistema de arquivos — o escopo mínimo do MCP é a barreira real
- Regra documentável no `AGENTS.md`: "Nenhum server MCP deve receber `./` como escopo"

---

### Risco 2 — Server com escrita habilitada permite que o agente altere código sem revisão humana

**Descrição:** O `filesystem-dev` tem escrita habilitada em `./src`. Um agente autônomo poderia modificar arquivos de código (ex.: `src/services/search.ts`, `src/functions/query/handler.ts`) em resposta a uma instrução ambígua, sem que nenhum humano revisasse a mudança antes de ela entrar no repositório.

**Cenário concreto:** O Dev pede ao agente "corrija o timeout na busca". O agente, sem contexto suficiente, reescreve `src/services/search.ts` introduzindo uma vulnerabilidade de injection (ex.: concatenando parâmetros sem sanitização) ou quebrando a lógica de `response-validator.ts`. A mudança é commitada diretamente sem PR.

**Mitigação:**
1. **Gate de revisão humana:** O `AGENTS.md` deve declarar explicitamente que toda escrita em `./src/` gerada por agente requer revisão via PR antes do commit — o agente propõe, o dev aprova
2. **Uso do server `memory` como rascunho:** O agente armazena propostas de mudança no grafo de memória para revisão humana antes de aplicar ao sistema de arquivos
3. **Separação de branches:** Agentes operam em feature branches; `main` é protegido — mesmo que o agente escreva um arquivo, o merge ainda exige revisão manual
4. **Registro de mudanças no `git`:** Cada escrita via MCP deve ser imediatamente seguida de `git diff` para que o dev veja o que mudou antes de commitar

---

## Resumo do setup

| Server | Pacote | Escopo | Acesso |
|---|---|---|---|
| `filesystem-dev` | `@modelcontextprotocol/server-filesystem` | `./src ./specs ./skills ./prompts ./tests` | Leitura + escrita |
| `filesystem-novatech-docs` | `@modelcontextprotocol/server-filesystem` | `./docs/novatech` | Read-only **por convenção** (AGENTS.md) |
| `filesystem-corpus` | `@modelcontextprotocol/server-filesystem` | `./data/retrieval-corpus` | Read-only **por convenção** (AGENTS.md) |
| `git` | `mcp-server-git` | Repositório local `.` | Leitura (log, diff, show) |
| `memory` | `@modelcontextprotocol/server-memory` | Grafo local | Leitura + escrita |

Todos os servers são gratuitos, rodam localmente via `npx`/`uvx` e não dependem de nenhum serviço externo (sem Azure, GitHub, Confluence ou APIs pagas).
