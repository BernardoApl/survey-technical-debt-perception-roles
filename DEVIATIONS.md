# Desvios do protocolo

## Permutação do qui-quadrado em D5 e E8 (condicional)

- **O quê:** depois de agrupar as categorias com menos de cinco respostas, se a enumeração exata de Fisher-Freeman-Halton exigir mais de 200.000 tabelas com as mesmas margens, usa-se o qui-quadrado de Pearson com 99.999 permutações e semente 2026. A coluna `desvio` em `testes_rq.csv` identifica cada uso efetivo.
- **Por quê:** limitar antecipadamente o custo computacional da enumeração exata, sem escolher o método pelo p-valor.
- **Impacto:** o p-valor é estimado por permutação, sujeito a erro de Monte Carlo, e usa a estatística qui-quadrado em vez da ordenação por probabilidade do teste de Fisher. Continua na família Holm de 14 testes.

Outros desvios e sua ocorrência efetiva serão consolidados na issue #8.
