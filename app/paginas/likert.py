"""Itens Likert (#10, Gabriel). Página reservada: substituir o conteúdo abaixo."""

import streamlit as st

from app import contexto

ctx = contexto.obter()
st.title("Itens Likert")
st.caption(ctx.nome_analise)
st.info("Em construção (issue #10). Barras divergentes de C1–C4 e D1–D4, com % de concordância e margem de erro, total e por grupo. Respeita os filtros (use ctx.filtrados).")
