"""Estado compartilhado entre a barra lateral (streamlit_app.py) e as páginas."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app.dados import Analise


@dataclass
class Contexto:
    nome_analise: str
    analise: Analise  # amostra completa (usar nos testes das RQs)
    filtrados: pd.DataFrame  # respostas válidas depois dos filtros da barra lateral
    filtros_ativos: list[str]
    sintetico: bool


def guardar(contexto: Contexto) -> None:
    st.session_state["contexto"] = contexto


def obter() -> Contexto:
    return st.session_state["contexto"]


def aviso_filtros(contexto: Contexto) -> None:
    """Mostra quantas respostas passam pelos filtros, nas páginas que os usam."""
    total = len(contexto.analise.dados)
    if contexto.filtros_ativos:
        st.info(
            f"Filtros ativos ({', '.join(contexto.filtros_ativos)}): "
            f"{len(contexto.filtrados)} de {total} respostas válidas."
        )
