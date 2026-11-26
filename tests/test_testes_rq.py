import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.testes_rq import _fisher_exato, holm, salvar_testes, testes_rq as calcular


def dados():
    rng = np.random.default_rng(41)
    n = 50
    d = pd.DataFrame({"grupo": ["técnico"] * 30 + ["gestão"] * 20})
    for col in ("NIV", "IMP", "POS", "PRA", "B3", "B5", "E7"):
        d[col] = rng.integers(1, 5, n).astype(float)
    d["DIST"] = d.POS - d.PRA
    d["D5"] = ["A"] * 24 + ["B"] * 21 + ["rara"] * 5
    d["E8"] = ["X"] * 23 + ["Y"] * 24 + ["rara"] * 3
    return d


def test_familia_holm_mantem_nao_executavel():
    ajustados = holm([0.001, np.nan, 0.01, 0.009], familia=4)
    assert ajustados[0] == pytest.approx(0.004)
    assert np.isnan(ajustados[1])
    assert ajustados[2] == pytest.approx(0.027)
    assert ajustados[3] == pytest.approx(0.027)


def test_fisher_exato_confere_scipy():
    t = np.array([[1, 9], [11, 3]])
    assert _fisher_exato(t) == pytest.approx(stats.fisher_exact(t).pvalue)


def test_14_testes_csv_e_margens(tmp_path):
    d = dados()
    saida = calcular(d)
    assert len(saida) == 14
    assert saida.rq.value_counts().to_dict() == {"RQ1": 1, "RQ2": 2, "RQ3": 5, "RQ4": 6}
    assert saida.p_bruto.notna().all()
    assert saida.p_holm.ge(saida.p_bruto).all()
    assert saida.loc[0, "margem_tecnico_pp"] == pytest.approx(100 * 1.96 * math.sqrt(.25 / 30))
    assert not saida.baixo_poder.any()
    assert "rara" in saida.loc[7, "categorias_agrupadas"]
    assert "margem_pp" in saida.loc[7, "proporcoes"]
    csv = pd.read_csv(salvar_testes(d, tmp_path))
    assert len(csv) == 14


def test_nao_executavel_continua_no_holm():
    d = dados()
    d["B5"] = 1
    d.loc[d.grupo == "gestão", "NIV"] = np.nan
    r = calcular(d)
    assert r.loc[0, "motivo"]
    assert pd.isna(r.loc[0, "p_holm"])
    assert (r.loc[r.comparacao.eq("B5"), "motivo"] != "").all()
    assert np.allclose(r.p_holm, holm(r.p_bruto), equal_nan=True)


def test_pares_grupo_pendente_e_baixo_poder():
    d = dados().iloc[:32].copy()
    d.loc[0, "grupo"] = None
    d.loc[1, "PRA"] = np.nan
    r = calcular(d)
    wilcoxon = r.iloc[4]
    assert wilcoxon.n == 31
    assert wilcoxon.n_sem_grupo == 1
    assert wilcoxon.baixo_poder
    assert r.iloc[0].n_sem_grupo == 0


def test_todos_pares_iguais_e_categoria_unica():
    d = dados()
    d.PRA = d.POS
    d.D5 = "A"
    r = calcular(d)
    assert "zero" in r.iloc[4].motivo
    assert "categorias" in r.iloc[2].motivo


def test_permutacao_reprodutivel_e_desvio(monkeypatch):
    import src.testes_rq as modulo
    monkeypatch.setattr(modulo, "LIMITE_TABELAS", 1)
    monkeypatch.setattr(modulo, "PERMUTACOES", 999)
    primeiro = calcular(dados()).iloc[2]
    segundo = calcular(dados()).iloc[2]
    assert primeiro.teste == "qui-quadrado por permutação"
    assert primeiro.p_bruto == segundo.p_bruto
    assert "DEVIATIONS.md" in primeiro.desvio


def test_pipeline_com_csv_sintetico(tmp_path):
    from src.describe import preparar
    from src.sintetico import salvar

    arquivo = salvar(tmp_path / "sintetico.csv", n=80)
    resultado = pd.read_csv(salvar_testes(preparar(arquivo), tmp_path))
    assert len(resultado) == 14
    assert (resultado.p_bruto.notna() | resultado.motivo.notna()).all()
