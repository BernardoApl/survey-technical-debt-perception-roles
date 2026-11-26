# Desvios do protocolo

## Permutação do qui-quadrado em D5 e E8 (condicional)

- **Resumo:** Quando o protocolo pede Fisher em D5 ou E8 e o cálculo exato fica pesado demais, usa-se o χ² por permutação.
- **O quê:** depois de agrupar as categorias com menos de cinco respostas, se alguma frequência esperada for menor que 5 (caso em que a Seção 5.5 pede Fisher) e a enumeração exata de Fisher-Freeman-Halton exigir mais de 200.000 tabelas com as mesmas margens, usa-se o qui-quadrado de Pearson com 99.999 permutações e semente 2026. A coluna `desvio` em `testes_rq.csv` identifica cada uso efetivo.
- **Por quê:** limitar antecipadamente o custo computacional da enumeração exata, sem escolher o método pelo p-valor.
- **Impacto:** o p-valor é estimado por permutação, sujeito a erro de Monte Carlo, e usa a estatística qui-quadrado em vez da ordenação por probabilidade do teste de Fisher. Continua na família Holm de 14 testes.

## Prorrogação da coleta até 25/11/2026

- **Resumo:** A coleta foi estendida de 22/11 para 25/11 por falta de respostas.
- **O quê:** a análise principal inclui respostas de 13/11 a 25/11, em vez de encerrar em 22/11 como previsto no protocolo.
- **Por quê:** o grupo decidiu prorrogar a coleta devido ao número insuficiente de respostas, antes de observar os resultados, conforme `docs/decisoes-analise.md`.
- **Impacto:** respostas recebidas na prorrogação integram a análise principal. `outputs/desvios.json` registra os totais recebidos e válidos de 23/11 a 25/11. Conforme a decisão 1, não há análise separada do período pré-registrado.

## Divulgação com um repost em vez de dois

- **Resumo:** Houve um repost no LinkedIn em vez dos dois previstos.
- **O quê:** o protocolo (Seção 8) previa um post no LinkedIn com reposts em 16/11 e 19/11. Houve um post e um único repost, dois dias depois. As datas reais e as capturas datadas ficam com as evidências da coleta (#13).
- **Por quê:** o segundo repost não foi feito dentro do cronograma planejado. Para compensar a divulgação menor e o número de respostas abaixo do esperado, o grupo prorrogou a coleta até 25/11, em vez de reabrir a divulgação depois do prazo.
- **Impacto:** menos lembretes nos canais podem ter reduzido o alcance e o número de respostas, sobretudo de gestão; a prorrogação até 25/11 compensou parte disso. Não afeta os critérios de análise.

## Amostra abaixo do mínimo e cota de gestão (condicionais)

- **Resumo:** Menos de 50 respostas válidas, ou gestão abaixo da meta de 20 (mínimo 15).
- **O quê:** a amostra pode ter menos de 50 respostas válidas e/ou não atingir a meta de 20 participantes de gestão ou o mínimo de 15.
- **Por quê:** participação por conveniência e adesão efetiva abaixo das metas planejadas; o pipeline registra a ocorrência e os números em `outputs/desvios.json`.
- **Impacto:** estimativas ficam mais imprecisas e comparações entre papéis podem ter baixo poder. Papéis pendentes são informados separadamente e podem alterar essas contagens após a classificação humana.

## Testes não executáveis (condicional)

- **Resumo:** Teste sem dados suficientes fica listado, sem p-valor.
- **O quê:** testes sem dados suficientes ou variação permanecem na tabela sem p-valor, com motivo também registrado em `outputs/desvios.json`.
- **Por quê:** a amostra observada pode não satisfazer os requisitos matemáticos do teste planejado.
- **Impacto:** a hipótese correspondente não recebe conclusão estatística. As demais continuam corrigidas por Holm considerando a família de 14 hipóteses.

## Análises exploratórias por cenário (condicional)

- **Resumo:** Se o alfa de POS ou PRA ficar abaixo de 0,70, há testes por cenário, fora do Holm.
- **O quê:** se o alfa de POS ou PRA for inferior a 0,70, cada vinheta recebe comparações de postura por grupo, postura × prática pareada e distância por grupo.
- **Por quê:** escores agregados de vinhetas com baixa consistência interna exigem a análise separada prevista na seção 5.3 do protocolo.
- **Impacto:** os testes adicionais são exploratórios, sem correção Holm, e constam de `outputs/testes_cenarios_exploratorios.csv`, separados das 14 hipóteses confirmatórias. A ocorrência e eventual alfa indefinido constam de `outputs/desvios.json`.
