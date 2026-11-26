import json

import numpy as np
import pandas as pd
import pytest

from src import sintetico
from src.clean import (
    COLUNAS_RECLASSIFICACAO,
    ler_reclassificacao,
    limpar,
    salvar_limpeza,
)
from src.config import (
    CODIGOS,
    FUSO,
    LIKERT,
    NAO,
    NAO_SEI,
    NSA,
    PAPEIS_TECNICOS,
    PERIODO_PREREGISTRADO,
    PERIODO_PRINCIPAL,
    SIM,
)
from src.load import carregar
from tests.fabrica import resposta, tabela

def etapas(resultado):
    """resp_id -> etapa do descarte (só descartadas)."""
    log = resultado.log[resultado.log["descartada"]]
    return dict(zip(log["resp_id"], log["etapa"]))


def test_resposta_valida_passa():
    r = limpar(tabela(resposta()))
    assert r.resumo["validas"] == 1
    assert r.log.empty


@pytest.mark.parametrize(
    "trocas, etapa",
    [
        ({"momento": "2026-11-12 23:59:59"}, 0),
        ({"momento": "2026-11-26 00:00:00"}, 0),
        ({"A1": NAO, **{c: np.nan for c in CODIGOS[2:]}}, 1),
        ({"B1": NAO, **{c: np.nan for c in CODIGOS[3:]}}, 2),
        ({"ATN": LIKERT[3]}, 3),
        ({c: LIKERT[3] for c in ("C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4")}, 4),
        ({c: NSA for c in ("C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4")}, 4),
    ],
)
def test_cada_etapa_isolada(trocas, etapa):
    r = limpar(tabela(resposta(**trocas), resposta("2026-11-20 10:00:00")))
    assert etapas(r) == {r.log["resp_id"].iloc[0]: etapa}
    assert r.resumo["validas"] == 1


def test_sete_iguais_nao_e_straightlining():
    itens = {c: LIKERT[3] for c in ("C1", "C2", "C3", "C4", "D1", "D2", "D3")}
    r = limpar(tabela(resposta(**itens, D4=LIKERT[4])))
    assert r.resumo["validas"] == 1


def test_ordem_recebe_motivo_da_primeira_etapa():
    itens = {c: LIKERT[0] for c in ("C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4")}
    r = limpar(tabela(resposta(ATN=LIKERT[0], **itens)))
    assert etapas(r) == {"R001": 3}
    assert len(r.log) == 1


@pytest.mark.parametrize(
    "momento, principal, preregistrado",
    [
        ("2026-11-13 00:00:00", True, True),
        ("2026-11-22 23:59:59", True, True),
        ("2026-11-23 00:00:00", True, False),
        ("2026-11-25 23:59:59", True, False),
        ("2026-11-26 00:00:00", False, False),
    ],
)
def test_limites_do_periodo(momento, principal, preregistrado):
    df = tabela(resposta(momento))
    assert (limpar(df, PERIODO_PRINCIPAL).resumo["validas"] == 1) is principal
    assert (limpar(df, PERIODO_PREREGISTRADO).resumo["validas"] == 1) is preregistrado


@pytest.mark.parametrize("minutos, descartada", [(40, True), (60, True), (61, False)])
def test_duplicata_janela(minutos, descartada):
    inicio = pd.Timestamp("2026-11-19 09:00:00")
    df = tabela(resposta(str(inicio)), resposta(str(inicio + pd.Timedelta(minutes=minutos))))
    assert etapas(limpar(df)) == ({"R002": 5} if descartada else {})


def test_tres_copias_fica_so_a_primeira():
    df = tabela(*(resposta(f"2026-11-19 09:{m:02d}:00") for m in (0, 20, 40)))
    assert etapas(limpar(df)) == {"R002": 5, "R003": 5}


def test_copia_de_resposta_ja_descartada_nao_vira_duplicata():
    df = tabela(
        resposta("2026-11-19 09:00:00", ATN=LIKERT[3]),
        resposta("2026-11-19 09:10:00", ATN=LIKERT[3]),
    )
    assert etapas(limpar(df)) == {"R001": 3, "R002": 3}


def test_duplicata_com_abertas_vazias():
    df = tabela(resposta("2026-11-19 09:00:00"), resposta("2026-11-19 09:30:00"))
    assert df["F1"].isna().all()
    assert etapas(limpar(df)) == {"R002": 5}


def test_resposta_parecida_nao_e_duplicata():
    df = tabela(resposta("2026-11-19 09:00:00"), resposta("2026-11-19 09:10:00", C5="8"))
    assert etapas(limpar(df)) == {}


