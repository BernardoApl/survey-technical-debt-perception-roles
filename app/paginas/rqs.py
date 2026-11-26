"""RQ1–RQ4: resultados da amostra completa, independentemente dos filtros."""
import streamlit as st

from app import contexto
from app.componentes import cabecalho_pagina, secao
from app.graficos import mostrar
from app.rqs_dados import (METRICAS, conclusao, figura_escores, figura_proporcoes,
                           figura_rq4, preparar, tabela_proporcoes, tabela_testes)
from src.config import ENUNCIADOS, MINIMO_GESTAO

ctx = contexto.obter()
dados = ctx.analise.dados
resultados = preparar(dados)
testes, frequencias, escores = (resultados[k] for k in ("testes", "frequencias", "escores"))

cabecalho_pagina("Questões de pesquisa", "Comparações e associações previstas no protocolo.", ctx)
st.info("Os resultados e gráficos desta página usam a amostra válida completa, sem aplicar os filtros da barra lateral.")
gestao = int(dados.grupo.eq("gestão").sum())
if gestao < MINIMO_GESTAO:
    st.warning(f"Baixo poder estatístico: há {gestao} participantes de gestão, abaixo do mínimo de {MINIMO_GESTAO}. "
               "Resultados não significativos não demonstram ausência de diferenças.")
pendentes = int(dados.grupo.isna().sum())
if pendentes:
    st.warning(f"Há {pendentes} resposta(s) sem grupo definido. Comparações por papel são provisórias; "
               "testes globais incluem essas respostas quando os dados necessários estão disponíveis.")
st.caption("Margens a 95% por grupo: pior caso p = 0,5, com o n de cada teste. Margens das proporções usam o percentual observado. "
           "A amostra é por conveniência: essas margens são indicativas e não corrigem viés de seleção.")

RQS = {
    "RQ1": ("Nível percebido", "Técnicos e gestores percebem o mesmo nível de dívida técnica?",
            "O nível percebido (NIV) não difere entre papéis."),
    "RQ2": ("Impacto percebido", "A percepção do impacto da dívida técnica difere entre papéis?",
            "O impacto percebido (IMP) não difere entre papéis."),
    "RQ3": ("Priorização e prática", "Como cada papel acha que a dívida técnica deveria ser priorizada e como ela é tratada na prática?",
            "Postura, prática percebida, frequência e quem decide não diferem entre papéis; a postura não difere da prática."),
    "RQ4": ("Experiência e porte", "A percepção de dívida técnica está associada à experiência e ao porte da empresa?",
            "Não há correlação entre nível, impacto ou postura e experiência ou porte."),
}

ITENS_POR_RQ = {
    "RQ1": ["C1", "C2", "C3", "C4", "C5", "C6"],
    "RQ2": ["D1", "D2", "D3", "D4", "D5"],
    "RQ3": ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"],
    "RQ4": ["B3", "B5", "C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4",
            "E1", "E3", "E5"],
}


def mostrar_testes(rq):
    st.markdown("**Testes previstos e conclusões por comparação**")
    st.dataframe(tabela_testes(testes, rq), hide_index=True, width="stretch")
    for _, linha in testes.loc[testes.rq.eq(rq)].iterrows():
        st.write(conclusao(linha))
    if rq == "RQ3":
        st.caption("A H0 geral menciona a prática por papel; a seção 5.5 não prevê um teste PRA × grupo separado. "
                   "M7 aparece descritivamente e na comparação pareada POS × PRA.")


def mostrar_proporcao(item, titulo):
    st.markdown(f"**{titulo}**")
    st.caption("Percentuais por grupo entre as respostas ao item; 'Não sei' é exibido quando aplicável.")
    mostrar(figura_proporcoes(frequencias, item))
    with st.expander(f"Ver proporções e margens · {titulo}"):
        st.dataframe(tabela_proporcoes(frequencias, item), hide_index=True, width="stretch")


def explorar_respostas(rq):
    with st.expander(f"Explorar respostas do CSV · {rq}"):
        st.caption("Selecione uma pergunta e uma opção para ver as contagens e os percentuais agregados "
                   "da amostra completa. A seleção não altera os testes nem os demais gráficos.")
        item = st.selectbox("Pergunta do formulário", ITENS_POR_RQ[rq],
                            format_func=lambda codigo: f"{codigo} · {ENUNCIADOS[codigo]}",
                            key=f"respostas_item_{rq}")
        tabela = tabela_proporcoes(frequencias, item)
        opcoes = list(dict.fromkeys(tabela["Resposta"].tolist()))
        selecionada = st.selectbox("Opção de resposta", ["Todas as opções", *opcoes],
                                   key=f"respostas_opcao_{rq}")
        if selecionada != "Todas as opções":
            tabela = tabela.loc[tabela["Resposta"].eq(selecionada)].reset_index(drop=True)
        st.dataframe(tabela, hide_index=True, width="stretch")
        if item == "C6":
            st.caption("C6 aceita múltiplas opções. Para os tipos de dívida, o denominador exclui "
                       "quem respondeu apenas 'Não sei'; para 'Nenhum' e 'Não sei', inclui todas as respostas.")


for numero, rq in enumerate(RQS, 1):
    titulo, pergunta, h0 = RQS[rq]
    with secao(numero, f"{rq} · {titulo}", chave=rq.lower()):
        st.markdown(f"**Pergunta:** {pergunta}")
        st.markdown(f"**H0:** {h0}")
        if rq in METRICAS:
            st.caption("Medianas por grupo; passe o cursor sobre as barras para ver n e intervalo interquartil (IQR).")
            mostrar(figura_escores(escores, METRICAS[rq]))
        if rq == "RQ1":
            mostrar_proporcao("C6", "M3 · Tipos de dívida técnica (C6)")
            st.caption("C6 permite múltiplas respostas; os percentuais podem somar mais de 100%.")
        elif rq == "RQ2":
            mostrar_proporcao("D5", "M5 · Maior efeito (D5)")
        elif rq == "RQ3":
            mostrar_proporcao("E7", "M9 · Frequência de tempo dedicado à dívida técnica (E7)")
            mostrar_proporcao("E8", "M10 · Quem decide (E8)")
        else:
            st.caption("Medianas agregadas por faixa; os testes de associação abaixo usam os pares individuais válidos.")
            mostrar(figura_rq4(dados, "B3"))
            mostrar(figura_rq4(dados, "B5"))
        mostrar_testes(rq)
        explorar_respostas(rq)
