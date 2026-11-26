"""Preparação de resultados agregados para a página de questões de pesquisa."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from app.graficos import CORES_GRUPO
from src.config import OPCOES_B3, OPCOES_B5
from src.describe import frequencias, resumo_escores
from src.testes_rq import testes_rq

GRUPOS = ("técnico", "gestão")
METRICAS = {
    "RQ1": [("M1", "NIV"), ("M2", "C5")],
    "RQ2": [("M4", "IMP")],
    "RQ3": [("M6", "POS"), ("M7", "PRA"), ("M8", "DIST")],
}


def preparar(dados: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Recebe a amostra completa; nunca utiliza o recorte dos filtros."""
    return {"testes": testes_rq(dados), "frequencias": frequencias(dados),
            "escores": resumo_escores(dados)}


def conclusao(linha: pd.Series) -> str:
    """Descreve apenas o teste associado, sem inferir igualdade nem causalidade."""
    nome = f"{linha['variavel']} × {linha['comparacao']}"
    if pd.isna(linha["p_holm"]):
        return f"{nome}: teste não executável — {linha['motivo'] or 'p-valor indisponível'}."
    if linha["p_holm"] <= 0.05:
        return f"{nome}: evidência contra H0 após ajuste de Holm (p ajustado = {linha['p_holm']:.4f})."
    return f"{nome}: não houve evidência suficiente para rejeitar H0 após Holm (p ajustado = {linha['p_holm']:.4f})."


def tabela_testes(testes: pd.DataFrame, rq: str) -> pd.DataFrame:
    colunas = {"id": "ID", "variavel": "Variável", "comparacao": "Comparação",
               "teste": "Teste", "estatistica_nome": "Estatística", "estatistica": "Valor",
               "p_bruto": "p bruto", "p_holm": "p Holm", "efeito_nome": "Efeito",
               "efeito": "Valor do efeito", "n": "n total", "n_tecnico": "n técnico",
               "n_gestao": "n gestão", "n_sem_grupo": "n sem grupo",
               "margem_tecnico_pp": "Margem técnico (p.p.)",
               "margem_gestao_pp": "Margem gestão (p.p.)", "motivo": "Motivo de não execução"}
    return testes.loc[testes.rq.eq(rq), list(colunas)].rename(columns=colunas).reset_index(drop=True)


def figura_escores(escores: pd.DataFrame, metricas: list[tuple[str, str]]) -> go.Figure:
    fig = go.Figure()
    for grupo in GRUPOS:
        linhas = escores[(escores.recorte == grupo)].set_index("escore")
        fig.add_bar(name=grupo.capitalize(), x=[f"{m} · {v}" for m, v in metricas],
                    y=[linhas.loc[v, "mediana"] for _, v in metricas],
                    customdata=[[linhas.loc[v, "n"], linhas.loc[v, "iqr"]] for _, v in metricas],
                    marker_color=CORES_GRUPO[grupo],
                    hovertemplate="%{x}<br>Mediana: %{y}<br>n: %{customdata[0]}<br>IQR: %{customdata[1]}<extra>%{fullData.name}</extra>")
    fig.update_layout(barmode="group", yaxis_title="Mediana", height=300, margin=dict(t=25, b=30))
    return fig


def tabela_proporcoes(freq: pd.DataFrame, item: str) -> pd.DataFrame:
    f = freq[(freq.item == item) & freq.recorte.isin(["total", *GRUPOS])].copy()
    return f[["opcao", "recorte", "k", "n", "pct", "margem_pp"]].rename(columns={
        "opcao": "Resposta", "recorte": "Grupo", "k": "k", "n": "n", "pct": "%",
        "margem_pp": "Margem (p.p.)"}).reset_index(drop=True)


def figura_proporcoes(freq: pd.DataFrame, item: str) -> go.Figure:
    f = freq[(freq.item == item) & freq.recorte.isin(GRUPOS)].copy()
    fig = go.Figure()
    for grupo in GRUPOS:
        sub = f[f.recorte.eq(grupo)]
        fig.add_bar(name=grupo.capitalize(), y=sub.opcao, x=sub.pct, orientation="h",
                    marker_color=CORES_GRUPO[grupo], customdata=sub[["k", "n", "margem_pp"]],
                    hovertemplate="%{y}<br>%{x:.1f}% ± %{customdata[2]:.1f} p.p.<br>%{customdata[0]}/%{customdata[1]}<extra>%{fullData.name}</extra>")
    fig.update_layout(barmode="group", xaxis_title="Percentual (%)", yaxis_title=None,
                      height=max(280, 90 + 45 * f.opcao.nunique()), margin=dict(t=25, l=10, r=20, b=35))
    return fig


def figura_rq4(dados: pd.DataFrame, variavel: str) -> go.Figure:
    """Medianas agregadas dos construtos por faixa ordinal; não expõe respostas individuais."""
    opcoes = OPCOES_B3 if variavel == "B3" else OPCOES_B5
    fig = go.Figure()
    for escore, cor in (("NIV", "#567DAF"), ("IMP", "#D88D64"), ("POS", "#709775")):
        sub = dados[[variavel, escore]].dropna().groupby(variavel)[escore].agg(["median", "count"])
        fig.add_scatter(x=opcoes, y=[sub.loc[i, "median"] if i in sub.index else None
                                     for i in range(1, len(opcoes) + 1)],
                        customdata=[int(sub.loc[i, "count"]) if i in sub.index else 0
                                    for i in range(1, len(opcoes) + 1)],
                        name=escore, mode="lines+markers", line=dict(color=cor),
                        hovertemplate="%{x}<br>Mediana: %{y}<br>n: %{customdata}<extra>%{fullData.name}</extra>")
    fig.update_layout(yaxis_title="Mediana do escore", height=340, margin=dict(t=25, b=55),
                      xaxis_title="Experiência em TI" if variavel == "B3" else "Porte da empresa")
    return fig
