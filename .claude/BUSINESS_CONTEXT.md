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