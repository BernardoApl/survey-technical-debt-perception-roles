"""Confiabilidade e validade convergente (#6): valores conferidos com cálculo à mão."""

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src import sintetico
from src.config import LIKERT, NAO_SEI, NSA, VINHETAS
from src.describe import preparar
from src.recode import recodificar
from src.reliability import (
    alfa_cronbach,
    confiabilidade,
    ic_feldt,
    validade_convergente,
)
from src.score import calcular_escores
from tests.fabrica import resposta, tabela

# 4 respostas × 3 itens. À mão:
#   variâncias (ddof 1): 5/3, 4/3, 4,75/3 -> soma 13,75/3
#   somas por resposta: 5, 7, 10, 13 -> variância 36,75/3
#   α = 3/2 · (1 − 13,75/36,75) = 1,5 · 23/36,75 = 0,938775...
MATRIZ = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 2, 4, 4], "c": [2, 3, 3, 5]})
ALFA_MATRIZ = 1.5 * 23 / 36.75


def test_alfa_a_mao():
    assert alfa_cronbach(MATRIZ) == pytest.approx(ALFA_MATRIZ)


def test_alfa_sem_item_a_mao():
    # sem "c": variâncias 5/3 + 4/3 = 3; somas 3, 4, 7, 8 -> variância 17/3
    # α = 2 · (1 − 3 / (17/3)) = 2 · 8/17 = 16/17
    assert alfa_cronbach(MATRIZ[["a", "b"]]) == pytest.approx(16 / 17)


def test_alfa_itens_iguais_e_1_e_casos_degenerados():
    assert alfa_cronbach(pd.DataFrame({"a": [1, 2, 3], "b": [1, 2, 3]})) == pytest.approx(1)
    assert math.isnan(alfa_cronbach(pd.DataFrame({"a": [3, 3], "b": [3, 3]})))  # soma constante
    assert math.isnan(alfa_cronbach(MATRIZ[["a"]]))  # 1 item
    assert math.isnan(alfa_cronbach(MATRIZ.head(1)))  # 1 resposta


def test_ic_feldt_pela_distribuicao_f():
    # n = 4, k = 3: gl 3 e 6
    inferior, superior = ic_feldt(ALFA_MATRIZ, 4, 3)
    assert inferior == pytest.approx(1 - (1 - ALFA_MATRIZ) * stats.f.ppf(0.975, 3, 6))
    assert superior == pytest.approx(1 - (1 - ALFA_MATRIZ) * stats.f.ppf(0.025, 3, 6))
    assert inferior < ALFA_MATRIZ < superior


def test_ic_feldt_igual_ao_pingouin():
    pg = pytest.importorskip("pingouin")  # ferramenta citada no protocolo (Seção 5.8)
    rng = np.random.default_rng(2026)
    base = rng.integers(1, 6, size=(40, 1))
    itens = pd.DataFrame(np.clip(base + rng.integers(-1, 2, size=(40, 4)), 1, 5))
    alfa_pg, ic_pg = pg.cronbach_alpha(data=itens, ci=0.95)
    alfa = alfa_cronbach(itens)
    assert alfa == pytest.approx(alfa_pg)
    assert np.round(ic_feldt(alfa, 40, 4), 3).tolist() == pytest.approx(list(ic_pg))


def _dados(*linhas):
    recodificados, _ = recodificar(tabela(*linhas))
    return calcular_escores(recodificados)


def _niv(i, c1, c2, c3, c4_marcado, **trocas):
    return resposta(f"2026-11-15 {10 + i:02d}:00", C1=LIKERT[c1 - 1], C2=LIKERT[c2 - 1],
                    C3=LIKERT[c3 - 1], C4=LIKERT[c4_marcado - 1], **trocas)


