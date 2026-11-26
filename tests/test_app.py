import re
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import app.dados as dados_app
from app.filtros import FILTROS, aplicar_filtros, filtros_ativos, rotular
from src import sintetico
from src.clean import limpar
from src.config import OPCOES_B3, OPCOES_B5
from src.load import carregar

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
PAGINAS = ["perfil", "likert", "rqs", "confiabilidade", "abertas", "instrumento", "metodologia"]


def _dados():
    return pd.DataFrame(
        {
            "resp_id": ["R1", "R2", "R3", "R4"],
            "grupo": ["técnico", "gestão", "técnico", pd.NA],
            "B3": [1.0, 3.0, 5.0, 3.0],
            "B5": [1.0, 1.0, 4.0, 2.0],
            "B6": ["Startup", "Setor público", "Startup", "Produto próprio"],
            "B7": [1.0, 2.0, 3.0, 4.0],
        }
    )


def _todos():
    return {coluna: list(opcoes) for coluna, (_, opcoes, _) in FILTROS.items()}


def test_todas_as_opcoes_nao_filtram():
    assert len(aplicar_filtros(_dados(), _todos())) == 4
    assert filtros_ativos(_todos()) == []


def test_selecao_vazia_nao_filtra():
    assert len(aplicar_filtros(_dados(), {c: [] for c in FILTROS})) == 4


def test_filtro_de_grupo_tira_pendentes():
    selecao = _todos() | {"grupo": ["técnico"]}
    assert aplicar_filtros(_dados(), selecao)["resp_id"].tolist() == ["R1", "R3"]
    assert filtros_ativos(selecao) == ["Grupo de papel"]


def test_filtro_ordinal_usa_o_texto_da_opcao():
    selecao = _todos() | {"B3": [OPCOES_B3[2]]}
    assert aplicar_filtros(_dados(), selecao)["resp_id"].tolist() == ["R2", "R4"]


def test_filtros_combinados():
    selecao = _todos() | {"B5": [OPCOES_B5[0]], "B6": ["Startup"]}
    assert aplicar_filtros(_dados(), selecao)["resp_id"].tolist() == ["R1"]


def test_rotular():
    assert rotular(_dados(), "B5").tolist()[2] == OPCOES_B5[3]
    assert rotular(_dados(), "B6").equals(_dados()["B6"])


@pytest.fixture
def app_sintetico(tmp_path, monkeypatch):
    """Dashboard lendo um CSV sintético como se fosse o real."""
    csv = sintetico.salvar(tmp_path / "respostas.csv", n=60)
    monkeypatch.setattr(dados_app, "CSV_BRUTO", csv)
    teste = AppTest.from_file(APP, default_timeout=60)
    teste.run()
    return teste


@pytest.mark.parametrize("pagina", PAGINAS)
def test_cada_pagina_abre_sem_erro(app_sintetico, pagina):
    app_sintetico.switch_page(f"paginas/{pagina}.py").run()
    assert not app_sintetico.exception, app_sintetico.exception
    assert any('class="top"' in h.proto.body for h in app_sintetico.get("html"))


def test_perfil_mostra_contagens(app_sintetico):
    rotulos = {m.label: int(m.value) for m in app_sintetico.metric}
    assert {"Recebidas", "Válidas", "Técnicos", "Gestão"} <= set(rotulos)
    legendas = " ".join(c.value for c in app_sintetico.caption)
    descartadas = rotulos["Recebidas"] - rotulos["Válidas"]
    assert f"{descartadas} descartadas" in legendas
    assert rotulos["Técnicos"] + rotulos["Gestão"] <= rotulos["Válidas"]
    assert "margem ±" in legendas


def test_csv_real_nao_mostra_aviso_de_sintetico(app_sintetico):
    assert not any("SINTÉTICOS" in e.value for e in app_sintetico.error)


def test_sem_csv_real_mostra_aviso(tmp_path, monkeypatch):
    monkeypatch.setattr(dados_app, "CSV_BRUTO", tmp_path / "nao_existe.csv")
    monkeypatch.setattr(dados_app, "CSV_SINTETICO", tmp_path / "sintetico.csv")
    teste = AppTest.from_file(APP, default_timeout=60)
    teste.run()
    assert any("SINTÉTICOS" in e.value for e in teste.error)


def test_trocar_filtro_muda_validas_filtradas(app_sintetico):
    def cabecalho():
        return next(h.proto.body for h in app_sintetico.get("html") if 'class="top"' in h.proto.body)

    assert "Filtros:" not in cabecalho()
    app_sintetico.multiselect(key="f_grupo").set_value(["gestão"]).run()
    aviso = cabecalho()
    assert "Filtros:" in aviso
    filtradas, total = (int(x) for x in re.search(r"<b>(\d+)</b> de (\d+)", aviso).groups())
    assert filtradas < total
    assert not app_sintetico.exception


