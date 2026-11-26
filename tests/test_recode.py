import numpy as np
import pandas as pd
import pytest

from src import sintetico
from src.clean import COLUNAS_RECLASSIFICACAO, limpar
from src.config import (
    LIKERT,
    NAO_SEI,
    NSA,
    OPCOES_B3,
    OPCOES_B4,
    OPCOES_B5,
    OPCOES_B6,
    OPCOES_B7,
    OPCOES_D5,
    OPCOES_E7,
    OPCOES_E8,
    PAPEIS_GESTAO,
    PAPEIS_TECNICOS,
    TIPOS_C6,
    VINHETAS,
)
from src.load import carregar
from src.recode import (
    COLUNAS_TIPOS_C6,
    ITENS_INVERTIDOS,
    ORDINAIS,
    ValorDesconhecido,
    recodificar,
)
from tests.fabrica import resposta, tabela


def recod(*linhas, reclassificacao=None):
    return recodificar(tabela(*linhas), reclassificacao)


def _reclass(**grupos):
    return pd.DataFrame(
        [{"texto_original": t, "grupo": g, "decidido_por": "t", "justificativa": "t"}
         for t, g in grupos.items()],
        columns=COLUNAS_RECLASSIFICACAO,
    )


# ---------------------------------------------------------------------------
# Cobertura dos dicionários
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "item, opcoes",
    [
        ("C1", LIKERT), ("D4", LIKERT), ("ATN", LIKERT),
        ("E1", VINHETAS[1]), ("E2", VINHETAS[1]), ("E3", VINHETAS[2]),
        ("E4", VINHETAS[2]), ("E5", VINHETAS[3]), ("E6", VINHETAS[3]),
        ("E7", [o for o in OPCOES_E7 if o != NAO_SEI]),
        ("B3", OPCOES_B3), ("B4", OPCOES_B4), ("B5", OPCOES_B5), ("B7", OPCOES_B7),
    ],
)
def test_toda_opcao_vira_sua_posicao(item, opcoes):
    dados, _ = recod(*(resposta(f"2026-11-15 10:0{i}:00", **{item: o})
                       for i, o in enumerate(opcoes)))
    assert dados[item].tolist() == list(range(1, len(opcoes) + 1))


@pytest.mark.parametrize(
    "item, opcoes",
    [("B6", OPCOES_B6), ("D5", OPCOES_D5), ("E8", OPCOES_E8)],
)
def test_toda_opcao_nominal_e_aceita(item, opcoes):
    dados, _ = recod(*(resposta(f"2026-11-15 10:0{i}:00", **{item: o})
                       for i, o in enumerate(opcoes)))
    assert len(dados) == len(opcoes)


@pytest.mark.parametrize(
    "item",
    [*ORDINAIS, "B6", "D5", "E8", "B8", "C5", "C6"],
)
def test_valor_desconhecido_gera_erro(item):
    with pytest.raises(ValorDesconhecido, match=item):
        recod(resposta(**{item: "opção que não existe"}))


@pytest.mark.parametrize("item, valor", [("B8", "0"), ("B8", "6"), ("C5", "11"), ("C5", "-1")])
def test_escala_numerica_fora_do_intervalo(item, valor):
    with pytest.raises(ValorDesconhecido, match=item):
        recod(resposta(**{item: valor}))


def test_escalas_numericas():
    dados, _ = recod(resposta(B8="1", C5="0"), resposta("2026-11-16 10:00", B8="5", C5="10"))
    assert dados["B8"].tolist() == [1, 5]
    assert dados["C5"].tolist() == [0, 10]


# ---------------------------------------------------------------------------
# Inversão e "Não sei"
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("item", ITENS_INVERTIDOS)
def test_inversao(item):
    dados, _ = recod(*(resposta(f"2026-11-15 10:0{i}:00", **{item: o})
                       for i, o in enumerate(LIKERT)))
    assert dados[f"{item}_raw"].tolist() == [1, 2, 3, 4, 5]
    assert dados[item].tolist() == [5, 4, 3, 2, 1]


def test_item_nao_invertido_fica_igual():
    dados, _ = recod(resposta(C1=LIKERT[0]))
    assert dados["C1"].iloc[0] == 1


