"""Dashboard público a partir de tabelas agregadas, sem CSV bruto."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.graficos import barras_divergentes, mostrar
from app.rqs_dados import (METRICAS, conclusao, figura_escores, figura_proporcoes,
                           tabela_proporcoes, tabela_testes)
from src.config import ENUNCIADOS, ITENS_CONSTRUTO, MINIMO_GESTAO, OPCOES_B3, OPCOES_B5, RAIZ

ARQUIVO_PUBLICO = RAIZ / "data" / "publico" / "resultados.json"
RQS = {
    "RQ1": ("Nível percebido", "Técnicos e gestores percebem o mesmo nível de dívida técnica?",
            "O nível percebido (NIV) não difere entre papéis."),
    "RQ2": ("Impacto percebido", "A percepção do impacto da dívida técnica difere entre papéis?",
            "O impacto percebido (IMP) não difere entre papéis."),
    "RQ3": ("Priorização e prática", "Como a dívida técnica deveria ser priorizada e como é tratada na prática?",
            "Postura, prática percebida, frequência e quem decide não diferem entre papéis; postura não difere da prática."),
    "RQ4": ("Experiência e porte", "A percepção está associada à experiência e ao porte da empresa?",
            "Não há correlação entre nível, impacto ou postura e experiência ou porte."),
}
ITENS = {
    "RQ1": ["C1", "C2", "C3", "C4", "C5", "C6"],
    "RQ2": ["D1", "D2", "D3", "D4", "D5"],
    "RQ3": ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"],
    "RQ4": ["B3", "B5", "C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4", "E1", "E3", "E5"],
}


def _figura_rq4(tabela: pd.DataFrame, variavel: str) -> go.Figure:
    opcoes = OPCOES_B3 if variavel == "B3" else OPCOES_B5
    fig = go.Figure()
    for escore, cor in (("NIV", "#567DAF"), ("IMP", "#D88D64"), ("POS", "#709775")):
        sub = tabela[(tabela.variavel == variavel) & (tabela.escore == escore)].set_index("categoria")
        fig.add_scatter(x=opcoes, y=[sub.loc[i, "mediana"] if i in sub.index else None
                                     for i in range(1, len(opcoes) + 1)],
                        customdata=[int(sub.loc[i, "n"]) if i in sub.index else 0
                                    for i in range(1, len(opcoes) + 1)],
                        name=escore, mode="lines+markers", line=dict(color=cor),
                        hovertemplate="%{x}<br>Mediana: %{y}<br>n: %{customdata}<extra>%{fullData.name}</extra>")
    fig.update_layout(yaxis_title="Mediana do escore", height=340, margin=dict(t=25, b=55))
    return fig


def _rqs(d: dict, rq_selecionada: str, controles) -> None:
    freq = pd.DataFrame(d["frequencias"])
    escores = pd.DataFrame(d["escores_por_grupo"])
    testes = pd.DataFrame(d["testes_rq"])
    st.title("Questões de pesquisa")
    st.caption("Margens de erro a 95% são indicativas, pois a amostra é por conveniência.")
    for rq, (titulo, pergunta, h0) in RQS.items():
        if rq != rq_selecionada:
            continue
        st.header(f"{rq} · {titulo}")
        st.markdown(f"**Pergunta:** {pergunta}  \n**H0:** {h0}")
        if rq in METRICAS:
            mostrar(figura_escores(escores, METRICAS[rq]))
        itens = {"RQ1": [("C6", "M3 · Tipos de dívida técnica")],
                 "RQ2": [("D5", "M5 · Maior efeito")],
                 "RQ3": [("E7", "M9 · Frequência"), ("E8", "M10 · Quem decide")]}.get(rq, [])
        for item, nome in itens:
            st.subheader(nome)
            mostrar(figura_proporcoes(freq, item))
            with st.expander(f"Ver proporções e margens · {item}"):
                st.dataframe(tabela_proporcoes(freq, item), hide_index=True, width="stretch")
        if rq == "RQ4":
            agrupados = pd.DataFrame(d["rq4_medianas"], columns=["variavel", "escore", "categoria", "n", "mediana"])
            for variavel in ("B3", "B5"):
                st.subheader("Experiência" if variavel == "B3" else "Porte da empresa")
                mostrar(_figura_rq4(agrupados, variavel))
        st.markdown("**Testes previstos e conclusões por comparação**")
        st.dataframe(tabela_testes(testes, rq), hide_index=True, width="stretch")
        for _, linha in testes[testes.rq.eq(rq)].iterrows():
            st.write(conclusao(linha))
        with controles:
            item = st.selectbox("Pergunta do formulário", ITENS[rq],
                                format_func=lambda codigo: f"{codigo} · {ENUNCIADOS[codigo]}",
                                key=f"publico_item_{rq}")
            tabela = tabela_proporcoes(freq, item)
            opcoes = list(dict.fromkeys(tabela["Resposta"].tolist()))
            opcao = st.selectbox("Opção de resposta", ["Todas as opções", *opcoes], key=f"publico_opcao_{rq}")
        with st.expander(f"Explorar respostas · {rq}"):
            if opcao != "Todas as opções":
                tabela = tabela[tabela.Resposta.eq(opcao)]
            st.dataframe(tabela, hide_index=True, width="stretch")
            if item == "C6":
                st.caption("Múltipla escolha. Nos tipos de dívida, o denominador exclui quem respondeu apenas 'Não sei'.")


def renderizar(caminho: Path = ARQUIVO_PUBLICO) -> None:
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    st.sidebar.caption("Resultados agregados da pesquisa")
    grupos = {
        "Amostra": ["Perfil da amostra"],
        "Resultados": ["Questões de pesquisa", "Itens Likert", "Confiabilidade", "Respostas abertas"],
        "Estudo": ["Metodologia e desvios"],
    }
    grupo = st.sidebar.radio("Navegação", list(grupos), key="publico_grupo")
    pagina = st.sidebar.radio("Página", grupos[grupo], key="publico_pagina")
    etapas = {
        "Perfil da amostra": ["Visão geral", "Distribuição de perfil"],
        "Questões de pesquisa": list(RQS),
        "Itens Likert": ["Nível percebido", "Impacto percebido"],
        "Confiabilidade": ["Alfa de Cronbach", "Alfa por item", "Validade convergente"],
        "Metodologia e desvios": ["Metodologia", "Descartes e limitações"],
    }
    etapa = st.sidebar.radio("Etapa", etapas[pagina], key=f"etapa_{pagina}") if pagina in etapas else None
    controles, resultado = st.columns([1, 3], gap="large")
    with controles:
        st.subheader("Seleção")
        st.caption("Os resultados usam a amostra válida e os recortes agregados disponíveis.")
    with resultado:
        _renderizar_pagina(d, pagina, etapa, controles)


def _renderizar_pagina(d: dict, pagina: str, etapa: str | None, controles) -> None:
    if pagina == "Questões de pesquisa":
        _rqs(d, etapa, controles)
    elif pagina == "Perfil da amostra":
        st.title(pagina)
        cols = st.columns(4)
        for col, label, chave in zip(cols, ["Recebidas", "Válidas", "Técnicos", "Gestão"],
                                     ["recebidas", "validas", "tecnico", "gestao"]):
            col.metric(label, d["amostra"][chave])
        st.caption(f"O arquivo recebido já havia sido filtrado e contém {d['amostra']['recebidas']} respostas. "
                   f"Descartes pelas regras da análise: {d['amostra']['descartadas']}. "
                   "Os totais não representam o número original de respostas coletadas.")
        freq = pd.DataFrame(d["frequencias"])
        if etapa == "Distribuição de perfil":
            with controles:
                item = st.selectbox("Perfil", ["B2", "B3", "B4", "B5", "B6", "B7", "B8"],
                                    format_func=lambda x: f"{x} · {ENUNCIADOS[x]}")
            st.subheader("Distribuição de perfil")
            st.dataframe(tabela_proporcoes(freq, item), hide_index=True, width="stretch")
    elif pagina == "Itens Likert":
        st.title(pagina)
        dist, conc = pd.DataFrame(d["distribuicao_likert"]), pd.DataFrame(d["concordancia_likert"])
        itens = ITENS_CONSTRUTO["NIV" if etapa == "Nível percebido" else "IMP"]
        with controles:
            item_escolhido = st.selectbox("Item", ["Todos", *itens], format_func=lambda x: x if x == "Todos" else f"{x} · {ENUNCIADOS[x]}")
        itens_exibidos = itens if item_escolhido == "Todos" else [item_escolhido]
        for item in itens_exibidos:
            st.markdown(f"**{item}.** {ENUNCIADOS[item]}")
            mostrar(barras_divergentes(dist[dist.item.eq(item)], conc[conc.item.eq(item)]))
        st.dataframe(conc[conc.item.isin(itens_exibidos)], hide_index=True, width="stretch")
    elif pagina == "Confiabilidade":
        st.title(pagina)
        for titulo, chave in (("Alfa de Cronbach", "confiabilidade"),
                              ("Alfa por item", "confiabilidade_itens"),
                              ("Validade convergente", "validade_convergente")):
            if titulo != etapa:
                continue
            st.subheader(titulo)
            st.dataframe(pd.DataFrame(d[chave]), hide_index=True, width="stretch")
    elif pagina == "Respostas abertas":
        st.title(pagina)
        st.write("A codificação e a revisão das respostas abertas dependem da conclusão da etapa manual. "
                "Esta versão pública não exibe textos individuais.")
    else:
        st.title(pagina)
        st.markdown("A pesquisa usa amostragem por conveniência e bola de neve. Os resultados se referem à amostra "
                    "e não representam automaticamente todos os profissionais. A coleta foi prorrogada até 25/11/2026.")
        st.write(f"A amostra contém {d['amostra']['gestao']} participantes de gestão; o mínimo planejado é {MINIMO_GESTAO}. "
                 f"Há {d['amostra']['sem_grupo']} resposta(s) sem grupo classificado. Comparações por papel são provisórias.")
        if etapa == "Descartes e limitações":
            st.dataframe(pd.DataFrame(list(d["amostra"]["descartes_por_etapa"].items()),
                                  columns=["Etapa", "Descartadas"]), hide_index=True, width="stretch")
