"""O que foi medido: os construtos (NIV, IMP, POS, PRA), as perguntas e os cenários."""

import html

import pandas as pd
import streamlit as st

from app import contexto
from app.componentes import cabecalho_pagina, nota, secao
from app.glossario import CENARIOS, CONSTRUTOS, LEITURA
from src.config import ENUNCIADOS, VINHETAS

ctx = contexto.obter()
cabecalho_pagina("O que foi medido", contexto=ctx)


def cartao(titulo: str, subtitulo: str, corpo: str) -> str:
    return (f"<div class='cartao-html'><h4>{titulo}</h4>"
            f"<p class='subtitulo'>{html.escape(subtitulo)}</p>{corpo}</div>")


# ---------------------------------------------------------------------------
# 1. Os quatro construtos e suas perguntas
# ---------------------------------------------------------------------------
with secao(1, "Construtos", chave="instrumento-construtos"):
    cartoes = []
    for c in CONSTRUTOS.values():
        itens = "".join(
            f"<li><span class='codigo'>{item}</span> {html.escape(ENUNCIADOS[item])}"
            + (" <span class='invertido'>invertido</span>" if item in c.invertidos else "") + "</li>"
            for item in c.itens
        )
        corpo = f"<ul class='itens'>{itens}</ul><p class='escala'>{html.escape(c.escala)}</p>"
        cartoes.append(cartao(f"<span class='sigla'>{c.sigla}</span> {html.escape(c.nome)}", c.mede, corpo))
    st.html(f"<div class='grade-cartoes'>{''.join(cartoes)}</div>")
    nota("Itens invertidos têm a escala virada antes do cálculo (6 − valor), para que um número "
         "maior signifique sempre mais dívida ou mais impacto.")

# ---------------------------------------------------------------------------
# 2. Os três cenários de POS e PRA
# ---------------------------------------------------------------------------
with secao(2, "Cenários de POS e PRA", chave="instrumento-cenarios"):
    cartoes = []
    for numero, (titulo, situacao, (deveria, acontece)) in enumerate(CENARIOS, start=1):
        opcoes = "".join(f"<li><span class='codigo'>{k}</span> {html.escape(texto)}</li>"
                         for k, texto in enumerate(VINHETAS[numero], start=1))
        corpo = (f"<ol class='itens opcoes'>{opcoes}</ol>"
                 f"<p class='escala'>{deveria}: o que a equipe <b>deveria</b> fazer (POS) · "
                 f"{acontece}: o que <b>normalmente acontece</b> (PRA)</p>")
        cartoes.append(cartao(f"Cenário {numero} · {html.escape(titulo)}", situacao, corpo))
    st.html(f"<div class='trio-cartoes'>{''.join(cartoes)}</div>")
    nota("As opções vão de 1 (prioriza a entrega) a 4 (prioriza pagar a dívida). As duas do meio "
         "são meios-termos, e não há ponto neutro.")

# ---------------------------------------------------------------------------
# 3. Como ler os escores
# ---------------------------------------------------------------------------
with secao(3, "Como ler os escores", chave="instrumento-leitura"):
    st.table(pd.DataFrame(LEITURA, columns=["Escore", "Cálculo", "Escala", "Leitura"]).set_index("Escore"))
    nota("O escore fica ausente quando mais da metade dos itens do construto é \"Não sei\".")
