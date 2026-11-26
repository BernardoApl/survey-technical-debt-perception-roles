"""Perfil da amostra: tamanho com margem de erro, descartes e perfil por grupo (#9)."""

import pandas as pd
import streamlit as st

from app import contexto
from app.componentes import cabecalho_pagina, nota, secao
from app.filtros import ROTULOS_ORDINAIS, rotular
from app.graficos import (
    COR_VAGA_GESTAO,
    CORES_GRUPO,
    barras_perfil,
    caixa_de_unidades,
    fmt,
    funil_descartes,
    margem,
    mostrar,
    piramide_papeis,
)
from src.config import (
    META_GESTAO,
    META_VALIDAS,
    MINIMO_GESTAO,
    MINIMO_VALIDAS,
    OPCOES_B6,
    PAPEIS_GESTAO,
    PAPEIS_TECNICOS,
)

ctx = contexto.obter()
resumo = ctx.analise.resumo
log = ctx.analise.log
completos = ctx.analise.dados  # amostra válida completa (sem filtros)

cabecalho_pagina("Perfil da amostra", contexto=ctx)

# ---------------------------------------------------------------------------
# 1. Tamanho da amostra, com a margem de erro do protocolo (Seção 2)
# ---------------------------------------------------------------------------
n_validas = resumo["validas"]
n_tecnico = int((completos["grupo"] == "técnico").sum())
n_gestao = int((completos["grupo"] == "gestão").sum())

with secao(1, "Tamanho da amostra", chave="perfil-tamanho"):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recebidas", resumo["recebidas"],
              help="Todas as respostas exportadas do formulário, antes da limpeza.")
    c2.metric("Válidas", n_validas,
              help=f"Meta {META_VALIDAS}, mínimo {MINIMO_VALIDAS} (protocolo, Seção 2).")
    c3.metric("Técnicos", n_tecnico)
    c4.metric("Gestão", n_gestao,
              help=f"Meta {META_GESTAO}, mínimo {MINIMO_GESTAO} (protocolo, Seção 2).")
    c1.caption(f"{resumo['descartadas']} descartadas")
    c2.caption(f"margem ±{fmt(margem(n_validas))} p.p.")
    c3.caption(f"margem ±{fmt(margem(n_tecnico))} p.p.")
    c4.caption(f"margem ±{fmt(margem(n_gestao))} p.p.")
    nota("Margem de erro a 95% de uma proporção no pior caso (p = 0,5), pelo n de cada recorte. "
         "Como a amostra é por conveniência, a margem é indicativa (protocolo, Seção 2).")

# ---------------------------------------------------------------------------
# 2. Do formulário à análise: funil dos descartes
# ---------------------------------------------------------------------------
with secao(2, "Do formulário à análise", chave="perfil-funil"):
    esquerda, direita = st.columns([3, 2], gap="large")
    with esquerda:
        mostrar(funil_descartes(resumo))
    with direita:
        st.markdown("Cada resposta descartada recebe só o motivo da **primeira** etapa em que "
                    "falhou (protocolo, Seção 5.1). Os filtros da barra lateral não mudam esta parte.")
        descartes = log[log["descartada"]].drop(columns="descartada")
        with st.expander(f"Motivo de cada descarte ({len(descartes)})"):
            if descartes.empty:
                st.write("Nenhuma resposta descartada.")
            else:
                st.dataframe(descartes.rename(columns={"resp_id": "Resposta", "etapa": "Etapa",
                                                       "motivo": "Motivo"}),
                             hide_index=True, width="stretch")
        ausentes = log[~log["descartada"]]
        if not ausentes.empty:
            with st.expander(f"Construto sem escore ({len(ausentes)})"):
                st.caption("Mais de 50% de \"Não sei\" no construto: a resposta continua válida, "
                           "só aquele escore fica ausente.")
                st.dataframe(ausentes[["resp_id", "motivo"]].rename(
                    columns={"resp_id": "Resposta", "motivo": "Motivo"}), hide_index=True, width="stretch")
        if resumo["outro_pendentes"]:
            st.warning(f"{len(resumo['outro_pendentes'])} papel(is) digitado(s) em \"Outro\" ainda sem "
                       "classificação (issue #5). Essas respostas ficam sem grupo.")

