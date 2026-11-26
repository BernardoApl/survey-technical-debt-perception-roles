<div align="center">

# 🧭 Dívida Técnica: o Mesmo Código, Visões Diferentes

### Como profissionais técnicos e de gestão percebem o nível, o impacto e a gestão da dívida técnica

<br>

Medição e Experimentação em Engenharia de Software

PUC Minas · 2º semestre de 2026

<br>

**Bernardo Augusto Pereira** · **Felipe Pereira de Sousa** · **Gabriel Reis Lebron** · **Lorran Avelar**

</div>

---

## 📌 Sobre

Devs, tech leads, POs e gerentes trabalham no mesmo sistema, mas será que enxergam a **dívida técnica** da mesma forma?

Este repositório reúne o survey que compara como profissionais de **papéis técnicos** e de **gestão** percebem o nível, o impacto e a priorização da dívida técnica nos projetos em que trabalham. A pesquisa usa um questionário online **anônimo**, de cerca de 10 minutos, respondido por profissionais de equipes de desenvolvimento de software no Brasil.

> **Dívida técnica** são atalhos ou decisões técnicas que trazem ganho no curto prazo (por exemplo, entregar mais rápido), mas deixam o software mais difícil ou caro de mudar depois.

O planejamento completo (questões de pesquisa, questionário, amostragem e plano de análise) está em [planejamento_survey.pdf](planejamento_survey.pdf).

---

## ⚙️ Instalação

Requer **Python 3.12** (dependências fixadas em [requirements.txt](requirements.txt)). Também há configuração opcional para Dev Containers / Codespaces em [`.devcontainer/`](.devcontainer/devcontainer.json).

Crie e ative um ambiente virtual na raiz do repositório:

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 📄 Onde colocar o CSV, modo público e privacidade

1. **CSV bruto local:** exporte as respostas do Google Forms em CSV (UTF-8) e salve em:
   ```text
   data/raw/respostas.csv
   ```
2. **Privacidade (LGPD):** o repositório é público. Por regra do [`.gitignore`](.gitignore), ficam fora do Git:
   - `data/raw/respostas.csv` e demais arquivos em `data/raw/` (exceto `.gitkeep`);
   - `data/manual/reclassificacao_outro.csv`, `data/manual/revisao_anonimizacao.csv` e `data/manual/codificacao_*.csv`;
   - `data/processed/` e saídas em `outputs/`;
   - planilhas `*.xlsx` e CSVs soltos na raiz.
3. **Modos de abertura do dashboard (`app/streamlit_app.py`):**
   - **Com `data/raw/respostas.csv` local:** abre o painel completo com filtros por segmento e todas as 7 páginas.
   - **Sem CSV bruto, com `data/publico/resultados.json`:** abre o modo público agregado ([`app/publico.py`](app/publico.py)), exibindo apenas tabelas e gráficos agregados sem respostas individuais nem textos abertos (gerado localmente via `python -m src.publicar_agregados`).
   - **Sem CSV bruto e sem fotografia pública:** gera automaticamente `data/raw/sintetico.csv` e exibe aviso de **dados sintéticos** em todas as páginas (também pode ser gerado com `python -m src.sintetico --n 80 --saida data/raw/sintetico.csv`).

---

## ▶️ Como executar

### Pipeline completo (comando único)

Com `data/raw/respostas.csv` no lugar, execute na raiz do projeto:

```bash
python -m src.pipeline
```

O comando usa semente `2026` e regenera tudo do zero:
- valida cabeçalhos e datas do formulário;
- aplica a limpeza (etapas 0 a 6), recodifica e calcula os escores;
- gera estatísticas descritivas, confiabilidade, validade convergente e os 14 testes confirmatórios (`outputs/testes_rq.csv`);
- gera testes exploratórios por cenário em `outputs/testes_cenarios_exploratorios.csv` quando o alfa de `POS` ou `PRA` for menor que `0,70` (se o alfa não puder ser calculado, registra a limitação em `outputs/desvios.json`);
- sincroniza as planilhas de revisão/codificação das abertas em `data/manual/` preservando decisões já preenchidas e grava as saídas em `outputs/` e `data/processed/`;
- grava `outputs/resumo_amostra.json` (`recebidas = válidas + descartadas` e `validas_por_grupo`) e `outputs/desvios.json` (respostas recebidas e válidas na prorrogação de `23/11` a `25/11`, amostra abaixo do mínimo, cota de gestão, testes não executáveis, permutação, pendências abertas e estado dos testes por cenário).

Os arquivos manuais em `data/manual/` seguem [docs/procedimento-abertas.md](docs/procedimento-abertas.md); enquanto houver pendências humanas, os resultados correspondentes são parciais. Também é possível rodar etapas isoladas (`python -m src.load`, `python -m src.clean`, `python -m src.abertas`, `python -m src.describe`, `python -m src.testes_rq`).

### Fotografia agregada para deploy público

Para atualizar [data/publico/resultados.json](data/publico/resultados.json) a partir de `data/raw/respostas.csv` sem incluir dados individuais nem textos abertos:

```bash
python -m src.publicar_agregados
```