def test_confiabilidade_usa_c4_invertido_e_listwise():
    # C4 marcado = 6 − valor desejado. NIV recodificado:
    #   (1,2,2,2) (2,2,3,3) (3,4,3,4) (4,4,5,5) + uma resposta com "Não sei avaliar" em C1
    linhas = [_niv(0, 1, 2, 2, 4), _niv(1, 2, 2, 3, 3), _niv(2, 3, 4, 3, 2), _niv(3, 4, 4, 5, 1)]
    linhas.append(resposta("2026-11-15 15:00", C1=NSA))
    alfa, itens = confiabilidade(_dados(*linhas))
    niv = alfa.set_index("construto").loc["NIV"]
    esperado = alfa_cronbach(pd.DataFrame(
        {"C1": [1, 2, 3, 4], "C2": [2, 2, 4, 4], "C3": [2, 3, 3, 5], "C4": [2, 3, 4, 5]}))
    assert (niv["n"], niv["excluidas"], niv["k"]) == (4, 1, 4)
    assert niv["alfa"] == pytest.approx(esperado)
    assert niv["itens"] == "C1, C2, C3, C4 (R)"
    assert bool(niv["atinge_meta"]) is (esperado >= 0.70)

    c4 = itens.set_index(["construto", "item"]).loc[("NIV", "C4 (R)")]
    assert c4["alfa_sem_item"] == pytest.approx(ALFA_MATRIZ)  # sobram C1–C3 = MATRIZ
    # item-total corrigida: C4 = (2,3,4,5) contra C1+C2+C3 = (5,7,10,13)
    assert c4["r_item_total"] == pytest.approx(np.corrcoef([2, 3, 4, 5], [5, 7, 10, 13])[0, 1])


def test_confiabilidade_tem_os_quatro_construtos(tmp_path):
    d = preparar(sintetico.salvar(tmp_path / "respostas.csv", n=60))
    alfa, itens = confiabilidade(d)
    assert alfa["construto"].tolist() == ["NIV", "IMP", "POS", "PRA"]
    assert itens.groupby("construto").size().to_dict() == {"NIV": 4, "IMP": 4, "POS": 3, "PRA": 3}
    assert (alfa["n"] + alfa["excluidas"] == len(d)).all()
    # conferência manual: alfa do NIV recalculado direto das colunas
    assert alfa.loc[0, "alfa"] == pytest.approx(alfa_cronbach(d[["C1", "C2", "C3", "C4"]].dropna()))


# ---------------------------------------------------------------------------
# Validade convergente
# ---------------------------------------------------------------------------
def test_spearman_a_mao():
    # NIV = C1..C4 iguais (1..5) e C5 = (2, 1, 4, 3, 5): d² = 1+1+1+1+0 = 4
    # ρ = 1 − 6·4 / (5·24) = 0,8
    linhas = [resposta(f"2026-11-15 {10 + i:02d}:00", C5=str(c5),
                       **{c: LIKERT[v - 1] for c in ("C1", "C2", "C3")},
                       C4=LIKERT[5 - v])  # C4 invertido também vale v
              for i, (v, c5) in enumerate(zip([1, 2, 3, 4, 5], [2, 1, 4, 3, 5]))]
    v = validade_convergente(_dados(*linhas)).set_index("par").loc["NIV × C5"]
    assert v["n"] == 5
    assert v["rho"] == pytest.approx(0.8)
    assert not v["no_holm"]


def test_spearman_ignora_nao_sei_em_e7():
    linhas = [
        resposta(f"2026-11-15 {10 + i:02d}:00",
                 E2=VINHETAS[1][v], E4=VINHETAS[2][v], E6=VINHETAS[3][v],
                 E7=e7)
        for i, (v, e7) in enumerate([(0, "Nunca"), (1, "Raramente (algumas vezes por ano)"),
                                     (2, "Às vezes (cerca de uma vez por mês)"),
                                     (3, "Frequentemente (na maioria das sprints ou ciclos)"),
                                     (3, NAO_SEI)])
    ]
    v = validade_convergente(_dados(*linhas)).set_index("par").loc["PRA × E7"]
    assert v["n"] == 4
    assert v["rho"] == pytest.approx(1)


def test_spearman_com_poucos_pares_fica_nan():
    v = validade_convergente(_dados(resposta())).set_index("par")
    assert v["rho"].isna().all() and v["p_valor"].isna().all()