dados = ctx.filtrados
if dados.empty:
    st.warning("Nenhuma resposta válida passa pelos filtros escolhidos.")
    st.stop()

# ---------------------------------------------------------------------------
# 3. Técnicos e gestores: um quadrado por pessoa
# ---------------------------------------------------------------------------
with secao(3, "Técnicos e gestores", chave="perfil-grupos"):
    caixa, legenda = st.columns([2, 3], gap="large")
    with caixa:
        mostrar(caixa_de_unidades(dados["grupo"], META_GESTAO))
    with legenda:
        contagem = dados["grupo"].fillna("sem grupo").value_counts()
        total = int(contagem.sum())
        n_g = int(contagem.get("gestão", 0))
        itens = [("técnico", "Técnicos"), ("gestão", "Gestão"), ("sem grupo", "Sem grupo (pendente)")]
        linhas = [
            f"<span style='color:{CORES_GRUPO[chave]};font-size:1.3em'>■</span> "
            f"**{rotulo}**: {int(contagem.get(chave, 0))} ({fmt(100 * contagem.get(chave, 0) / total)}%)"
            for chave, rotulo in itens if contagem.get(chave, 0) or chave != "sem grupo"
        ]
        if n_g < META_GESTAO:
            linhas.append(f"<span style='color:{COR_VAGA_GESTAO};font-size:1.3em'>■</span> "
                          f"Faltam **{META_GESTAO - n_g}** para a meta de {META_GESTAO} de gestão")
        st.markdown("Cada quadrado é **uma resposta válida**.\n\n" + "  \n".join(linhas),
                    unsafe_allow_html=True)
        if n_g >= META_GESTAO:
            st.success(f"Meta de gestão atingida: {n_g} respostas (meta {META_GESTAO}, "
                       f"mínimo {MINIMO_GESTAO}).")
        elif n_g >= MINIMO_GESTAO:
            st.info(f"Mínimo de gestão atingido ({n_g} de {MINIMO_GESTAO}), abaixo da meta de {META_GESTAO}.")
        else:
            st.warning(f"Gestão abaixo do mínimo pré-registrado ({n_g} de {MINIMO_GESTAO}): "
                       "comparações entre grupos com poder muito baixo (protocolo, Seção 2).")

# ---------------------------------------------------------------------------
# 4. Papéis de cada lado
# ---------------------------------------------------------------------------
with secao(4, "Papel principal", chave="perfil-papeis"):
    papel = dados["B2"].where(dados["B2"].isin(PAPEIS_TECNICOS + PAPEIS_GESTAO), "Outro")
    mostrar(piramide_papeis(papel, dados["grupo"]))
    pendentes = int(dados["grupo"].isna().sum())
    if pendentes:
        nota(f"{pendentes} resposta(s) com papel \"Outro\" ainda sem grupo não aparecem aqui.")

# ---------------------------------------------------------------------------
# 5. Perfil das respostas válidas
# ---------------------------------------------------------------------------
perfis = [
    ("B3", "Tempo de experiência em TI (B3)", ROTULOS_ORDINAIS["B3"], True),
    ("B4", "Tempo na equipe atual (B4)", ROTULOS_ORDINAIS["B4"], True),
    ("B5", "Funcionários da empresa (B5)", ROTULOS_ORDINAIS["B5"], True),
    ("B6", "Tipo de empresa (B6)", OPCOES_B6, False),
    ("B7", "Tamanho da equipe (B7)", ROTULOS_ORDINAIS["B7"], True),
    ("B8", "Familiaridade com o termo dívida técnica (B8, 1 a 5)", ["1", "2", "3", "4", "5"], True),
]
with secao(5, "Perfil das respostas válidas", chave="perfil-perfil"):
    colunas = st.columns(2, gap="large")
    for i, (coluna, titulo, opcoes, ordinal) in enumerate(perfis):
        categoria = (dados[coluna].astype("Int64").astype(str) if coluna == "B8"
                     else rotular(dados, coluna))
        with colunas[i % 2]:
            mostrar(barras_perfil(pd.Series(categoria, index=dados.index), opcoes, titulo, ordinal))