@pytest.fixture
def pastas_vazias(tmp_path, monkeypatch):
    """data/processed/ e outputs/ temporários, para não ler arquivos locais."""
    import src.config

    processado, saidas = tmp_path / "processed", tmp_path / "outputs"
    monkeypatch.setattr(src.config, "DIR_PROCESSADO", processado)
    monkeypatch.setattr(src.config, "DIR_SAIDAS", saidas)
    return processado, saidas


def _codificar_tudo(tmp_path, pastas, original, anonimizado, aprovar=True):
    """Roda o fluxo da #5 sobre o CSV sintético: aprova, codifica igual e salva."""
    from src.abertas import ler_livro, processar, salvar_abertas

    analise = dados_app.preparar_analise(dados_app.CSV_BRUTO)
    limpeza = limpar(carregar(dados_app.CSV_BRUTO))
    validas = limpeza.validas.copy()
    alvo = validas["resp_id"].iloc[0]
    validas.loc[validas["resp_id"] == alvo, "F1"] = original
    livro = ler_livro()
    r = processar(validas, livro)
    revisao = r.revisao.copy()
    if aprovar:
        revisao["status"], revisao["revisado_por"] = "aprovado", "teste"
        revisao.loc[revisao["texto_original"] == original, "texto_anonimizado"] = anonimizado
    r = processar(validas, livro, revisao)
    planilhas = {}
    for nome, planilha in r.planilhas.items():
        planilha = planilha.copy()
        planilha["codigos"] = planilha["item"].map({"F1": "efeito_esforco;falta_testes",
                                                   "F2": "pressao_prazo"})
        planilhas[nome] = planilha
    r = processar(validas, livro, revisao, planilhas, None, limpeza.reclassificacao)
    processado, saidas = pastas
    salvar_abertas(r, tmp_path / "manual", processado, saidas)
    assert set(analise.dados["resp_id"]) == set(validas["resp_id"])
    return r


def test_abertas_sem_codificacao_nao_mostra_texto(app_sintetico, pastas_vazias):
    app_sintetico.switch_page("paginas/abertas.py").run()
    assert not app_sintetico.exception, app_sintetico.exception
    assert any("Aguardando" in i.value for i in app_sintetico.info)
    textos = " ".join(m.value for m in app_sintetico.markdown)
    assert "monstro" not in textos and "Primeira linha" not in textos


def test_abertas_com_pendencia_nao_mostra_nada(tmp_path, app_sintetico, pastas_vazias):
    _codificar_tudo(tmp_path, pastas_vazias, "Texto da Fulana.", "", aprovar=False)
    app_sintetico.switch_page("paginas/abertas.py").run()
    assert any("pendência" in i.value for i in app_sintetico.info)
    assert not app_sintetico.dataframe


def test_abertas_mostra_frequencias_iguais_as_da_issue_5(tmp_path, app_sintetico, pastas_vazias):
    original = "O sistema Atlas da Fulana caiu."
    anonimizado = "O sistema [removido] da [removido] caiu."
    r = _codificar_tudo(tmp_path, pastas_vazias, original, anonimizado)

    app_sintetico.switch_page("paginas/abertas.py").run()
    assert not app_sintetico.exception, app_sintetico.exception
    assert not any("Aguardando" in i.value for i in app_sintetico.info)
    exibida = app_sintetico.dataframe[0].value.set_index(["codigo", "recorte"])
    saida = r.frequencias[r.frequencias["item"] == "F1"].set_index(["codigo", "recorte"])
    for chave, linha in exibida.iterrows():
        assert linha["k"] == saida.loc[chave, "k"], chave
        assert linha["n"] == saida.loc[chave, "n"], chave
        assert linha["pct"] == round(saida.loc[chave, "pct"], 1), chave
        assert linha["margem_pp"] == round(saida.loc[chave, "margem_pp"], 1), chave
    assert set(exibida.index.get_level_values("codigo")) == {"efeito_esforco", "falta_testes"}
    textos = " ".join(m.value for m in app_sintetico.markdown)
    assert anonimizado in textos
    assert "Atlas" not in textos and "Fulana" not in textos


def test_abertas_respeitam_filtro_de_grupo(tmp_path, app_sintetico, pastas_vazias):
    _codificar_tudo(tmp_path, pastas_vazias, "Texto.", "Texto.")
    app_sintetico.multiselect(key="f_grupo").set_value(["gestão"]).run()
    app_sintetico.switch_page("paginas/abertas.py").run()
    assert not app_sintetico.exception, app_sintetico.exception
    exibida = app_sintetico.dataframe[0].value
    assert "técnico" not in set(exibida["recorte"])


# ---------------------------------------------------------------------------
# Itens Likert e confiabilidade (#10): o que aparece bate com as saídas da #6
# ---------------------------------------------------------------------------
def _analise():
    return dados_app.preparar_analise(dados_app.CSV_BRUTO).dados


