"""Confiabilidade (#10, Gabriel). Página reservada: substituir o conteúdo abaixo."""

import streamlit as st

from app import contexto

ctx = contexto.obter()
st.title("Confiabilidade")
st.caption(ctx.nome_analise)
st.info("Em construção (issue #10). Alfa de Cronbach de NIV, IMP, POS e PRA com IC 95%, meta de 0,70, alfa se o item for removido e validade convergente.")
