import csv

import pandas as pd
import pytest

from src import sintetico
from src.config import CODIGOS, FUSO
from src.load import ErroFormulario, carregar, converter_data


@pytest.fixture
def csv_sintetico(tmp_path):
    return sintetico.salvar(tmp_path / "respostas.csv", n=30)


def _reescrever(caminho, cabecalho=None, linhas=None):
    with open(caminho, encoding="utf-8", newline="") as f:
        leitor = list(csv.reader(f))
    cab = cabecalho if cabecalho is not None else leitor[0]
    corpo = linhas if linhas is not None else leitor[1:]
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([cab, *corpo])
    return caminho


def test_carrega_sintetico(csv_sintetico):
    df = carregar(csv_sintetico)
    assert list(df.columns) == ["resp_id", *CODIGOS]
    assert df["resp_id"].iloc[0] == "R001"
    assert df["resp_id"].is_unique
    assert df["timestamp"].is_monotonic_increasing
    assert str(df["timestamp"].dt.tz) == FUSO


def test_cabecalho_alterado_gera_erro_com_posicao(csv_sintetico):
    cab = list(sintetico.CABECALHOS)
    cab[14] = "Qual nota você dá para a dívida técnica?"
    _reescrever(csv_sintetico, cabecalho=cab)
    with pytest.raises(ErroFormulario, match=r"posição 14 \(C5\)"):
        carregar(csv_sintetico)


@pytest.mark.parametrize("delta", [-1, 1])
def test_numero_de_colunas_errado(csv_sintetico, delta):
    with open(csv_sintetico, encoding="utf-8", newline="") as f:
        linhas = list(csv.reader(f))
    ajustar = (lambda l: l[:-1]) if delta < 0 else (lambda l: l + ["extra"])
    _reescrever(csv_sintetico, ajustar(linhas[0]), [ajustar(l) for l in linhas[1:]])
    with pytest.raises(ErroFormulario, match="colunas"):
        carregar(csv_sintetico)


def test_cabecalho_com_bom_e_espacos(csv_sintetico):
    cab = list(sintetico.CABECALHOS)
    cab[1] = "  Li o termo de  consentimento e aceito participar. "
    _reescrever(csv_sintetico, cabecalho=cab)
    conteudo = csv_sintetico.read_bytes()
    csv_sintetico.write_bytes(b"\xef\xbb\xbf" + conteudo)
    assert len(carregar(csv_sintetico)) > 0


def test_texto_com_quebra_de_linha_e_aspas(csv_sintetico):
    df = carregar(csv_sintetico)
    assert (df["F1"] == 'Primeira linha.\nSegunda linha com "aspas".').sum() == 1


def test_vazio_vira_nan(csv_sintetico):
    df = carregar(csv_sintetico)
    assert df["F2"].isna().any()
    assert not (df.fillna("x") == "").any().any()


def test_c6_mantem_ponto_e_virgula(csv_sintetico):
    df = carregar(csv_sintetico)
    assert (df["C6"] == "Código;Nenhum").any()


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("2026/11/16 9:23:49 AM GMT-3", "2026-11-16 09:23:49"),
        ("2026/11/16 9:23:49 PM GMT-3", "2026-11-16 21:23:49"),
        ("2026/11/16 12:05:00 AM GMT-3", "2026-11-16 00:05:00"),
        ("2026/11/16 12:05:00 PM GMT-3", "2026-11-16 12:05:00"),
    ],
)
def test_converter_data(texto, esperado):
    resultado = converter_data(pd.Series([texto])).iloc[0]
    assert resultado == pd.Timestamp(esperado, tz=FUSO)


def test_data_invalida_gera_erro():
    with pytest.raises(ErroFormulario, match="Data/hora"):
        converter_data(pd.Series(["16/11/2026 09:23"]))


def test_formato_do_gerador_bate_com_o_leitor():
    from datetime import datetime

    texto = sintetico.formatar_data(datetime(2026, 11, 16, 21, 23, 49))
    assert texto == "2026/11/16 9:23:49 PM GMT-3"
    assert converter_data(pd.Series([texto])).iloc[0] == pd.Timestamp(
        "2026-11-16 21:23:49", tz=FUSO
    )


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError, match="data/raw/respostas.csv"):
        carregar(tmp_path / "nao_existe.csv")


def test_linhas_totalmente_vazias_sao_ignoradas(csv_sintetico):
    antes = len(carregar(csv_sintetico))
    with open(csv_sintetico, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([[""] * len(CODIGOS)] * 3)
    assert len(carregar(csv_sintetico)) == antes
