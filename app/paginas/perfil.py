"""Perfil da amostra: recebidas, descartes com motivo e distribuição do perfil (#9)."""

import pandas as pd
import plotly.express as px
import streamlit as st

from app import contexto
from app.filtros import ROTULOS_ORDINAIS, rotular
from src.clean import ETAPAS
from src.config import OPCOES_B6, PAPEIS_GESTAO, PAPEIS_TECNICOS

ctx = contexto.obter()
resumo = ctx.analise.resumo
log = ctx.analise.log

st.title("Perfil da amostra")
st.caption(ctx.nome_analise)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Respostas recebidas", resumo["recebidas"])
c2.metric("Descartadas", resumo["descartadas"])
c3.metric("Válidas", resumo["validas"])
c4.metric("Válidas com os filtros", len(ctx.filtrados))

st.subheader("Descartes")
st.caption("Cada resposta descartada recebe só o motivo da primeira etapa em que falhou "
           "(protocolo, Seção 5.1). Os filtros não se aplicam aos descartes.")
por_etapa = pd.DataFrame(
    [{"Etapa": int(rotulo.split(" - ")[0]), "Critério": rotulo.split(" - ", 1)[1], "Respostas": n}
     for rotulo, n in resumo["descartes_por_etapa"].items()]
)
st.dataframe(por_etapa, hide_index=True, width="stretch")

descartes = log[log["descartada"]].drop(columns="descartada")
with st.expander(f"Motivo de cada descarte ({len(descartes)})"):
    if descartes.empty:
        st.write("Nenhuma resposta descartada.")
    else:
        st.dataframe(
            descartes.rename(columns={"resp_id": "Resposta", "etapa": "Etapa", "motivo": "Motivo"}),
            hide_index=True, width="stretch",
        )

ausentes = log[~log["descartada"]]
if not ausentes.empty:
    st.info(
        f"{ETAPAS[6].capitalize()}: {len(ausentes)} caso(s) com mais de 50% de \"Não sei\" "
        "em um construto. A resposta continua válida; só o escore daquele construto fica ausente."
    )
    st.dataframe(
        ausentes[["resp_id", "motivo"]].rename(columns={"resp_id": "Resposta", "motivo": "Motivo"}),
        hide_index=True,
    )

if resumo["outro_pendentes"]:
    st.warning(
        f"{len(resumo['outro_pendentes'])} papel(is) digitado(s) em \"Outro\" ainda sem "
        "classificação (issue #5). Essas respostas ficam sem grupo."
    )

st.subheader("Perfil das respostas válidas")
contexto.aviso_filtros(ctx)
dados = ctx.filtrados
if dados.empty:
    st.warning("Nenhuma resposta passa pelos filtros escolhidos.")
    st.stop()


def papel_publico(b2: pd.Series) -> pd.Series:
    """Cargo digitado em "Outro" é texto livre do respondente: aparece só como "Outro"."""
    return b2.where(b2.isin(PAPEIS_TECNICOS + PAPEIS_GESTAO), "Outro")


def barras(serie: pd.Series, titulo: str, ordem: list[str] | None = None) -> None:
    contagem = serie.fillna("Sem grupo (pendente)").value_counts()
    if ordem:
        contagem = contagem.reindex([o for o in ordem if o in contagem.index]
                                    + [o for o in contagem.index if o not in ordem])
    tabela = pd.DataFrame({"Categoria": contagem.index, "Respostas": contagem.values})
    tabela["%"] = (100 * tabela["Respostas"] / tabela["Respostas"].sum()).round(1)
    figura = px.bar(
        tabela, x="Respostas", y="Categoria", orientation="h", text=tabela["%"].map("{:.1f}%".format),
        title=titulo, hover_data={"%": True},
    )
    figura.update_layout(yaxis={"categoryorder": "array", "categoryarray": tabela["Categoria"][::-1]},
                         yaxis_title=None, height=120 + 32 * len(tabela), margin={"t": 50, "b": 10})
    st.plotly_chart(figura, width="stretch")


barras(dados["grupo"], "Grupo de papel", ["técnico", "gestão"])
barras(papel_publico(dados["B2"]), "Papel principal (B2)", PAPEIS_TECNICOS + PAPEIS_GESTAO + ["Outro"])
esquerda, direita = st.columns(2)
with esquerda:
    barras(rotular(dados, "B3"), "Tempo de experiência em TI (B3)", ROTULOS_ORDINAIS["B3"])
    barras(rotular(dados, "B5"), "Funcionários da empresa (B5)", ROTULOS_ORDINAIS["B5"])
    barras(rotular(dados, "B7"), "Tamanho da equipe (B7)", ROTULOS_ORDINAIS["B7"])
with direita:
    barras(rotular(dados, "B4"), "Tempo na equipe atual (B4)", ROTULOS_ORDINAIS["B4"])
    barras(dados["B6"], "Tipo de empresa (B6)", OPCOES_B6)
    barras(dados["B8"].astype("Int64").astype(str),
           "Familiaridade com o termo dívida técnica (B8, 1 a 5)", ["1", "2", "3", "4", "5"])
