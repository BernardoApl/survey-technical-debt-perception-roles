"""Gráficos do dashboard (Plotly) e cores fixas.

Técnico × gestão têm as mesmas cores em todas as páginas. Use `mostrar(figura)`
para exibir: ele aplica o tema do projeto (o do Lab04), vírgula decimal e
esconde a barra de ferramentas. Coloque os gráficos dentro de `secao(...)`.
"""

from __future__ import annotations

import itertools
import math

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Tons suaves, que convivem com o fundo nos temas claro e escuro.
CORES_GRUPO = {"técnico": "#7AA2D6", "gestão": "#E0A07A", "sem grupo": "#8A8F98"}
ROTULOS_GRUPO = {"técnico": "Técnico", "gestão": "Gestão", "sem grupo": "Sem grupo (pendente)"}
# Categorias ordenadas (do menor ao maior): tons de um mesmo cinza-azulado.
SEQUENCIAL = ["#DCE3EC", "#B4C1D3", "#8597B0", "#56698A", "#2F3F5C"]
# Categorias sem ordem (ex.: tipo de empresa).
QUALITATIVA = ["#7C9CBF", "#E3B04B", "#8CBF88", "#C98BB9", "#E08E79", "#A1A1AA"]


def fmt(x: float, casas: int = 1) -> str:
    """Número no formato brasileiro: 1.234,5"""
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def margem(n: int, p: float = 0.5) -> float:
    """Margem de erro a 95% de uma proporção, em pontos percentuais (protocolo, Seção 2)."""
    return 100 * 1.96 * math.sqrt(p * (1 - p) / n) if n else float("nan")


def _texto_legivel(cor: str) -> str:
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    return "#111113" if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "#ffffff"


FONTE = "Inter, system-ui, sans-serif"
COR_TEXTO = "#111113"
COR_SUAVE = "#6b6b76"
COR_GRADE = "#e7e7ea"

pio.templates["survey"] = go.layout.Template(
    layout=go.Layout(
        font={"family": FONTE, "size": 12, "color": COR_SUAVE},
        title={"font": {"family": FONTE, "size": 15, "color": COR_TEXTO}, "x": 0, "xanchor": "left"},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        xaxis={"gridcolor": COR_GRADE, "linecolor": COR_GRADE, "tickcolor": COR_GRADE,
               "zeroline": False, "fixedrange": True, "title": {"font": {"color": COR_SUAVE}}},
        yaxis={"gridcolor": COR_GRADE, "linecolor": COR_GRADE, "tickcolor": COR_GRADE,
               "zeroline": False, "fixedrange": True, "tickfont": {"color": COR_TEXTO}},
        hoverlabel={"font_family": FONTE, "bgcolor": "#ffffff", "bordercolor": COR_GRADE},
    )
)
pio.templates.default = "plotly_white+survey"


_contador = itertools.count()


