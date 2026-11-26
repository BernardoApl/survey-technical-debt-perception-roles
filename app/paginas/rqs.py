"""Questões de pesquisa (#11, Bernardo). Página reservada: substituir o conteúdo abaixo."""

import streamlit as st

from app import contexto

ctx = contexto.obter()
st.title("Questões de pesquisa")
st.caption(ctx.nome_analise)
st.info("Em construção (issue #11). Uma seção por RQ com pergunta, H0, gráfico, teste, p bruto, p Holm, tamanho de efeito e margem de erro. Usa sempre a amostra completa (ctx.analise.dados), sem filtros.")
