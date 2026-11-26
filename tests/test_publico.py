import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import app.dados as dados_app
import app.publico as publico
import src.publicar_agregados as exportador
from src import sintetico

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


@pytest.fixture
def fotografia(tmp_path, monkeypatch):
    csv = sintetico.salvar(tmp_path / "entrada.csv", n=40)
    monkeypatch.setattr(exportador, "ler_reclassificacao", lambda: pd.DataFrame(
        columns=["texto_original", "grupo", "decidido_por", "justificativa"]))
    saida = exportador.gerar(csv, tmp_path / "agregado.json")
    return csv, saida


def test_agregados_nao_contem_dados_individuais(fotografia):
    csv, saida = fotografia
    bruto = pd.read_csv(csv, encoding="utf-8-sig")
    d = json.loads(saida.read_text(encoding="utf-8"))
    texto = saida.read_text(encoding="utf-8")
    assert len(d["testes_rq"]) == 14
    assert "resp_id" not in texto and "timestamp" not in texto
    for nome in ("F1", "F2"):
        coluna = bruto.columns[-2 if nome == "F1" else -1]
        for resposta in bruto[coluna].dropna():
            assert resposta not in texto
    assert d["amostra"]["recebidas"] == d["amostra"]["validas"] + d["amostra"]["descartadas"]


def test_modo_publico_sem_csv_mostra_rqs_reais_agregadas(fotografia, tmp_path, monkeypatch):
    _, saida = fotografia
    monkeypatch.setattr(dados_app, "CSV_BRUTO", tmp_path / "ausente.csv")
    monkeypatch.setattr(publico, "ARQUIVO_PUBLICO", saida)
    app = AppTest.from_file(APP, default_timeout=90).run()
    assert not app.exception, app.exception
    assert not any("DADOS SINTÉTICOS" in erro.value for erro in app.error)
    app.radio(key="publico_grupo").set_value("Resultados").run()
    app.radio(key="publico_pagina").set_value("Questões de pesquisa").run()
    assert not app.exception, app.exception
    tabelas = [item.value for item in app.dataframe if "p Holm" in item.value.columns]
    assert [len(t) for t in tabelas] == [1]
    app.selectbox(key="publico_item_RQ1").select("C6").run()
    assert not app.exception, app.exception
    for rq, total in (("RQ2", 2), ("RQ3", 5), ("RQ4", 6)):
        app.radio(key="etapa_Questões de pesquisa").set_value(rq).run()
        assert not app.exception, app.exception
        assert [len(t.value) for t in app.dataframe if "p Holm" in t.value.columns] == [total]


@pytest.mark.parametrize("pagina", ["Itens Likert", "Confiabilidade", "Respostas abertas", "Metodologia e desvios"])
def test_paginas_publicas_sem_erro(fotografia, tmp_path, monkeypatch, pagina):
    _, saida = fotografia
    monkeypatch.setattr(dados_app, "CSV_BRUTO", tmp_path / "ausente.csv")
    monkeypatch.setattr(publico, "ARQUIVO_PUBLICO", saida)
    app = AppTest.from_file(APP, default_timeout=90).run()
    grupo = "Estudo" if pagina == "Metodologia e desvios" else "Resultados"
    app.radio(key="publico_grupo").set_value(grupo).run()
    app.radio(key="publico_pagina").set_value(pagina).run()
    assert not app.exception, app.exception
