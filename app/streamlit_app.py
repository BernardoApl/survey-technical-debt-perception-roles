"""Dashboard do survey de dívida técnica.

Uso: streamlit run app/streamlit_app.py
Lê data/raw/respostas.csv (ou um CSV sintético, com aviso) a cada execução.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402

from app import contexto  # noqa: E402
from app.dados import NOME_PERIODO, preparar  # noqa: E402
from app.filtros import FILTROS, aplicar_filtros, filtros_ativos, rotular  # noqa: E402

st.set_page_config(page_title="Dívida técnica por papel", layout="wide")

PAGINAS = Path(__file__).parent / "paginas"
navegacao = st.navigation(
    {
        "Amostra": [
            st.Page(PAGINAS / "perfil.py", title="Perfil da amostra", default=True),
        ],
        "Resultados": [
            st.Page(PAGINAS / "likert.py", title="Itens Likert"),
            st.Page(PAGINAS / "rqs.py", title="Questões de pesquisa"),
            st.Page(PAGINAS / "confiabilidade.py", title="Confiabilidade"),
            st.Page(PAGINAS / "abertas.py", title="Respostas abertas"),
        ],
        "Estudo": [
            st.Page(PAGINAS / "metodologia.py", title="Metodologia e desvios"),
        ],
    }
)

analise, e_sintetico = preparar()

with st.sidebar:
    st.caption(NOME_PERIODO)

    st.subheader("Filtros por segmento")
    st.caption("Valem para Perfil, Itens Likert e Respostas abertas. "
               "Os testes das questões de pesquisa usam sempre a amostra completa.")
    selecao = {}
    for coluna, (rotulo, opcoes, _) in FILTROS.items():
        presentes = set(rotular(analise.dados, coluna).dropna())
        disponiveis = [o for o in opcoes if o in presentes]
        selecao[coluna] = st.multiselect(rotulo, disponiveis, default=disponiveis, key=f"f_{coluna}")

    pendentes = int(analise.dados["grupo_pendente"].sum())
    if pendentes:
        st.warning(f"{pendentes} resposta(s) com papel \"Outro\" ainda sem grupo; "
                   "saem quando o filtro de grupo está ativo.")

contexto.guardar(
    contexto.Contexto(
        nome_analise=NOME_PERIODO,
        analise=analise,
        filtrados=aplicar_filtros(analise.dados, selecao),
        filtros_ativos=filtros_ativos(selecao),
        sintetico=e_sintetico,
    )
)

if e_sintetico:
    st.error(
        "**DADOS SINTÉTICOS.** Não há `data/raw/respostas.csv`; os números abaixo são "
        "fictícios e servem só para desenvolvimento."
    )

navegacao.run()
