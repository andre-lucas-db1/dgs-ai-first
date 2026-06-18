# Contexto de Negócio — Projeto NovaTech

## Sobre a Empresa

A **NovaTech** é uma empresa de médio porte do setor de **logística**, com 1.200 funcionários. A operação depende fortemente de documentação interna estruturada e atualizada.

## Problema a Resolver

A equipe de atendimento ao cliente (45 pessoas) gasta em média **12 minutos por chamado** buscando informações em fontes dispersas para responder dúvidas sobre prazos, regras de frete, políticas de devolução e procedimentos de reclamação.

Isso resulta em:
- Respostas inconsistentes entre atendentes
- Atrasos no atendimento
- Frustração de clientes e equipe interna

## Fontes de Documentação Atuais

| Fonte | Conteúdo | Volume |
|---|---|---|
| SharePoint corporativo | Manuais de procedimento, políticas de compliance, normas de segurança de carga | ~800 documentos (PDF e Word) |
| Confluence (wiki interna) | Páginas de conhecimento operacional | ~400 páginas |
| Pasta de rede | Planilhas de referência (SLA, tabelas de frete) | Atualização mensal |

## Domínio — Conceitos e Entidades Relevantes

- **SLA**: tabelas de nível de serviço por tipo de cliente, atualizadas mensalmente pela área Comercial
- **Regras de frete**: cálculo de frete conforme tipo de carga, rota e cliente
- **Política de devolução**: procedimentos e prazos aceitos por tipo de produto/ocorrência
- **Procedimento de reclamação**: fluxo formal para abertura e tratamento de reclamações de clientes
- **Compliance**: políticas regulatórias e de segurança de carga mantidas pela área de Compliance
- **Chamado**: unidade de atendimento ao cliente — volume médio de 320/dia, ~60% exigem consulta a documentação

## Restrições e Riscos de Negócio

- A documentação é atualizada mensalmente por **3 áreas distintas** (Operações, Compliance, Comercial) sem processo unificado de revisão
- Existem **documentos com versões contraditórias** — hoje resolvido informalmente ("perguntando para quem sabe")
- Qualquer resposta gerada pelo assistente deve **indicar a fonte** para manter rastreabilidade e confiança

## Solução Contratada

A **DB1** foi contratada para construir um **assistente de IA** que permita aos atendentes fazer perguntas em linguagem natural e receber respostas fundamentadas na documentação oficial, com citação de fonte.

### Integração prevista
- **Microsoft Teams** — interface de uso pelos atendentes
- **SharePoint** — principal fonte de documentos
- **Azure AI Services** — infraestrutura de IA (licenças M365 E3 já disponíveis)

## Métricas de Sucesso

| Métrica | Atual | Meta |
|---|---|---|
| Tempo médio de busca por chamado | 12 minutos | < 2 minutos |

## Restrições de Projeto

- Prazo: **3 meses** (discovery + desenvolvimento + go-live)
- Orçamento definido para o período acima
- Expectativa de resultado validada pela diretoria da NovaTech

## O Cenário (continuação)

O projeto NovaTech foi aprovado. O discovery está concluído e a fase de entendimento produziu artefatos concretos: ADRs com decisões arquiteturais (modelo LLM, estratégia de contexto, tratamento de documentos contraditórios, build vs buy), uma spec de requisitos de produto para o pipeline de RAG, um protótipo funcional de RAG com ferramentas open-source, cenários de falha mapeados pelo QA, e um plano de testes inicial. Agora o time precisa estruturar o ambiente, os padrões e os artefatos que vão governar o desenvolvimento.

### O que foi definido na fase anterior (cenário 1)

- **Modelo LLM:** Azure OpenAI (GPT-4o) — escolhido pela integração com o ecossistema Microsoft da NovaTech e pela janela de 128K tokens (ADR-0001).
- **Pipeline de RAG:** Azure AI Search + Azure OpenAI. O protótipo open-source (ChromaDB + sentence-transformers) validou a abordagem e identificou problemas de chunking em tabelas (ADR-0004).
- **Estratégia de contexto:** Context budget de ~4K tokens para system prompt + ~8K para chunks (5 chunks de ~1.500 tokens) + pergunta + histórico limitado a 3 turnos (ADR-0002).
- **Documentos contraditórios:** Metadado de vigência no pipeline; prompt instrui o modelo a priorizar versão mais recente; documentos obsoletos marcados, não excluídos (ADR-0003).
- **Integração:** Microsoft Teams (bot) + painel web interno.
- **Base documental:** das ~1.250 fontes brutas do cenário 1 (SharePoint, Confluence e planilhas), após deduplicação e limpeza no discovery restaram 847 documentos válidos consolidados (12 deles com contradições pendentes de resolução pelo Compliance da NovaTech); 63 foram descartados por obsolescência e ~340 eliminados como duplicatas ou redundâncias.
- **Arquitetura:** 4 componentes — (1) pipeline de ingestão, (2) API do assistente (Azure Functions + Azure AI Search + Azure OpenAI), (3) interface no Teams via Bot Framework, e (4) painel web interno (dashboard de métricas e histórico).
- **Stack:** TypeScript (backend e bot), React (painel web), Bicep para infraestrutura como código.
- **Repositório:** `novatech-assistant` (o prefixo `db1/` é narrativo). Nesta fase é trabalhado como repositório Git **local** — ver Anexo D (Starter Repo); não há remoto nem GitHub necessários.
- **Time:** 1 Tech Lead, 2 Desenvolvedores (1 pleno, 1 sênior), 1 QA, 1 Product Specialist, 1 Delivery Manager.

### O desafio desta fase

Antes de escrever a primeira linha de código de produção, o time precisa:
1. Definir como agentes de IA (Copilot, Claude Code) serão usados no desenvolvimento — regras, limites, padrões.
2. Recortar o domínio do projeto (bounded contexts, linguagem ubíqua) e especificar o que será construído usando Spec Driven Development.
3. Configurar as conexões que os agentes precisam para operar (MCP servers para acessar repositório, docs, Azure).
4. Criar skills reutilizáveis que encapsulam os padrões do projeto para geração consistente de código e artefatos.

---