def mostrar(figura: go.Figure) -> None:
    """Exibe a figura no seu próprio cartão branco, com o tema do projeto."""
    # Fundo explícito: o Streamlit preenche com a cor secundária do tema o que a figura não define.
    figura.update_layout(separators=",.", paper_bgcolor="#ffffff", plot_bgcolor="#ffffff")
    with st.container(key=f"grafico-{next(_contador)}"):
        st.plotly_chart(figura, theme=None, width="stretch", config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# Funil dos descartes
# ---------------------------------------------------------------------------
def funil_descartes(resumo: dict) -> go.Figure:
    """Recebidas -> cada etapa de descarte (só as que descartaram alguém) -> válidas."""
    rotulos, valores, textos = ["Recebidas"], [resumo["recebidas"]], [str(resumo["recebidas"])]
    restantes = resumo["recebidas"]
    for etapa, n in resumo["descartes_por_etapa"].items():
        if not n:
            continue
        restantes -= n
        rotulos.append(f"− {etapa.split(' - ', 1)[1]}")
        valores.append(restantes)
        textos.append(f"{restantes}  (−{n})")
    rotulos.append("Válidas")
    valores.append(resumo["validas"])
    textos.append(str(resumo["validas"]))

    cores = ["#56698A"] + ["#B4C1D3"] * (len(valores) - 2) + ["#2F3F5C"]
    figura = go.Figure(go.Funnel(
        y=rotulos, x=valores, text=textos, textinfo="text", textposition="inside",
        marker={"color": cores}, connector={"line": {"width": 0}, "fillcolor": "rgba(150,160,180,.15)"},
        textfont={"color": [_texto_legivel(c) for c in cores]},
        hovertemplate="%{y}: %{x} respostas<extra></extra>",
    ))
    figura.update_layout(height=70 + 44 * len(rotulos), margin={"l": 0, "r": 0, "t": 10, "b": 10})
    return figura


# ---------------------------------------------------------------------------
# Quadradinhos: uma grande caixa em que cada quadrado é uma pessoa
# ---------------------------------------------------------------------------
COR_VAGA_GESTAO = "#F2DCCB"  # areia clara: quanto falta para a meta de gestão


def caixa_de_unidades(grupo: pd.Series, meta_gestao: int, colunas: int = 10) -> go.Figure:
    """Grade com um quadrado por resposta válida, preenchida linha a linha.

    Ordem: técnicos, gestores, as vagas que faltam para a meta de gestão (em
    laranja claro) e, por último, quem ainda está sem grupo.
    """
    contagem = grupo.fillna("sem grupo").value_counts()
    n_gestao = int(contagem.get("gestão", 0))
    blocos = [
        (0, int(contagem.get("técnico", 0)), "Técnico"),
        (1, n_gestao, "Gestão"),
        (2, max(meta_gestao - n_gestao, 0), f"Falta para a meta de {meta_gestao} de gestão"),
        (3, int(contagem.get("sem grupo", 0)), "Sem grupo (pendente)"),
    ]
    celulas = [(valor, rotulo) for valor, n, rotulo in blocos for _ in range(n)]
    linhas = max(1, math.ceil(len(celulas) / colunas))
    z = [[None] * colunas for _ in range(linhas)]
    texto = [[""] * colunas for _ in range(linhas)]
    for k, (valor, rotulo) in enumerate(celulas):
        z[k // colunas][k % colunas] = valor
        texto[k // colunas][k % colunas] = rotulo

    cores = [CORES_GRUPO["técnico"], CORES_GRUPO["gestão"], COR_VAGA_GESTAO, CORES_GRUPO["sem grupo"]]
    escala = []
    for k, cor in enumerate(cores):  # escala em degraus: um valor inteiro = uma cor
        escala += [[k / len(cores), cor], [(k + 1) / len(cores), cor]]
    figura = go.Figure(go.Heatmap(
        z=z, text=texto, zmin=-0.5, zmax=len(cores) - 0.5, colorscale=escala, showscale=False,
        xgap=4, ygap=4, hoverongaps=False, hovertemplate="%{text}<extra></extra>",
    ))
    figura.update_layout(
        height=40 + 34 * linhas, margin={"l": 0, "r": 0, "t": 10, "b": 10},
        xaxis={"visible": False, "constrain": "domain"},
        yaxis={"visible": False, "autorange": "reversed", "scaleanchor": "x", "constrain": "domain"},
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figura


# ---------------------------------------------------------------------------
# Papéis: técnicos à esquerda, gestores à direita
# ---------------------------------------------------------------------------
NOMES_CURTOS = {"Desenvolvedor(a) (front-end, back-end, mobile ou full stack)": "Desenvolvedor(a)"}


def piramide_papeis(papel: pd.Series, grupo: pd.Series) -> go.Figure:
    """Cada lado ordenado do papel mais frequente para o menos frequente."""
    tabela = pd.DataFrame({"papel": papel.map(lambda p: NOMES_CURTOS.get(p, p)), "grupo": grupo})
    lados = {
        g: tabela[tabela["grupo"] == g]["papel"].value_counts()
        for g in ("técnico", "gestão")
    }
    linhas = max(len(lados["técnico"]), len(lados["gestão"]), 1)
    maior = max([s.max() for s in lados.values() if len(s)] + [1])

    figura = go.Figure()
    for chave, sinal, lado_texto in (("técnico", -1, "outside"), ("gestão", 1, "outside")):
        serie = lados[chave]
        figura.add_bar(
            y=list(range(len(serie))), x=[sinal * v for v in serie.values], orientation="h",
            marker_color=CORES_GRUPO[chave], showlegend=False, width=0.7,
            text=[f"{nome} · {v}" for nome, v in serie.items()], textposition=lado_texto,
            cliponaxis=False,
            hovertemplate=[f"{nome}: {v}<extra>{ROTULOS_GRUPO[chave]}</extra>" for nome, v in serie.items()],
        )
    passo = max(1, math.ceil(maior / 4))
    ticks = list(range(-passo * 4, passo * 4 + 1, passo))
    limite = maior * 2.1
    figura.update_layout(
        barmode="overlay", height=90 + 34 * linhas, margin={"l": 10, "r": 10, "t": 36, "b": 10},
        xaxis={"range": [-limite, limite], "tickvals": ticks, "ticktext": [str(abs(t)) for t in ticks],
               "zeroline": True, "zerolinewidth": 1.5, "title": None},
        yaxis={"autorange": "reversed", "visible": False},
    )
    for x, texto, cor in ((-limite, "◀ Técnicos", CORES_GRUPO["técnico"]),
                          (limite, "Gestores ▶", CORES_GRUPO["gestão"])):
        figura.add_annotation(x=x, y=-0.9, text=f"<b>{texto}</b>", showarrow=False,
                              xanchor="left" if x < 0 else "right", font={"color": cor, "size": 13})
    return figura


# ---------------------------------------------------------------------------
# Barras do perfil: uma barra por categoria, cada uma na sua cor
# ---------------------------------------------------------------------------
def paleta_categorias(n: int, ordinal: bool) -> list[str]:
    """Tons de cinza-azulado (claro -> escuro) para categorias ordenadas; cores distintas sem ordem."""
    if not ordinal:
        return QUALITATIVA[:n]
    passo = (len(SEQUENCIAL) - 1) / max(n - 1, 1)
    return [SEQUENCIAL[round(i * passo)] for i in range(n)]


def barras_perfil(categoria: pd.Series, opcoes: list[str], titulo: str,
                  ordinal: bool = True) -> go.Figure:
    """Barras horizontais com o número de respostas por categoria e o rótulo "n (x%)"."""
    contagem = categoria.value_counts()
    ordem = [o for o in opcoes if o in contagem.index] + [o for o in contagem.index if o not in opcoes]
    contagem = contagem.reindex(ordem)
    total = contagem.sum()
    figura = go.Figure(go.Bar(
        y=ordem, x=contagem.values, orientation="h",
        marker_color=paleta_categorias(len(ordem), ordinal), marker_line={"width": 0},
        text=[f"{n} ({fmt(100 * n / total)}%)" for n in contagem.values], textposition="outside",
        cliponaxis=False, hovertemplate="%{y}: %{x} respostas<extra></extra>",
    ))
    figura.update_layout(
        title=titulo, height=120 + 32 * len(ordem), margin={"t": 50, "b": 10, "r": 80},
        yaxis={"type": "category", "categoryorder": "array", "categoryarray": ordem[::-1],
               "title": None},
        xaxis={"title": "Respostas", "range": [0, contagem.max() * 1.25]},
    )
    return figura
