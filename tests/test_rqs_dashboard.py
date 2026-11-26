from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import app.dados as dados_app
from app.rqs_dados import conclusao, preparar, tabela_testes
from src import sintetico

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


@pytest.fixture
def tela(tmp_path, monkeypatch):
    csv = sintetico.salvar(tmp_path / "respostas.csv", n=50)
    monkeypatch.setattr(dados_app, "CSV_BRUTO", csv)
    monkeypatch.setattr(dados_app, "ler_reclassificacao", lambda: pd.DataFrame(
        columns=["texto_original", "grupo", "decidido_por", "justificativa"]))
    app = AppTest.from_file(APP, default_timeout=90).run()
    return app.switch_page("paginas/rqs.py").run()


def test_rqs_mostra_14_testes_e_metricas(tela):
    assert not tela.exception, tela.exception
    titulos = " ".join(h.proto.body for h in tela.get("html"))
    assert all(rq in titulos for rq in ("RQ1", "RQ2", "RQ3", "RQ4"))
    tabelas = [d.value for d in tela.dataframe if "p Holm" in d.value.columns]
    assert [len(t) for t in tabelas] == [1, 2, 5, 6]
    assert all("Margem gestão (p.p.)" in t.columns for t in tabelas)
    textos = " ".join(m.value for m in tela.markdown)
    assert all(m in textos for m in ("M3", "M5", "M9", "M10"))
    assert any("amostra válida completa" in i.value for i in tela.info)
    assert len(tela.get("plotly_chart")) == 9


def test_filtros_nao_alteram_testes(tela):
    antes = [d.value for d in tela.dataframe if "p Holm" in d.value.columns]
    tela.multiselect(key="f_grupo").set_value(["gestão"]).run()
    depois = [d.value for d in tela.dataframe if "p Holm" in d.value.columns]
    assert not tela.exception, tela.exception
    for a, b in zip(antes, depois, strict=True):
        pd.testing.assert_frame_equal(a, b)


def test_conclusao_nao_interpreta_nao_significativo_como_igualdade():
    base = {"variavel": "NIV", "comparacao": "grupo", "motivo": "", "p_holm": 0.2}
    assert "não houve evidência suficiente" in conclusao(pd.Series(base))
    base.update(p_holm=float("nan"), motivo="sem grupo")
    assert "não executável" in conclusao(pd.Series(base))


def test_amostra_pequena_mostra_aviso_e_motivos(tmp_path, monkeypatch):
    csv = sintetico.salvar(tmp_path / "pequena.csv", n=0)
    monkeypatch.setattr(dados_app, "CSV_BRUTO", csv)
    monkeypatch.setattr(dados_app, "ler_reclassificacao", lambda: pd.DataFrame(
        columns=["texto_original", "grupo", "decidido_por", "justificativa"]))
    tela = AppTest.from_file(APP, default_timeout=90).run().switch_page("paginas/rqs.py").run()
    assert not tela.exception, tela.exception
    assert any("Baixo poder" in aviso.value for aviso in tela.warning)
    tabelas = [d.value for d in tela.dataframe if "p Holm" in d.value.columns]
    assert sum(len(t) for t in tabelas) == 14
    assert any(t["Motivo de não execução"].ne("").any() for t in tabelas)


def test_explorar_respostas_agregadas_nao_altera_testes(tela):
    antes = [d.value for d in tela.dataframe if "p Holm" in d.value.columns]
    tela.selectbox(key="respostas_item_RQ1").select("C6").run()
    assert not tela.exception, tela.exception
    opcoes = tela.selectbox(key="respostas_opcao_RQ1").options
    opcao = next(opcao for opcao in opcoes if opcao != "Todas as opções")
    tela.selectbox(key="respostas_opcao_RQ1").select(opcao).run()
    assert not tela.exception, tela.exception
    tabelas = [d.value for d in tela.dataframe if "Resposta" in d.value.columns]
    tabela = next(t for t in tabelas if len(t) == 3 and set(t["Resposta"]) == {opcao})
    assert set(tabela["Grupo"]) == {"total", "técnico", "gestão"}
    assert set(tabela.columns) == {"Resposta", "Grupo", "k", "n", "%", "Margem (p.p.)"}
    depois = [d.value for d in tela.dataframe if "p Holm" in d.value.columns]
    for a, b in zip(antes, depois, strict=True):
        pd.testing.assert_frame_equal(a, b)
