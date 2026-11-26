# Decisões da análise

Decisões tomadas **antes de rodar qualquer teste estatístico** (issue #1). O protocolo pré-registrado (`planejamento_survey.pdf`) continua sendo a referência: cada decisão diz se é um desvio dele. Os desvios entram também em `DEVIATIONS.md`.

Status: **Decidida** (escolha do grupo) ou **Proposta** (recomendação a confirmar antes da #7).

---

## 1. Período de coleta

**Status:** Decidida · **Desvio:** sim

- **Análise principal:** respostas enviadas de **13/11/2026 00:00 a 25/11/2026 23:59:59** (America/Sao_Paulo).
- O formulário é fechado em 25/11/2026 às 23:59 e não é reaberto.

**Motivo:** o número de respostas até 22/11 ficou abaixo do esperado, e a coleta foi prorrogada para tentar alcançar a meta.

**Os resultados não foram olhados antes da decisão de prorrogar.** A decisão se baseou apenas na quantidade de respostas.

**Impacto:** o protocolo (Seção 8) previa encerramento em 22/11 "sem prorrogação". Não há análise separada só com o período pré-registrado: todos os resultados usam as respostas até 25/11. O número de respostas recebidas na prorrogação (23/11 a 25/11) é registrado em `DEVIATIONS.md`.

## 2. Reclassificação dos papéis digitados em "Outro" (B2)

**Status:** Decidida · **Desvio:** não (operacionaliza a Seção 1 e a etapa 2 da Seção 5.1)

Cada cargo digitado é classificado olhando **só o texto do cargo**, sem as demais respostas da pessoa:

| Classificação | Critério | Exemplos |
|---|---|---|
| Técnico | Trabalha diretamente com código, testes, infraestrutura ou dados | engenheiro de software, estagiário de desenvolvimento, analista de sistemas que programa, DBA |
| Gestão | Decide prioridade, escopo, prazo ou pessoas | CTO, head de produto, líder de squad que não programa |
| Fora da amostra | Não se encaixa em nenhum dos dois grupos | designer UX/UI, suporte, comercial, RH |
| Fora da amostra (ambíguo) | Não dá para saber o grupo só pelo cargo | "analista de TI" |

Cada decisão fica em `data/manual/reclassificacao_outro.csv`, com justificativa. Esse arquivo não vai para o Git, porque guarda texto digitado pelo respondente (ver item 9).

## 3. Anonimização das respostas abertas (F1, F2)

**Status:** Decidida · **Desvio:** não (Seção 6)

- **Substituir por `[removido]`:** nomes de pessoas, empresas, clientes, produtos e sistemas internos, cidades e unidades, e situações específicas a ponto de identificar a empresa.
- **Manter:** tecnologias genéricas (por exemplo, Java, React, AWS) e termos técnicos.
- **Na dúvida:** remover.
- Os textos originais nunca vão para o Git; só o texto revisado e aprovado vai para `data/processed/`.

## 4. Codificação das respostas abertas

**Status:** Decidida · **Desvio:** não (Seção 5.7)

Feita na #5, depois da limpeza e da anonimização. Dois integrantes codificam separadamente e resolvem as divergências juntos.

## 5. Proteção de recortes pequenos no dashboard

**Status:** Decidida · **Desvio:** não

Não será implementada. O grupo avaliou que os filtros não devem gerar recortes que permitam identificar respondentes.

---

## Propostas a confirmar antes da #7

Pontos que o protocolo não fixa ou que precisam ficar definidos antes de ver os dados. A recomendação vale como padrão, a menos que o grupo decida outra coisa antes de rodar os testes.

### 6. Margem de erro nas questões de pesquisa

**Desvio:** não (aplica a Seção 2).

A especificação da Parte 2 pede margem de erro em cada RQ. Cada RQ mostra:
- a margem de erro de cada grupo pelo seu n (pior caso, p = 0,5), como na tabela da Seção 2;
- a margem ±e de cada proporção exibida (por exemplo, % de concordância, D5 e E8).

### 7. Duplicatas e straightlining

**Desvio:** não (operacionaliza a Seção 5.1).

- **Duplicatas:** respostas idênticas em todos os itens, enviadas a até 60 minutos uma da outra. Fica a primeira.
- **Straightlining:** "Não sei avaliar" nos 8 itens de NIV e IMP também conta.

### 8. Testes por cenário na RQ3

**Desvio:** sim, se usados. Se o alfa de POS ou PRA ficar abaixo de 0,70, a RQ3 também é testada por cenário (Seção 5.3). Esses testes ficam **fora** da família de 14 do Holm e são relatados como exploratórios.

### 9. Privacidade dos dados publicados

**Desvio:** não (Seção 6).

- O CSV bruto e os arquivos com texto digitado pelo respondente (`reclassificacao_outro.csv`, `revisao_anonimizacao.csv`) ficam fora do Git.
- Os dados processados e o log de descartes públicos saem **sem o horário de envio**.