def _conferir_likert(exibida, dados):
    from src.describe import concordancia_likert, distribuicao_likert, frequencias

    esperado = concordancia_likert(dados)
    esperado = esperado[esperado["n"] > 0]
    nao_sei = distribuicao_likert(frequencias(dados)).drop_duplicates(["item", "recorte"]) \
        .set_index(["item", "recorte"])["nao_sei"]
    rotulos = {"total": "Total", "técnico": "Técnico", "gestão": "Gestão"}
    assert len(exibida) == len(esperado)
    exibida = exibida.set_index(["item", "recorte"])
    for _, linha in esperado.iterrows():
        mostrada = exibida.loc[(linha["item"], rotulos[linha["recorte"]])]
        assert mostrada["n"] == linha["n"]
        assert mostrada["k"] == linha["k"]
        assert mostrada["pct"] == round(linha["pct"], 1)
        assert mostrada["margem_pp"] == round(linha["margem_pp"], 1)
        assert mostrada["nao_sei"] == nao_sei[(linha["item"], linha["recorte"])]


def test_likert_bate_com_a_issue_6(app_sintetico):
    from src.config import ENUNCIADOS

    app_sintetico.switch_page("paginas/likert.py").run()
    assert not app_sintetico.exception, app_sintetico.exception
    _conferir_likert(app_sintetico.dataframe[0].value, _analise())
    assert len(app_sintetico.get("plotly_chart")) == 8  # um gráfico por item, C1–C4 e D1–D4
    textos = " ".join(m.value for m in app_sintetico.markdown)
    for item in ("C1", "C4", "D2", "D4"):
        assert ENUNCIADOS[item] in textos
    assert "C4 (R)" in textos and "D2 (R)" in textos


def test_likert_respeita_filtros(app_sintetico):
    app_sintetico.multiselect(key="f_grupo").set_value(["gestão"]).run()
    app_sintetico.switch_page("paginas/likert.py").run()
    assert not app_sintetico.exception, app_sintetico.exception
    exibida = app_sintetico.dataframe[0].value
    assert set(exibida["recorte"]) == {"Total", "Gestão"}
    dados = _analise()
    _conferir_likert(exibida, dados[dados["grupo"] == "gestão"])


def test_confiabilidade_bate_com_a_issue_6(app_sintetico):
    from src.reliability import confiabilidade, validade_convergente

    app_sintetico.switch_page("paginas/confiabilidade.py").run()
    assert not app_sintetico.exception, app_sintetico.exception
    alfa, itens = confiabilidade(_analise())
    validade = validade_convergente(_analise())

    tab_alfa, tab_itens, tab_validade = (d.value for d in app_sintetico.dataframe)
    assert tab_alfa["construto"].tolist() == alfa["construto"].tolist()
    assert tab_alfa["n"].tolist() == alfa["n"].tolist()
    assert tab_alfa["alfa"].tolist() == alfa["alfa"].round(3).tolist()
    assert tab_itens["alfa_sem_item"].tolist() == itens["alfa_sem_item"].round(3).tolist()
    assert tab_itens["r_item_total"].tolist() == itens["r_item_total"].round(3).tolist()
    assert tab_validade["rho"].tolist() == validade["rho"].round(3).tolist()
    assert tab_validade["n"].tolist() == validade["n"].tolist()
    # a meta aparece na página e o gráfico do alfa é exibido
    assert any("0,70" in h.proto.body for h in app_sintetico.get("html"))
    assert len(app_sintetico.get("plotly_chart")) == 1


def test_confiabilidade_ignora_filtros(app_sintetico):
    app_sintetico.switch_page("paginas/confiabilidade.py").run()
    antes = app_sintetico.dataframe[0].value["n"].tolist()
    app_sintetico.multiselect(key="f_grupo").set_value(["gestão"]).run()
    app_sintetico.switch_page("paginas/confiabilidade.py").run()
    assert not app_sintetico.exception, app_sintetico.exception
    assert app_sintetico.dataframe[0].value["n"].tolist() == antes


def test_editar_arquivo_manual_muda_a_chave_do_cache(tmp_path, monkeypatch):
    """Reclassificar um "Outro" depois de abrir o dashboard precisa recalcular os grupos."""
    csv = tmp_path / "respostas.csv"
    csv.write_text("x", encoding="utf-8")
    reclass = tmp_path / "reclassificacao_outro.csv"
    monkeypatch.setattr(dados_app, "ENTRADAS_MANUAIS", [reclass])
    antes = dados_app.versao_das_entradas(csv)
    reclass.write_text("texto_original,grupo,decidido_por,justificativa\n", encoding="utf-8")
    assert dados_app.versao_das_entradas(csv) != antes
