"""Metodologia e desvios (#12): o que mudou em relação ao protocolo e por quê.

O texto dos desvios vem de DEVIATIONS.md e o das decisões de docs/decisoes-analise.md.
Estados e números vêm do CSV bruto, pelo mesmo cálculo do pipeline (src.pipeline.calcular).
"""

import html
import re

import streamlit as st

from app import contexto
from app.componentes import cabecalho_pagina, nota, secao
from app.dados import preparar_estudo
from app.graficos import fmt, margem
from app.metodologia_dados import (
    A_PREENCHER,
    A_RESOLVER,
    AMEACAS,
    NAO_OCORREU,
    OBJETIVO_GQM,
    PLANO,
    QUESTOES,
    estado,
    titulo_curto,
    ler_decisoes,
    ler_desvios,
)
from src.config import META_GESTAO, MINIMO_GESTAO

ctx = contexto.obter()
estudo = preparar_estudo()
calculados = estudo["desvios"]

cabecalho_pagina("Metodologia e desvios", contexto=ctx)

# ---------------------------------------------------------------------------
# 1. O estudo em resumo (protocolo pré-registrado em 12/11/2026)
# ---------------------------------------------------------------------------
with secao(1, "O estudo pré-registrado", chave="metodologia-protocolo"):
    # Um único bloco em grade: os dois cartões ficam lado a lado e com a mesma altura.
    gqm = "".join(f"<span class='rotulo'>{html.escape(rotulo)}</span><b>{html.escape(valor)}</b>"
                  for rotulo, valor in OBJETIVO_GQM)
    plano = "".join(f"<li><b>{html.escape(rotulo)}:</b> {html.escape(texto)}</li>" for rotulo, texto in PLANO)
    st.html(
        "<div class='par-cartoes'>"
        f"<div class='cartao-html'><h4>Objetivo (GQM)</h4><div class='gqm'>{gqm}</div></div>"
        f"<div class='cartao-html'><h4>Como o estudo foi planejado</h4><ul class='plano'>{plano}</ul></div>"
        "</div>"
    )
    st.table(QUESTOES.set_index("RQ"))
    nota("Resumo do protocolo pré-registrado em 12/11/2026 (planejamento_survey.pdf), "
         "antes da primeira resposta coletada.")

# ---------------------------------------------------------------------------
# 2. Desvios do protocolo
# ---------------------------------------------------------------------------
CLASSES = {A_RESOLVER: "resolver", A_PREENCHER: "preencher", NAO_OCORREU: "nao"}


def texto_html(texto: str) -> str:
    """Escapa o texto e transforma `trechos` em <code>, como no Markdown."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(texto))


# Só o que mudou de fato: regras condicionais que não foram acionadas nos dados não aparecem.
desvios, estados = [], []
for d in ler_desvios():
    situacao = estado(d, calculados)
    if situacao[0] != NAO_OCORREU:
        desvios.append(d)
        estados.append(situacao)

with secao(2, "O que mudou em relação ao protocolo", chave="metodologia-desvios"):
    nota("Estado recalculado a partir do CSV bruto. Texto completo em DEVIATIONS.md.")
    colunas = st.columns(2, gap="medium")
    for i, (desvio, (situacao, nos_dados)) in enumerate(zip(desvios, estados)):
        with colunas[i % 2], st.container(key=f"cartao-desvio-{i}"):
            classe = CLASSES.get(situacao, "ocorreu")
            st.html(
                f"<div class='cartao-topo'><h3>{html.escape(titulo_curto(desvio.titulo))}</h3>"
                f"<span class='estado estado-{classe}'>{html.escape(situacao)}</span></div>"
                f"<p class='campo'>{texto_html(desvio.resumo)}</p>"
                + (f"<div class='nos-dados'>{html.escape(nos_dados)}</div>" if nos_dados else "")
            )
            with st.expander("Detalhes"):
                st.html("".join(f"<p class='campo'><b>{rotulo}</b> {texto_html(texto)}</p>"
                                for rotulo, texto in (("O quê:", desvio.o_que), ("Por quê:", desvio.por_que),
                                                      ("Impacto:", desvio.impacto)) if texto))

# ---------------------------------------------------------------------------
# 3. Decisões que operacionalizam o protocolo
# ---------------------------------------------------------------------------
with secao(3, "Decisões tomadas antes da análise", chave="metodologia-decisoes"):
    decisoes = ler_decisoes()
    decisoes["Status"] = decisoes["Status"].replace({"Proposta": "Adotada (padrão)"})
    decisoes["Detalhe"] = (decisoes["Detalhe"].str.replace(r"^(sim|não)[,.]?\s*", "", regex=True)
                           .str.strip("() .").str.replace(r"[*`]", "", regex=True))
    st.table(decisoes.set_index("Nº"))
    nota("Escolhas que o protocolo deixava em aberto, fixadas antes de rodar os testes "
         "(docs/decisoes-analise.md). As que mudam o protocolo também aparecem na seção 2.")

# ---------------------------------------------------------------------------
# 4. Limitações e ameaças à validade
# ---------------------------------------------------------------------------
dados = ctx.analise.dados
n_validas = len(dados)
n_gestao = int((dados["grupo"] == "gestão").sum())
n_tecnico = int((dados["grupo"] == "técnico").sum())

with secao(4, "Limitações", chave="metodologia-limitacoes"):
    c1, c2, c3 = st.columns(3)
    c1.metric("Margem, amostra total", f"±{fmt(margem(n_validas))} p.p.", help=f"n = {n_validas}")
    c2.metric("Margem, técnicos", f"±{fmt(margem(n_tecnico))} p.p.", help=f"n = {n_tecnico}")
    c3.metric("Margem, gestão", f"±{fmt(margem(n_gestao))} p.p.", help=f"n = {n_gestao}")
    avisos = ["A amostra é por conveniência, concentrada na rede do grupo: os resultados valem "
              "para a amostra e não são generalizados para todos os profissionais do Brasil."]
    if n_gestao < MINIMO_GESTAO:
        avisos.append(f"Gestão abaixo do mínimo ({n_gestao} de {MINIMO_GESTAO}): poder muito baixo "
                      "nas comparações entre grupos; resultados exploratórios.")
    elif n_gestao < META_GESTAO:
        avisos.append(f"Gestão abaixo da meta ({n_gestao} de {META_GESTAO}).")
    abertas = estudo["pendencias_abertas"]
    pendentes = [
        f"{estudo['outro_pendentes']} papel(is) \"Outro\" sem classificação" if estudo["outro_pendentes"] else "",
        f"{abertas['anonimizacao']} texto(s) aberto(s) aguardando anonimização" if abertas.get("anonimizacao") else "",
        f"{abertas['consenso']} divergência(s) de codificação sem consenso" if abertas.get("consenso") else "",
    ]
    if any(pendentes):
        avisos.append("Pendências humanas (#5): " + "; ".join(p for p in pendentes if p) + ".")
    for aviso in avisos:
        st.markdown(f"- {aviso}")
    st.table(AMEACAS.set_index("Ameaça"))
    nota("Ameaças previstas no protocolo (Seção 7; Kitchenham e Pfleeger, 2008; Wohlin et al., 2012).")
