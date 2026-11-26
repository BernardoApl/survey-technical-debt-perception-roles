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

Regras de execução (#5; passo a passo em `docs/procedimento-abertas.md`):

- **O que entra:** F1 e F2 não vazios das respostas válidas (período do item 1).
- **Livro de códigos:** `data/manual/livro_codigos.csv` (versionado). A versão inicial parte das três categorias citadas na Seção 5.7 (pressão de prazo, falta de testes e falta de apoio da gestão, válidas para F1 e F2), dos tipos e efeitos já medidos em C6 e D5 e das causas e efeitos de DT de Rios et al. (2018), citados no protocolo.
- **Rastreabilidade:** F1 responde à RQ2 e F2 à RQ3 (tabela da Seção 3). A tabela de frequências traz essa coluna. Depois da leitura das respostas (fase de familiarização de Braun e Clarke), a dupla ajusta o livro **antes** de codificar. Código novo que surgir durante a codificação entra no livro, e os dois revisam os textos já codificados.
- **Vários códigos por texto:** permitido. `outro` marca tema sem código (descrito em `observacao`). `nao_codificavel` marca resposta sem conteúdo analisável.
- **Independência:** cada codificador preenche só a sua planilha e não abre a do outro até os dois terminarem.
- **Divergência:** texto em que os conjuntos de códigos não são idênticos. A dupla decide o conjunto final junto, com justificativa.
- **Concordância:** % de concordância e kappa de Cohen por código, calculados antes do consenso. São só descritivos: não mudam nenhum critério.
- **Frequência:** por item e código, k / n, em que n = textos do item com códigos finais no recorte (inclui `nao_codificavel`). Como um texto pode ter vários códigos, os % de um item não somam 100. Margem ±e pela fórmula da Seção 2 com o p observado (item 6). Total, técnico e gestão. Papel "Outro" ainda sem grupo entra só no total.

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

- O CSV bruto e os arquivos com texto digitado pelo respondente (`reclassificacao_outro.csv`, `revisao_anonimizacao.csv` e as planilhas `codificacao_*.csv`) ficam fora do Git.
- Os dados processados e o log de descartes públicos saem **sem o horário de envio**.
- O texto aprovado de F1/F2 (`data/processed/respostas_abertas.csv`) sai **sem `resp_id`**, só com item, grupo de papel e códigos. Os códigos com `resp_id` (`codigos_abertas.csv`) saem sem texto. Assim nenhum arquivo público liga um relato ao perfil completo de quem respondeu (Seção 6: "só resultados agregados são publicados"). Consequência: no dashboard, os filtros de perfil valem para as frequências dos códigos, mas não para os exemplos de texto.

### 10. Estatística descritiva e confiabilidade (#6)

**Desvio:** não (operacionaliza as Seções 2, 3, 5.3 e 5.4). Código em `src/describe.py` e `src/reliability.py`; `python -m src.describe` grava as tabelas em `outputs/`.

- **Recortes:** total, técnico e gestão. Papel "Outro" ainda sem grupo entra só no total.
- **Frequências:** n = respostas que responderam ao item, com "Não sei" contado como uma opção. Ficam de fora A1 e B1 (todas as válidas responderam "Sim") e ATN (todas marcaram a opção pedida). Cargo digitado em "Outro" aparece só como "Outro".
- **C6 (múltipla escolha):** cada opção é uma proporção separada. Nos 6 tipos, n exclui quem marcou só "Não sei" (o mesmo denominador do M3); em "Nenhum" e "Não sei", n são todas as respostas.
- **% de concordância:** respostas 4 ou 5 sobre as que não são "Não sei avaliar" (tratado como ausente, Seção 3). Em C4 e D2 vale a resposta **como foi marcada**, isto é, a concordância com a frase do formulário, antes da inversão.
- **Margem de erro:** fórmula da Seção 2 com o p observado, em toda proporção (item 6).
- **Mediana e IQR:** NIV, IMP, POS, PRA, DIST e C5, total e por grupo. Quartis pelo método linear do pandas (tipo 7 de Hyndman e Fan).
- **Alfa de Cronbach:** só com as respostas que têm todos os itens do construto (listwise), com C4 e D2 invertidos. IC 95% de Feldt, a mesma fórmula do pingouin (conferido em teste). A tabela traz n, quantas respostas ficaram de fora, se atinge a meta de 0,70, o alfa sem cada item e a correlação item-total corrigida. Calculado na amostra total, não por grupo.
- **Validade convergente:** Spearman bilateral NIV × C5 e PRA × E7, com as respostas que têm os dois valores. Espera-se ρ positivo; os dois testes ficam fora da família de 14 do Holm.
- **Dashboard (#10):** a página de itens Likert segue os filtros da barra lateral. As barras divergentes mostram o % de cada opção sobre quem avaliou o item (sem "Não sei avaliar"), com o neutro no centro, e a soma de "Concordo" é o mesmo % de concordância da tabela. A página de confiabilidade usa sempre a amostra válida completa, porque a qualidade da medida não deve mudar com um recorte.
