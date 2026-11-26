"""Confiabilidade dos construtos e validade convergente (#10).

Todos os números vêm de src.reliability (as mesmas funções de
outputs/confiabilidade.csv, confiabilidade_itens.csv e validade_convergente.csv).
Usa sempre a amostra válida completa: a qualidade da medida não muda com os filtros.
"""

import math

import streamlit as st

from app import contexto
from app.componentes import cabecalho_pagina, nota, secao
from app.graficos import alfa_com_ic, fmt, mostrar
from src.config import META_ALFA
from src.reliability import confiabilidade, validade_convergente

NOMES = {
    "NIV": "Nível percebido (NIV)",
    "IMP": "Impacto percebido (IMP)",
    "POS": "Postura (POS)",
    "PRA": "Prática percebida (PRA)",
}
VINHETAS = {"POS", "PRA"}


def fmt_p(p: float) -> str:
    if math.isnan(p):
        return "—"
    return "< 0,001" if p < 0.001 else fmt(p, 3)


def fmt_num(x: float, casas: int = 2) -> str:
    return "—" if x is None or math.isnan(x) else fmt(x, casas)


ctx = contexto.obter()
cabecalho_pagina(
    "Confiabilidade",
    "Se os itens de cada construto medem a mesma coisa (alfa de Cronbach) e se os escores "
    "andam junto com medidas parecidas (validade convergente).",
    ctx,
)
dados = ctx.analise.dados
nota("Esta página usa sempre a <b>amostra válida completa</b>: os filtros da barra lateral não "
     f"se aplicam ({len(dados)} respostas).")

alfa, alfa_itens = confiabilidade(dados)
validade = validade_convergente(dados)

# ---------------------------------------------------------------------------
# 1. Alfa de Cronbach com IC 95% e a meta
# ---------------------------------------------------------------------------
with secao(1, "Alfa de Cronbach", chave="conf-alfa"):
    nota(f"Meta do protocolo: α ≥ {fmt(META_ALFA, 2)} (Seção 5.3). O alfa usa só as respostas com "
         "todos os itens do construto respondidos; C4 e D2 entram invertidos. "
         "IC 95% pela distribuição F (Feldt).")
    if alfa["alfa"].notna().any():
        mostrar(alfa_com_ic(alfa, META_ALFA, NOMES))
    tabela = alfa.assign(
        nome=alfa["construto"].map(NOMES),
        alfa=alfa["alfa"].round(3),
        ic95=[f"{fmt_num(i)} a {fmt_num(s)}"
              for i, s in zip(alfa["ic95_inferior"], alfa["ic95_superior"])],
        meta=alfa["atinge_meta"].map({True: "sim", False: "não"}).fillna("—"),
    )[["nome", "construto", "itens", "n", "excluidas", "alfa", "ic95", "meta"]]
    st.dataframe(
        tabela, hide_index=True, width="stretch",
        column_config={
            "nome": "Construto", "construto": "Sigla", "itens": "Itens",
            "n": st.column_config.NumberColumn("n", help="Respostas com todos os itens"),
            "excluidas": st.column_config.NumberColumn(
                "Fora do cálculo", help="Respostas com algum \"Não sei\" nos itens do construto"),
            "alfa": st.column_config.NumberColumn("α", format="%.3f"),
            "ic95": "IC 95%", "meta": f"α ≥ {fmt(META_ALFA, 2)}",
        },
    )

    abaixo = alfa[alfa["atinge_meta"].eq(False)]
    vinhetas_abaixo = [c for c in abaixo["construto"] if c in VINHETAS]
    likert_abaixo = [c for c in abaixo["construto"] if c not in VINHETAS]
    if likert_abaixo:
        st.warning(
            f"Abaixo da meta: {', '.join(NOMES[c] for c in likert_abaixo)}. Pelo protocolo "
            "(Seção 5.3), o item problemático é revisto, e isso é declarado como desvio em "
            "DEVIATIONS.md. A seção 2 mostra qual item mais baixa o alfa."
        )
    if vinhetas_abaixo:
        st.warning(
            f"Abaixo da meta: {', '.join(NOMES[c] for c in vinhetas_abaixo)}. Pelo protocolo "
            "(Seção 5.3) e pela decisão 8 (docs/decisoes-analise.md), a RQ3 também é analisada "
            "por cenário, como análise exploratória fora da correção de Holm, e isso é declarado "
            "como desvio em DEVIATIONS.md."
        )
    if alfa["alfa"].isna().any():
        st.info("Sem alfa para "
                + ", ".join(NOMES[c] for c in alfa.loc[alfa["alfa"].isna(), "construto"])
                + ": poucas respostas completas ou soma sem variação.")

