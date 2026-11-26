"""Dashboard do survey de dívida técnica.

Uso: streamlit run app/streamlit_app.py
Lê data/raw/respostas.csv (ou um CSV sintético, com aviso) a cada execução.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import importlib  # noqa: E402

import streamlit as st  # noqa: E402

# Recarrega os módulos visuais a cada execução: o Streamlit às vezes mantém a versão
# antiga de módulos importados pelas páginas, e o visual não atualiza sem reiniciar.
from app import componentes, graficos  # noqa: E402

importlib.reload(graficos)
importlib.reload(componentes)

from app import contexto  # noqa: E402
from app import dados as dados_app  # noqa: E402
from app import publico  # noqa: E402
from app.dados import NOME_PERIODO, preparar  # noqa: E402
from app.filtros import FILTROS, aplicar_filtros, filtros_ativos, rotular  # noqa: E402

st.set_page_config(page_title="Dívida técnica por papel", page_icon="📊", layout="wide")
st.html(f"<style>{(Path(__file__).parent / 'estilo.css').read_text(encoding='utf-8')}</style>")

# No Cloud o CSV bruto não existe: usar somente a fotografia agregada publicada.
if not dados_app.CSV_BRUTO.exists() and publico.ARQUIVO_PUBLICO.exists():
    publico.renderizar(publico.ARQUIVO_PUBLICO)
    st.stop()

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
    selecao, opcoes_presentes = {}, {}
    for coluna, (rotulo, opcoes, _) in FILTROS.items():
        presentes = set(rotular(analise.dados, coluna).dropna())
        disponiveis = [o for o in opcoes if o in presentes]
        opcoes_presentes[coluna] = disponiveis
        selecao[coluna] = st.multiselect(rotulo, disponiveis, default=disponiveis, key=f"f_{coluna}")

    pendentes = int(analise.dados["grupo_pendente"].sum())
    if pendentes:
        st.warning(f"{pendentes} resposta(s) com papel \"Outro\" ainda sem grupo; "
                   "saem quando o filtro de grupo está ativo.")

contexto.guardar(
    contexto.Contexto(
        nome_analise=NOME_PERIODO,
        analise=analise,
        filtrados=aplicar_filtros(analise.dados, selecao, opcoes_presentes),
        filtros_ativos=filtros_ativos(selecao, opcoes_presentes),
        sintetico=e_sintetico,
    )
)

if e_sintetico:
    st.error(
        "**DADOS SINTÉTICOS.** Não há `data/raw/respostas.csv`; os números abaixo são "
        "fictícios e servem só para desenvolvimento."
    )

navegacao.run()