@pytest.mark.parametrize(
    "trocas, construto",
    [
        ({"C1": NSA, "C2": NSA, "C3": NSA}, "NIV"),
        ({"D1": NSA, "D2": NSA, "D3": NSA}, "IMP"),
        ({"E2": NAO_SEI, "E4": NAO_SEI}, "PRA"),
    ],
)
def test_construto_ausente_nao_descarta(trocas, construto):
    r = limpar(tabela(resposta(**trocas)))
    assert r.resumo["validas"] == 1
    assert r.resumo["construtos_ausentes"][construto] == 1
    assert r.log["descartada"].tolist() == [False]
    assert r.log["etapa"].tolist() == [6]


def test_metade_de_nao_sei_nao_e_ausente():
    r = limpar(tabela(resposta(C1=NSA, C2=NSA)))
    assert r.resumo["construtos_ausentes"]["NIV"] == 0


def _reclass(**grupos):
    return pd.DataFrame(
        [{"texto_original": t, "grupo": g, "decidido_por": "teste", "justificativa": "teste"}
         for t, g in grupos.items()],
        columns=COLUNAS_RECLASSIFICACAO,
    )


def test_outro_classificado_como_tecnico_fica():
    r = limpar(tabela(resposta(B2="Engenheiro de software")),
               reclassificacao=_reclass(**{"Engenheiro de software": "técnico"}))
    assert r.resumo["validas"] == 1
    assert r.resumo["outro_pendentes"] == []


def test_outro_classificado_como_fora_e_descartado():
    r = limpar(tabela(resposta(B2="Designer UX")),
               reclassificacao=_reclass(**{"Designer UX": "fora"}))
    assert etapas(r) == {"R001": 2}


def test_outro_novo_fica_pendente_e_entra_no_arquivo():
    r = limpar(tabela(resposta(B2="Analista de TI")))
    assert r.resumo["validas"] == 1
    assert r.resumo["outro_pendentes"] == ["Analista de TI"]
    linha = r.reclassificacao.set_index("texto_original").loc["Analista de TI"]
    assert linha["grupo"] == ""


def test_reclassificacao_com_grupo_invalido(tmp_path):
    caminho = tmp_path / "reclass.csv"
    _reclass(**{"CTO": "gerência"}).to_csv(caminho, index=False)
    with pytest.raises(ValueError, match="grupo inválido"):
        ler_reclassificacao(caminho)


def test_reclassificacao_inexistente_vira_tabela_vazia(tmp_path):
    assert ler_reclassificacao(tmp_path / "nao_existe.csv").empty


@pytest.fixture
def sintetico_carregado(tmp_path):
    return carregar(sintetico.salvar(tmp_path / "respostas.csv", n=40))


@pytest.mark.parametrize("periodo", [PERIODO_PRINCIPAL, PERIODO_PREREGISTRADO])
def test_contas_fecham(sintetico_carregado, periodo):
    r = limpar(sintetico_carregado, periodo)
    resumo = r.resumo
    assert resumo["recebidas"] == resumo["validas"] + resumo["descartadas"]
    assert resumo["descartadas"] == sum(resumo["descartes_por_etapa"].values())
    descartes = r.log[r.log["descartada"]]
    assert descartes["resp_id"].is_unique
    assert set(descartes["resp_id"]).isdisjoint(r.validas["resp_id"])


def test_casos_especiais_do_sintetico(sintetico_carregado):
    df = sintetico_carregado
    r = limpar(df, PERIODO_PRINCIPAL)
    etapa_de = etapas(r)
    por_data = df.set_index(df["timestamp"].dt.strftime("%d/%m %H:%M"))["resp_id"]
    esperado = {
        "12/11 23:30": 0, "26/11 00:30": 0, "14/11 10:00": 1, "14/11 11:00": 2,
        "15/11 09:00": 3, "15/11 10:00": 4, "19/11 09:40": 5,
    }
    for momento, etapa in esperado.items():
        assert etapa_de[por_data[momento]] == etapa, momento
    assert por_data["24/11 14:00"] in set(r.validas["resp_id"])
    assert por_data["24/11 14:00"] not in set(
        limpar(df, PERIODO_PREREGISTRADO).validas["resp_id"]
    )
    assert "Analista de TI" in r.resumo["outro_pendentes"]


def test_salvar_limpeza_sem_horario_nem_abertas(tmp_path, sintetico_carregado):
    r = limpar(sintetico_carregado)
    salvar_limpeza(r, "_teste", tmp_path / "out", tmp_path / "proc")
    validas = pd.read_csv(tmp_path / "proc" / "respostas_validas_teste.csv")
    assert not {"timestamp", "F1", "F2"} & set(validas.columns)
    assert "Analista de TI" not in set(validas["B2"])
    assert "Outro" in set(validas["B2"])
    log = pd.read_csv(tmp_path / "out" / "log_descartes_teste.csv")
    assert list(log.columns) == ["resp_id", "etapa", "motivo", "descartada"]
    resumo = json.loads((tmp_path / "out" / "resumo_amostra_teste.json").read_text("utf-8"))
    assert resumo["validas"] == len(validas)
