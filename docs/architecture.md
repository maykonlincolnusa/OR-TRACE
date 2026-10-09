# Decisões de engenharia

## ADR 001 — Domínio independente

Dataclasses e Decimal definem fatos financeiros imutáveis. Protocols definem portas;
FastAPI, Pydantic e armazenamento ficam nas bordas. Serviços recebem Ledger por injeção.
A moeda segue um código de três letras; cadastro ISO 4217 e escala específica de cada
moeda são validações futuras. O contrato atual suporta até oito casas decimais.

## ADR 002 — Ledger e outbox atômicos

Persistir transações e eventos na mesma unidade de trabalho evita perder notificações.
O adaptador de memória usa lock e cópia antes do commit. O contrato PostgreSQL deve usar
BEGIN/COMMIT e restrições únicas, comparando conteúdo em retries: ON CONFLICT DO NOTHING
isoladamente esconderia divergências. Há chave de negócio (source_system, external_id)
e chave interna id. Reprocessamento idêntico não cria outro evento.

O dispatcher entrega pelo menos uma vez. Falha depois do ack e antes da marcação pode
duplicar mensagens. Consumidores implementam inbox atômica com a atualização da projeção,
retentativas com backoff, dead letter e replay. O exemplo não inicia workers nem broker.

## ADR 003 — Grafo como projeção reconstruível

Nós Entity e Account; aresta OWNS de Entity para Account; arestas TRANSFER de Account
para Account, identificadas por transaction_id, com amount, currency e occurred_at.
O consumidor de transaction.ingested realiza upsert idempotente. Em tecnologias que
não suportam arestas paralelas identificáveis, Transaction vira nó intermediário.
Cadastros são carregados pelo ledger/snapshot; seus eventos de mudança serão uma extensão
versionada. GraphProjection é uma porta preparada, ainda não usada pelo motor de consulta.
Monitorar lag e watermark da projeção; leitura investigativa deve indicar corte consistente.
Nesta versão, snapshot do ledger em memória é a única fonte de consulta.

## ADR 004 — Sem inferência falsa de propriedade

O algoritmo DFS percorre caminhos temporalmente válidos, em uma única moeda, com
timestamps estritamente crescentes. Backward inverte a navegação, mas devolve a linhagem
em ordem cronológica. Empates temporais não estabelecem causalidade e não são conectados.
Para no primeiro retorno a uma conta. Uma entrada inicia apenas a partir da conta consultada;
não pressupõe saldo inicial nem procura instituições fora da base.

O mínimo dos valores das arestas é somente um teto por caminho. Não existe alocação
conservativa entre caminhos sobrepostos, FIFO, LIFO, proportional taint ou conversão FX.
Saldos anteriores, receitas externas e mistura de fundos exigem política explícita de
atribuição, reconciliação de saldos e rastreio da parcela atribuída antes de qualquer
afirmação de origem econômica. Contas com pass-through são candidatas baseadas em pares,
não classificação definitiva baseada no balanço completo.

## ADR 005 — Limites e desempenho

Consultas aceitam 1–10 hops e 1–1000 caminhos. Há teto interno de 10.000 expansões.
truncated é conservador: alcançar um teto já pode sinalizar incompletude. Não oferece
paginação nem ranking dos caminhos mais arriscados. Ordenação determinística por tempo/id.
O snapshot e a indexação inicial custam O(T); enumeração pode crescer exponencialmente
até os limites. Fan-in/out consideram todo o intervalo e moeda da consulta, inclusive
arestas fora do caminho. Não interpretar essas evidências como causalidade temporal.
Antes de produção: consulta indexada por janela, jobs assíncronos, quotas, timeout,
cancelamento e orçamento de memória, sem truncamento silencioso.

## ADR 006 — Risco explicável

Score heurístico versionado (1.0), soma de pesos distintos limitada a 100. Não é probabilidade,
modelo calibrado, classificação regulatória ou decisão automática. Uma regra contribui
uma vez ao score e pode produzir múltiplas evidências. Pesos/limiares estão no serviço
e sua alteração exige versão e validação de regressão. Configuração externa, aprovação
de regras, datasets rotulados e análise de falsos positivos fazem parte do roadmap.
