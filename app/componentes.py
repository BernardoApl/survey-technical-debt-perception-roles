"""Blocos visuais das páginas, no estilo do Lab04 (classes em app/estilo.css).

Exemplo de página:

    cabecalho_pagina("Itens Likert", "O que cada grupo respondeu em cada item.", ctx)
    with secao(1, "Nível percebido", chave="likert-niv"):
        mostrar(figura)
"""

from __future__ import annotations

import html

import streamlit as st


def cabecalho_pagina(titulo: str, descricao: str = "", contexto=None) -> None:
    """Título grande, texto de abertura opcional e uma linha com o período e os filtros ativos."""
    meta = []
    if contexto is not None:
        meta.append(f"<span>{html.escape(contexto.nome_analise)}</span>")
        if contexto.filtros_ativos:
            meta.append("<span class='sep'></span>")
            meta.append(f"<span>Filtros: <b>{html.escape(', '.join(contexto.filtros_ativos))}</b> · "
                        f"<b>{len(contexto.filtrados)}</b> de {len(contexto.analise.dados)} "
                        "respostas válidas</span>")
    st.html(
        f"""
        <header class="top">
          <span class="eyebrow">Survey · Dívida técnica por papel</span>
          <h1>{html.escape(titulo)}</h1>
          {f'<p class="lede">{html.escape(descricao)}</p>' if descricao else ''}
          <div class="meta">{''.join(meta)}</div>
        </header>
        """
    )


def secao(numero: int, titulo: str, chave: str | None = None):
    """Cabeçalho numerado da seção e o bloco do conteúdo (use com `with`).

    A seção não tem cartão: cada gráfico exibido com `mostrar` já fica no seu próprio cartão.
    """
    st.html(f"<div class='sec-head'><span class='sec-num'>{numero}</span>"
            f"<h2>{html.escape(titulo)}</h2></div>")
    return st.container(key=f"sec-{chave or numero}")


def nota(texto: str) -> None:
    """Texto pequeno e cinza (aceita HTML simples)."""
    st.html(f"<p class='nota'>{texto}</p>")


def pendente(texto: str) -> None:
    st.html(f"<div class='pending'><b>Pendente</b>{html.escape(texto)}</div>")
