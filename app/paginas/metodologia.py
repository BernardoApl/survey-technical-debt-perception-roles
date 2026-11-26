"""Metodologia e desvios (#12, Gabriel). Página reservada: substituir o conteúdo abaixo."""

import streamlit as st

from app import contexto

ctx = contexto.obter()
st.title("Metodologia e desvios")
st.caption(ctx.nome_analise)
st.info("Em construção (issue #12). Resumo do protocolo, desvios (o quê, por quê e impacto), incluindo a prorrogação da coleta de 22/11 para 25/11.")
