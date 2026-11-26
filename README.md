<div align="center">

# 🧭 Dívida Técnica: o Mesmo Código, Visões Diferentes

### Como profissionais técnicos e de gestão percebem o nível, o impacto e a gestão da dívida técnica

<br>

Medição e Experimentação em Engenharia de Software

PUC Minas · 2º semestre de 2026

<br>

**Bernardo Augusto Pereira** · **Felipe Pereira de Sousa** · **Gabriel Reis Lebron**

</div>

---

## 📌 Sobre

Devs, tech leads, POs e gerentes trabalham no mesmo sistema, mas será que enxergam a **dívida técnica** da mesma forma?

Este repositório reúne o survey que compara como profissionais de **papéis técnicos** e de **gestão** percebem o nível, o impacto e a priorização da dívida técnica nos projetos em que trabalham. A pesquisa é feita com um questionário online **anônimo**, de cerca de 10 minutos, respondido por profissionais de equipes de desenvolvimento de software no Brasil.

> **Dívida técnica** são atalhos ou decisões técnicas que trazem ganho no curto prazo (por exemplo, entregar mais rápido), mas deixam o software mais difícil ou caro de mudar depois.

O planejamento completo (questões de pesquisa, questionário, amostragem e plano de análise) está no [protocolo do survey](planejamento_survey.pdf).

## Executar a análise

Instale as dependências com `python -m pip install -r requirements.txt`, coloque a exportação do formulário em `data/raw/respostas.csv` e execute `python -m src.pipeline`. O comando valida o formulário, limpa e recodifica os dados, gera escores, descritivas, confiabilidade, testes e saídas das respostas abertas. Os resultados são gravados em `outputs/` e `data/processed/`; `outputs/resumo_amostra.json` contém a conferência de recebidas, descartadas e válidas por grupo, e `outputs/desvios.json` registra a prorrogação e os desvios calculados. A semente é 2026.

Os arquivos em `data/manual/` guardam decisões humanas e são preservados entre execuções. A classificação de cargos, revisão de anonimização, codificação e consenso devem ser completados conforme [o procedimento](docs/procedimento-abertas.md); enquanto houver pendências, os resultados correspondentes são parciais. Não publique o CSV bruto nem os arquivos manuais com texto de respondentes. A análise principal usa a coleta prorrogada até 25/11/2026; a margem de erro e os testes por cenário permanecem propostas no documento de decisões.

As saídas individuais de `data/processed/` ficam fora do Git. Se o alfa de POS ou PRA for menor que 0,70, o pipeline gera testes exploratórios por cenário, separados dos 14 testes confirmatórios; se o alfa não puder ser calculado, a limitação aparece em `outputs/desvios.json`.

Para gerar os 14 testes confirmatórios a partir do CSV bruto em `data/raw/respostas.csv`, execute `python -m src.testes_rq`. O arquivo `outputs/testes_rq.csv` mantém também os testes não executáveis, com motivo. Holm considera as 14 hipóteses mesmo quando faltam p-valores. As margens por grupo usam o n válido de cada teste e p = 0,5; em D5 e E8, `proporcoes` contém frequências e margens por categoria e grupo. Essas margens são indicativas, pois a amostra é por conveniência. O aviso de baixo poder usa o total de participantes de gestão da amostra válida. O r de Mann-Whitney usa Z assintótico com correção de empates, sem correção de continuidade, e sinal positivo quando o grupo técnico tende a valores maiores; o p usa a aproximação bilateral com correção de continuidade. O r de Wilcoxon é a magnitude de Z dividida pela raiz do número de pares válidos. Os testes globais incluem respostas com papel pendente; as comparações por grupo as excluem. O critério de Fisher e a alternativa de permutação estão em [DEVIATIONS.md](DEVIATIONS.md).
