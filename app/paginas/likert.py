"""Itens Likert: barras divergentes de C1–C4 e D1–D4, total e por grupo (#10).

Todos os números vêm de src.describe (as mesmas funções de
outputs/concordancia_likert.csv e distribuicao_likert.csv), calculados sobre as
respostas que passam pelos filtros da barra lateral.
"""

import streamlit as st

from app import contexto
from app.componentes import cabecalho_pagina, nota, secao
from app.graficos import ROTULOS_RECORTE, barras_divergentes, legenda_likert, mostrar
from src.config import ENUNCIADOS, ITENS_CONSTRUTO
from src.describe import concordancia_likert, distribuicao_likert, frequencias
from src.recode import ITENS_INVERTIDOS

CONSTRUTOS = [
    ("NIV", "Nível percebido de dívida técnica (NIV)"),
    ("IMP", "Impacto percebido nos últimos 3 meses (IMP)"),
]

ctx = contexto.obter()
cabecalho_pagina(
    "Itens Likert",
    "Como cada grupo respondeu às afirmações sobre o nível (C1–C4) e o impacto (D1–D4) "
    "da dívida técnica. Cada barra soma 100% de quem avaliou o item, com o neutro no centro.",
    ctx,
)

dados = ctx.filtrados
if dados.empty:
    st.warning("Nenhuma resposta válida passa pelos filtros escolhidos.")
    st.stop()

concordancia = concordancia_likert(dados)
distribuicao = distribuicao_likert(frequencias(dados))

nota(legenda_likert())
nota("À direita de cada barra: <b>% de concordância</b> (Concordo parcialmente ou totalmente) "
     "± margem de erro a 95% (protocolo, Seção 2). \"Não sei avaliar\" fica fora do n e aparece "
     "na tabela no fim da página. Itens com (R) são invertidos: concordar indica <b>menos</b> "
     "dívida técnica. Aqui eles aparecem como foram respondidos, sem a inversão usada nos escores.")

for numero, (construto, titulo) in enumerate(CONSTRUTOS, start=1):
    with secao(numero, titulo, chave=f"likert-{construto.lower()}"):
        for item in ITENS_CONSTRUTO[construto]:
            marca = " (R)" if item in ITENS_INVERTIDOS else ""
            st.markdown(f"**{item}{marca}.** {ENUNCIADOS[item]}")
            mostrar(barras_divergentes(distribuicao[distribuicao["item"] == item],
                                       concordancia[concordancia["item"] == item]))

with secao(len(CONSTRUTOS) + 1, "Tabela", chave="likert-tabela"):
    nao_sei = distribuicao.drop_duplicates(["item", "recorte"]).set_index(["item", "recorte"])
    com_n = concordancia[concordancia["n"] > 0]
    tabela = com_n.assign(
        texto=com_n["item"].map(ENUNCIADOS),
        recorte=com_n["recorte"].map(ROTULOS_RECORTE),
        nao_sei=[int(nao_sei.at[(i, r), "nao_sei"]) for i, r in zip(com_n["item"], com_n["recorte"])],
        pct=com_n["pct"].round(1),
        margem_pp=com_n["margem_pp"].round(1),
    )[["item", "texto", "recorte", "n", "nao_sei", "k", "pct", "margem_pp"]]
    st.dataframe(
        tabela, hide_index=True, width="stretch",
        column_config={
            "item": "Item", "texto": "Afirmação", "recorte": "Recorte",
            "n": st.column_config.NumberColumn("n", help="Responderam de 1 a 5"),
            "nao_sei": st.column_config.NumberColumn("Não sei avaliar"),
            "k": st.column_config.NumberColumn("Concordam", help="Respostas 4 ou 5"),
            "pct": st.column_config.NumberColumn("% concordância", format="%.1f"),
            "margem_pp": st.column_config.NumberColumn("± margem (p.p.)", format="%.1f"),
        },
    )
    nota("Como a amostra é por conveniência, a margem é indicativa. Diferenças entre grupos "
         "menores que a margem não são tratadas como conclusivas (protocolo, Seção 2).")
