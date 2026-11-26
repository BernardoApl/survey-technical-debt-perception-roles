"""Respostas abertas (F1, F2): frequência dos códigos temáticos por grupo (#9).

Lê data/manual/codificacao_abertas.csv, preenchido na issue #5. Só mostra
texto já anonimizado e com código final; o texto bruto de F1/F2 nunca aparece.
"""

import math

import pandas as pd
import plotly.express as px
import streamlit as st

from app import contexto
from app.componentes import cabecalho_pagina, nota, secao
from src.config import DIR_MANUAL

CSV_CODIFICACAO = DIR_MANUAL / "codificacao_abertas.csv"
COLUNAS = ["resp_id", "campo", "texto_anonimizado", "codigo_final"]
CAMPOS = {
    "F1": "F1: exemplo recente em que a dívida técnica afetou o trabalho",
    "F2": "F2: o que mais dificulta a redução da dívida técnica",
}

ctx = contexto.obter()
cabecalho_pagina(
    "Respostas abertas",
    "Temas que aparecem nas perguntas abertas, por grupo. Análise temática (Braun e Clarke, 2006) "
    "codificada por dois integrantes; só aparece texto já anonimizado e aprovado.",
    ctx,
)


def aguardando(motivo: str) -> None:
    with secao(1, "Códigos temáticos", chave="abertas-aguardando"):
        st.info(f"Aguardando a codificação das respostas abertas (issue #5): {motivo}.")
    st.stop()


if not CSV_CODIFICACAO.exists():
    aguardando(f"`{CSV_CODIFICACAO.relative_to(DIR_MANUAL.parents[1])}` ainda não existe")

codificacao = pd.read_csv(CSV_CODIFICACAO, dtype=str, keep_default_na=False)
faltam = set(COLUNAS) - set(codificacao.columns)
if faltam:
    aguardando(f"faltam as colunas {sorted(faltam)}")
com_texto = codificacao[codificacao["texto_anonimizado"].str.strip() != ""]
sem_codigo = com_texto["codigo_final"].str.strip() == ""
if sem_codigo.any():
    aguardando(f"{int(sem_codigo.sum())} resposta(s) ainda sem código final")

grupos = ctx.filtrados[["resp_id", "grupo"]]
codificadas = com_texto.merge(grupos, on="resp_id", how="inner")
if codificadas.empty:
    st.warning("Nenhuma resposta aberta codificada entre as respostas filtradas.")
    st.stop()

campo = st.radio("Pergunta", list(CAMPOS), format_func=CAMPOS.get, horizontal=True)
do_campo = codificadas[codificadas["campo"] == campo]
if do_campo.empty:
    st.write("Nenhuma resposta codificada para esta pergunta.")
    st.stop()

# Uma resposta pode ter mais de um código (separados por ";").
codigos = do_campo.assign(codigo=do_campo["codigo_final"].str.split(";")).explode("codigo")
codigos["codigo"] = codigos["codigo"].str.strip()
codigos["grupo"] = codigos["grupo"].fillna("sem grupo")

respondentes = do_campo.groupby(do_campo["grupo"].fillna("sem grupo"))["resp_id"].nunique()
total = do_campo["resp_id"].nunique()


def margem(p: float, n: int) -> float:
    """Margem de erro a 95% de uma proporção (protocolo, Seção 2)."""
    return 1.96 * math.sqrt(p * (1 - p) / n) if n else float("nan")


linhas = []
for (codigo, grupo), parte in codigos.groupby(["codigo", "grupo"]):
    n = respondentes[grupo]
    p = parte["resp_id"].nunique() / n
    linhas.append({"Código": codigo, "Grupo": grupo, "Respostas": parte["resp_id"].nunique(),
                   "%": round(100 * p, 1), "± margem (p.p.)": round(100 * margem(p, n), 1)})
for codigo, parte in codigos.groupby("codigo"):
    p = parte["resp_id"].nunique() / total
    linhas.append({"Código": codigo, "Grupo": "total", "Respostas": parte["resp_id"].nunique(),
                   "%": round(100 * p, 1), "± margem (p.p.)": round(100 * margem(p, total), 1)})
frequencias = pd.DataFrame(linhas).sort_values(["Grupo", "Respostas"], ascending=[True, False])

with secao(1, "Códigos temáticos", chave="abertas-codigos"):
    nota(f"{total} pessoa(s) responderam a esta pergunta. O % é sobre quem respondeu em cada "
         "grupo; uma resposta pode ter mais de um código. A barra de erro é a margem a 95%.")
    figura = px.bar(
        frequencias[frequencias["Grupo"] != "total"], x="%", y="Código", color="Grupo",
        barmode="group", orientation="h", error_x="± margem (p.p.)",
    )
    figura.update_layout(yaxis_title=None, height=150 + 40 * frequencias["Código"].nunique())
    st.plotly_chart(figura, width="stretch")
    st.dataframe(frequencias, hide_index=True, width="stretch")

with secao(2, "Exemplos", chave="abertas-exemplos"):
    escolhido = st.selectbox("Código", sorted(codigos["codigo"].unique()))
    exemplos = codigos[codigos["codigo"] == escolhido].drop_duplicates("resp_id")
    for _, linha in exemplos.iterrows():
        st.markdown(f"> {linha['texto_anonimizado']}\n\n— grupo {linha['grupo']}")
