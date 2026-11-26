import re
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import app.dados as dados_app
from app.filtros import FILTROS, aplicar_filtros, filtros_ativos, rotular
from src import sintetico
from src.config import OPCOES_B3, OPCOES_B5

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
PAGINAS = ["perfil", "likert", "rqs", "confiabilidade", "abertas", "metodologia"]


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


def test_abertas_sem_codificacao_nao_mostra_texto(app_sintetico):
    app_sintetico.switch_page("paginas/abertas.py").run()
    assert any("Aguardando" in i.value for i in app_sintetico.info)
    textos = " ".join(m.value for m in app_sintetico.markdown)
    assert "monstro" not in textos and "Primeira linha" not in textos


def test_abertas_com_codificacao_mostra_frequencias(tmp_path, monkeypatch, app_sintetico):
    import src.config

    analise = dados_app.preparar_analise(dados_app.CSV_BRUTO)
    v1, v2, v3, v4 = analise.dados["resp_id"].iloc[:4]
    descartada = analise.log.loc[analise.log["descartada"], "resp_id"].iloc[0]
    manual = tmp_path / "data" / "manual"
    manual.mkdir(parents=True)
    pd.DataFrame(
        {
            "resp_id": [v1, v2, v3, v4, descartada],
            "campo": ["F1", "F1", "F1", "F2", "F1"],
            "texto_anonimizado": ["Texto A [removido].", "Texto B.", "", "Texto C.", "Descartada."],
            "codigo_final": ["pressao_prazo;falta_testes", "pressao_prazo", "", "falta_apoio_gestao",
                             "outro"],
        }
    ).to_csv(manual / "codificacao_abertas.csv", index=False)
    monkeypatch.setattr(src.config, "DIR_MANUAL", manual)

    app_sintetico.switch_page("paginas/abertas.py").run()
    assert not app_sintetico.exception, app_sintetico.exception
    assert not any("Aguardando" in i.value for i in app_sintetico.info)
    tabela = app_sintetico.dataframe[0].value
    assert set(tabela["Código"]) == {"pressao_prazo", "falta_testes"}
    textos = " ".join(m.value for m in app_sintetico.markdown)
    assert "Texto A [removido]." in textos
    assert "Descartada." not in textos  # resposta descartada na limpeza não aparece


def test_abertas_com_codigo_pendente_nao_mostra_nada(tmp_path, monkeypatch, app_sintetico):
    import src.config

    manual = tmp_path / "manual"
    manual.mkdir()
    pd.DataFrame(
        {"resp_id": ["R001"], "campo": ["F1"], "texto_anonimizado": ["Texto."], "codigo_final": [""]}
    ).to_csv(manual / "codificacao_abertas.csv", index=False)
    monkeypatch.setattr(src.config, "DIR_MANUAL", manual)

    app_sintetico.switch_page("paginas/abertas.py").run()
    assert any("sem código final" in i.value for i in app_sintetico.info)