# ---------------------------------------------------------------------------
# 2. Alfa se o item for removido
# ---------------------------------------------------------------------------
with secao(2, "Alfa se o item for removido", chave="conf-itens"):
    nota("Se tirar um item <b>aumenta</b> o alfa, esse item mede algo diferente dos outros. "
         "A correlação item-total corrigida compara o item com a soma dos demais; valores baixos "
         "ou negativos apontam o mesmo problema. Mesmas respostas do alfa da seção 1.")
    alfa_de = alfa.set_index("construto")["alfa"]
    itens = alfa_itens.assign(
        nome=alfa_itens["construto"].map(NOMES),
        alfa_construto=alfa_itens["construto"].map(alfa_de).round(3),
        alfa_sem_item=alfa_itens["alfa_sem_item"].round(3),
        diferenca=(alfa_itens["alfa_sem_item"] - alfa_itens["construto"].map(alfa_de)).round(3),
        r_item_total=alfa_itens["r_item_total"].round(3),
    )
    itens["aumenta"] = itens["diferenca"].gt(0)
    st.dataframe(
        itens[["nome", "item", "n", "alfa_construto", "alfa_sem_item", "diferenca", "aumenta",
               "r_item_total"]],
        hide_index=True, width="stretch",
        column_config={
            "nome": "Construto", "item": "Item", "n": "n",
            "alfa_construto": st.column_config.NumberColumn("α do construto", format="%.3f"),
            "alfa_sem_item": st.column_config.NumberColumn("α sem o item", format="%.3f"),
            "diferenca": st.column_config.NumberColumn("Diferença", format="%+.3f"),
            "aumenta": st.column_config.CheckboxColumn("Remover aumenta α"),
            "r_item_total": st.column_config.NumberColumn("r item-total", format="%.3f"),
        },
    )

# ---------------------------------------------------------------------------
# 3. Validade convergente
# ---------------------------------------------------------------------------
DESCRICAO = {
    "NIV × C5": "Nível percebido (NIV) e a nota de 0 a 10 para a dívida técnica do projeto (C5)",
    "PRA × E7": "Prática percebida (PRA) e a frequência com que a equipe reduz dívida técnica (E7)",
}
with secao(3, "Validade convergente", chave="conf-validade"):
    nota("Correlação de Spearman (bilateral). Espera-se ρ <b>positivo</b> nos dois pares "
         "(protocolo, Seção 5.3). Estes dois testes ficam <b>fora</b> da correção de Holm dos "
         "14 testes das questões de pesquisa (Seção 5.6).")
    colunas = st.columns(len(validade))
    for coluna, (_, linha) in zip(colunas, validade.iterrows()):
        with coluna:
            st.metric(f"ρ {linha['par']}", fmt_num(linha["rho"]),
                      help=DESCRICAO.get(linha["par"], linha["par"]))
            st.caption(f"n = {linha['n']} · p = {fmt_p(linha['p_valor'])}")
            if math.isnan(linha["rho"]):
                st.caption("Sem pares suficientes para calcular.")
            elif linha["rho"] > 0 and linha["p_valor"] < 0.05:
                st.caption("Positiva e significativa a 5%, como esperado.")
            elif linha["rho"] > 0:
                st.caption("Positiva, mas não significativa a 5%.")
            else:
                st.caption("Não é positiva: não confirma a validade convergente.")
    st.dataframe(
        validade.assign(rho=validade["rho"].round(3), p_valor=validade["p_valor"].round(4))
        [["par", "n", "rho", "p_valor"]],
        hide_index=True, width="stretch",
        column_config={
            "par": "Par", "n": "n",
            "rho": st.column_config.NumberColumn("ρ de Spearman", format="%.3f"),
            "p_valor": st.column_config.NumberColumn("p (bilateral)", format="%.4f"),
        },
    )
