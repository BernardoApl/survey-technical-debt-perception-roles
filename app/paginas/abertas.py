"""Respostas abertas (F1, F2): frequência dos códigos temáticos por grupo (#9, #5).

Lê o que `python -m src.abertas` grava (issue #5):
- data/processed/codigos_abertas.csv: resp_id, item, codigo (códigos finais, sem texto);
- data/processed/respostas_abertas.csv: item, grupo, codigos, texto (texto aprovado, sem resp_id);
- outputs/pendencias_abertas.json: o que ainda falta anonimizar, codificar ou decidir.

As frequências usam a mesma função de outputs/frequencia_codigos.csv e respeitam
os filtros. Os exemplos de texto não têm resp_id (docs/decisoes-analise.md,
item 9), por isso só podem ser separados por grupo, não pelos filtros de perfil.
O texto original de F1/F2 nunca aparece aqui.
"""

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import contexto
from app.componentes import cabecalho_pagina, nota, secao
from app.graficos import CORES_GRUPO, ROTULOS_GRUPO, fmt, mostrar
from src import config
from src.abertas import frequencias, ler_livro

CAMPOS = {
    "F1": "F1 · exemplo recente em que a dívida técnica afetou o trabalho (RQ2)",
    "F2": "F2 · o que mais dificulta a redução da dívida técnica (RQ3)",
}

ctx = contexto.obter()
cabecalho_pagina(
    "Respostas abertas",
    "Temas que aparecem nas perguntas abertas, por grupo. Análise temática (Braun e Clarke, 2006) "
    "codificada por dois integrantes; só aparece texto já anonimizado e aprovado.",
    ctx,
)

csv_codigos = config.DIR_PROCESSADO / "codigos_abertas.csv"
csv_textos = config.DIR_PROCESSADO / "respostas_abertas.csv"
json_pendencias = config.DIR_SAIDAS / "pendencias_abertas.json"


def aguardando(motivo: str) -> None:
    with secao(1, "Códigos temáticos", chave="abertas-aguardando"):
        st.info(f"Aguardando a codificação das respostas abertas (issue #5): {motivo}.")
    st.stop()


if not csv_codigos.exists():
    aguardando("rode `python -m src.abertas` depois da anonimização e da codificação")
if json_pendencias.exists():
    p = json.loads(json_pendencias.read_text(encoding="utf-8"))
    faltam = p["anonimizacao"] + sum(p["codificacao"].values()) + p["consenso"]
    if faltam:
        aguardando(f"{faltam} pendência(s) de anonimização, codificação ou consenso")

codigos = pd.read_csv(csv_codigos, dtype=str, keep_default_na=False)
dados = ctx.filtrados
codigos = codigos[codigos["resp_id"].isin(dados["resp_id"])]
if codigos.empty:
    st.warning("Nenhuma resposta aberta codificada entre as respostas filtradas.")
    st.stop()

finais = (codigos.groupby(["resp_id", "item"])["codigo"].agg(frozenset)
          .rename("codigos").reset_index())
grupo_por_resp = pd.Series(dados["grupo"].to_numpy(), index=dados["resp_id"])
livro = ler_livro()
tabela = frequencias(finais, grupo_por_resp, livro)

campo = st.radio("Pergunta", list(CAMPOS), format_func=CAMPOS.get, horizontal=True)
do_campo = tabela[tabela["item"] == campo]
n_total = int(do_campo.loc[do_campo["recorte"] == "total", "n"].max())
if not n_total:
    st.write("Nenhuma resposta codificada para esta pergunta.")
    st.stop()

# Só os códigos que aparecem no total, do mais ao menos frequente.
total = do_campo[(do_campo["recorte"] == "total") & (do_campo["k"] > 0)]
ordem = total.sort_values("k", ascending=False)["nome"].tolist()

with secao(1, "Códigos temáticos", chave="abertas-codigos"):
    nota(f"{n_total} resposta(s) a esta pergunta com códigos finais. O % é sobre quem respondeu "
         "em cada grupo; uma resposta pode ter mais de um código, então os % não somam 100. "
         "A barra de erro é a margem a 95% (protocolo, Seção 2).")
    figura = go.Figure()
    for grupo in ("técnico", "gestão"):
        parte = do_campo[do_campo["recorte"] == grupo].set_index("nome").reindex(ordem)
        if not parte["n"].fillna(0).any():
            continue
        figura.add_bar(
            y=ordem, x=parte["pct"], orientation="h", name=ROTULOS_GRUPO[grupo],
            marker_color=CORES_GRUPO[grupo],
            error_x={"type": "data", "array": parte["margem_pp"].tolist(), "thickness": 1.2,
                     "color": "#6b6b76"},
            customdata=[[fmt(p), fmt(m), int(k), int(n)] for p, m, k, n in
                        zip(parte["pct"], parte["margem_pp"], parte["k"], parte["n"])],
            hovertemplate=("%{y}<br>%{customdata[0]}% ± %{customdata[1]} "
                           "(%{customdata[2]} de %{customdata[3]})<extra>" + ROTULOS_GRUPO[grupo]
                           + "</extra>"),
        )
    figura.update_layout(
        barmode="group", height=120 + 46 * len(ordem), margin={"l": 10, "r": 20, "t": 10, "b": 40},
        xaxis={"title": "% de quem respondeu no grupo", "range": [0, 105]},
        yaxis={"autorange": "reversed", "title": None},
        legend={"orientation": "h", "y": 1.08, "x": 0},
    )
    mostrar(figura)
    st.dataframe(
        do_campo[do_campo["nome"].isin(ordem) & (do_campo["n"] > 0)].assign(
            pct=lambda t: t["pct"].round(1), margem_pp=lambda t: t["margem_pp"].round(1),
        )[["nome", "codigo", "recorte", "n", "k", "pct", "margem_pp"]],
        hide_index=True, width="stretch",
        column_config={
            "nome": "Código", "codigo": "Id", "recorte": "Recorte", "n": "Responderam",
            "k": "Com o código",
            "pct": st.column_config.NumberColumn("%", format="%.1f"),
            "margem_pp": st.column_config.NumberColumn("± margem (p.p.)", format="%.1f"),
        },
    )

with secao(2, "Exemplos", chave="abertas-exemplos"):
    nota("Textos anonimizados e aprovados. Para que um relato não possa ser ligado ao perfil de "
         "quem respondeu, os exemplos não seguem os filtros de perfil da barra lateral, só o grupo.")
    textos = pd.read_csv(csv_textos, dtype=str, keep_default_na=False) if csv_textos.exists() \
        else pd.DataFrame(columns=["item", "grupo", "codigos", "texto"])
    nomes = dict(zip(livro["codigo"], livro["nome"]))
    codigo_por_nome = {v: k for k, v in nomes.items()}
    escolhido = st.selectbox("Código", ordem)
    codigo = codigo_por_nome[escolhido]
    exemplos = textos[(textos["item"] == campo)
                      & textos["codigos"].map(lambda c: codigo in c.split(";"))]
    if exemplos.empty:
        st.write("Nenhum exemplo com este código.")
    for _, linha in exemplos.iterrows():
        grupo = ROTULOS_GRUPO.get(linha["grupo"], "Sem grupo (pendente)")
        citacao = "\n> ".join(linha["texto"].splitlines())
        st.markdown(f"> {citacao}\n\n— {grupo}")