@pytest.mark.parametrize(
    "item, texto",
    [("C1", NSA), ("D2", NSA), ("E2", NAO_SEI), ("E7", NAO_SEI), ("D5", NAO_SEI), ("E8", NAO_SEI)],
)
def test_nao_sei_vira_ausente_e_marca_coluna(item, texto):
    dados, _ = recod(resposta(**{item: texto}))
    assert pd.isna(dados[item].iloc[0])
    assert bool(dados[f"{item}_nao_sei"].iloc[0])


def test_deveria_nao_aceita_nao_sei():
    with pytest.raises(ValorDesconhecido, match="E1"):
        recod(resposta(E1=NAO_SEI))


# ---------------------------------------------------------------------------
# C6
# ---------------------------------------------------------------------------
def _c6(valor):
    dados, inconsistencias = recod(resposta(C6=valor))
    return dados.iloc[0], inconsistencias


def test_c6_um_tipo():
    linha, inc = _c6("Arquitetura")
    assert bool(linha["C6_arquitetura"])
    assert linha[COLUNAS_TIPOS_C6].sum() == 1
    assert inc.empty


def test_c6_todos_os_tipos():
    linha, _ = _c6(";".join(TIPOS_C6))
    assert linha[COLUNAS_TIPOS_C6].all()


def test_c6_nenhum_sozinho():
    linha, inc = _c6("Nenhum")
    assert bool(linha["C6_nenhum"])
    assert not linha[COLUNAS_TIPOS_C6].any()
    assert inc.empty


@pytest.mark.parametrize("extra", ["Nenhum", NAO_SEI])
def test_c6_sem_tipo_junto_com_tipo_vale_o_tipo(extra):
    linha, inc = _c6(f"Código;{extra}")
    assert bool(linha["C6_codigo"])
    assert not linha["C6_nenhum"] and not linha["C6_nao_sei"]
    assert inc["item"].tolist() == ["C6"]


def test_c6_so_nao_sei_deixa_tipos_ausentes():
    linha, _ = _c6(NAO_SEI)
    assert bool(linha["C6_nao_sei"])
    assert linha[COLUNAS_TIPOS_C6].isna().all()


# ---------------------------------------------------------------------------
# Grupo de papel
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "papel, grupo",
    [*((p, "técnico") for p in PAPEIS_TECNICOS), *((p, "gestão") for p in PAPEIS_GESTAO)],
)
def test_grupo_das_opcoes_do_formulario(papel, grupo):
    dados, _ = recod(resposta(B2=papel))
    assert dados["grupo"].iloc[0] == grupo
    assert not dados["grupo_pendente"].iloc[0]


def test_outro_decidido_usa_reclassificacao():
    dados, _ = recod(resposta(B2="CTO"), reclassificacao=_reclass(CTO="gestão"))
    assert dados["grupo"].iloc[0] == "gestão"
    assert dados["B2"].iloc[0] == "CTO"


def test_outro_pendente():
    dados, _ = recod(resposta(B2="Analista de TI"))
    assert pd.isna(dados["grupo"].iloc[0])
    assert dados["grupo_pendente"].iloc[0]


def test_outro_fora_nao_deveria_chegar_aqui():
    with pytest.raises(ValueError, match="fora"):
        recod(resposta(B2="Designer UX"), reclassificacao=_reclass(**{"Designer UX": "fora"}))


# ---------------------------------------------------------------------------
# Ponta a ponta
# ---------------------------------------------------------------------------
def test_ponta_a_ponta_com_sintetico(tmp_path):
    df = carregar(sintetico.salvar(tmp_path / "respostas.csv", n=60))
    limpeza = limpar(df)
    dados, inconsistencias = recodificar(limpeza.validas, limpeza.reclassificacao)
    assert len(dados) == limpeza.resumo["validas"]
    assert dados["grupo"].notna().sum() + dados["grupo_pendente"].sum() == len(dados)
    assert set(dados["grupo"].dropna()) <= {"técnico", "gestão"}
    assert dados[["C1", "D4", "E1", "E7", "B3", "B8", "C5"]].apply(
        lambda c: c.dropna().map(float.is_integer).all()
    ).all()
    assert (inconsistencias["item"] == "C6").any()  # caso "Código;Nenhum" do gerador
    assert not np.isinf(dados.select_dtypes("number")).any().any()