**Notas metodológicas dos testes (`src.testes_rq` / `src.pipeline`):**
- `outputs/testes_rq.csv` mantém todas as 14 hipóteses da Seção 5.5 do protocolo, inclusive as não executáveis (com motivo).
- A correção de Holm-Bonferroni considera a família de 14 hipóteses mesmo quando faltam p-valores.
- As margens por grupo usam o `n` válido de cada teste e pior caso (`p = 0,5`); em `D5` e `E8`, `proporcoes` traz frequências e margens por categoria e grupo. Como a amostra é por conveniência, as margens são indicativas.
- O aviso de baixo poder usa o total de participantes de gestão na amostra válida.
- O tamanho de efeito `r` de Mann-Whitney usa `Z` assintótico com correção de empates, sem correção de continuidade, e sinal positivo quando o grupo técnico tende a valores maiores; o p-valor usa a aproximação bilateral com correção de continuidade.
- O `r` de Wilcoxon é `|Z|` dividido pela raiz do número de pares válidos.
- Em `D5` e `E8`, após agrupar categorias com menos de 5 respostas, usa-se qui-quadrado de Pearson quando todas as frequências esperadas são ≥ 5 e Fisher-Freeman-Halton exato quando alguma é < 5 (registrado em `esperada_minima`; decisão 11 de [docs/decisoes-analise.md](docs/decisoes-analise.md)), com fallback por permutação acima de 200.000 tabelas ([DEVIATIONS.md](DEVIATIONS.md)).
- Testes globais incluem respostas com papel "Outro" ainda pendente; comparações entre grupos as excluem.

### Dashboard (Streamlit)

```bash
streamlit run app/streamlit_app.py
```

Páginas implementadas no painel:
- *Perfil da amostra* · *Itens Likert* · *Questões de pesquisa* (M1–M10, 14 testes, conclusões geradas dos números, aviso de baixo poder e explorador agregado) · *Confiabilidade* · *Respostas abertas* · *O que foi medido* · *Metodologia e desvios*.

### Testes automatizados

Os testes usam apenas dados sintéticos (não requerem `data/raw/respostas.csv`):

```bash
pytest -v
```

---

## 📋 Análise principal e decisões metodológicas

Todas as decisões anteriores à análise estão registradas em [docs/decisoes-analise.md](docs/decisoes-analise.md) (`#1`).

### Análise principal adotada
- **Período oficial:** respostas enviadas entre **13/11/2026 00:00 e 25/11/2026 23:59:59** (`America/Sao_Paulo`), incorporando a prorrogação sobre o encerramento pré-registrado de 22/11/2026 por volume insuficiente de respostas, sem consulta prévia aos resultados e sem análise separada apenas até 22/11 ([DEVIATIONS.md](DEVIATIONS.md)).

### Resumo das decisões fechadas
- **Reclassificação de "Outro" (`B2`):** feita olhando apenas o texto do cargo (técnico, gestão ou fora da amostra; ambíguo vai para fora).
- **Anonimização (`F1`/`F2`):** nomes de pessoas, empresas, clientes, produtos/sistemas internos e locais identificáveis são trocados por `[removido]`; na dúvida, remove-se.
- **Codificação temática (`F1`/`F2`):** codificação independente por dois integrantes a partir de [data/manual/livro_codigos.csv](data/manual/livro_codigos.csv), seguida de consenso.
- **Recortes pequenos no dashboard:** supressão automática não implementada; os filtros existentes não identificam respondentes e exemplos de texto aberto são publicados sem `resp_id`.
- **Critério de `D5` e `E8` (item 11):** alinhado à Seção 5.5 do protocolo (qui-quadrado quando todas as esperadas são ≥ 5; Fisher exato quando alguma é < 5).

### Decisões humanas pendentes
- **Confirmações da `#1`:** confirmar formalmente o fechamento do formulário em 25/11/2026 às 23:59 e os itens 6 a 9 de [docs/decisoes-analise.md](docs/decisoes-analise.md) (margem de erro nas RQs, regra de duplicatas e *straightlining*, testes exploratórios por cenário se alfa < 0,70 e regras de privacidade — vigentes como padrão salvo decisão contrária).
- **Etapas manuais das abertas (`#5`):** completar eventuais pendências em `data/manual/` quando executado sobre o CSV bruto.
- **Evidências da coleta (`#13`):** capturas datadas e anonimizadas registradas em [docs/evidencias/](docs/evidencias/) (com o CSV bruto mantido em pasta privada fora do Git); pendente o teste de acesso ao painel do Google Forms sem expor respostas individuais.

---

## 🗂️ Estrutura do repositório

- `app/` — dashboard Streamlit (`streamlit_app.py`, `dados.py`, `filtros.py`, `graficos.py`, `componentes.py`, `glossario.py`, `metodologia_dados.py`, `rqs_dados.py`, `publico.py`, `paginas/`)
- `src/` — pipeline em Python (`pipeline.py`, `publicar_agregados.py`, `config.py`, `load.py`, `clean.py`, `recode.py`, `score.py`, `abertas.py`, `describe.py`, `reliability.py`, `testes_rq.py`, `sintetico.py`)
- `data/` — `raw/` (CSV bruto fora do Git), `manual/` (`livro_codigos.csv` versionado; planilhas com texto livre fora do Git), `processed/` (saídas limpas fora do Git) e `publico/` (`resultados.json` agregado)
- `docs/` — [decisoes-analise.md](docs/decisoes-analise.md), [procedimento-abertas.md](docs/procedimento-abertas.md) e [evidencias/](docs/evidencias/) (prints sanitizados da divulgação)
- `tests/` — testes automatizados com dados sintéticos
- `.devcontainer/` — configuração opcional de Dev Container
- `DEVIATIONS.md` — desvios em relação ao protocolo pré-registrado
- `planejamento_survey.pdf` — protocolo pré-registrado (fonte da verdade)
