"""Estatística descritiva (#6): valores conferidos com cálculo à mão."""

import math

import pandas as pd
import pytest

from src import sintetico
from src.clean import limpar
from src.config import LIKERT, NAO_SEI, NSA, PAPEIS_GESTAO, VINHETAS
from src.describe import (
    ITENS_FREQUENCIA,
    SEM_GRUPO,
    concordancia_likert,
    distribuicao_likert,
    frequencias,
    margem_erro,
    nao_sei,
    perfil,
    preparar,
    resumo_escores,
    salvar_tabelas,
    tabelas,
)
from src.load import carregar
from src.recode import recodificar
from src.score import calcular_escores
from tests.fabrica import resposta, tabela

GESTOR = PAPEIS_GESTAO[0]


def dados(*linhas):
    recodificados, _ = recodificar(tabela(*linhas))
    return calcular_escores(recodificados)


def _hora(i):
    return f"2026-11-15 {10 + i:02d}:00"


def linha(tab, **filtro):
    sel = tab
    for coluna, valor in filtro.items():
        sel = sel[sel[coluna] == valor]
    assert len(sel) == 1, filtro
    return sel.iloc[0]


# ---------------------------------------------------------------------------
# Margem de erro
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n, esperado", [(60, 12.7), (50, 13.9), (40, 15.5), (20, 21.9),
                                         (15, 25.3)])
def test_margem_pior_caso_bate_com_a_tabela_do_protocolo(n, esperado):
    assert round(100 * margem_erro(0.5, n), 1) == esperado


def test_margem_sem_respostas_e_nan():
    assert math.isnan(margem_erro(0.5, 0))


# ---------------------------------------------------------------------------
# Frequências
# ---------------------------------------------------------------------------
def test_frequencia_total_e_por_grupo():
    # 3 técnicos (B3: 3 a 5, 3 a 5, Mais de 10) e 1 gestor (B3: 3 a 5)
    d = dados(
        resposta(_hora(0), B3="3 a 5 anos"),
        resposta(_hora(1), B3="3 a 5 anos"),
        resposta(_hora(2), B3="Mais de 10 anos"),
        resposta(_hora(3), B3="3 a 5 anos", B2=GESTOR),
    )
    f = frequencias(d)
    total = linha(f, item="B3", opcao="3 a 5 anos", recorte="total")
    assert (total["n"], total["k"], total["pct"]) == (4, 3, 75)
    # e = 1,96 * sqrt(0,75 * 0,25 / 4) = 0,42435 -> 42,4 p.p.
    assert total["margem_pp"] == pytest.approx(42.435, abs=1e-3)
    tecnico = linha(f, item="B3", opcao="3 a 5 anos", recorte="técnico")
    assert (tecnico["n"], tecnico["k"]) == (3, 2)
    gestao = linha(f, item="B3", opcao="3 a 5 anos", recorte="gestão")
    assert (gestao["n"], gestao["k"], gestao["pct"]) == (1, 1, 100)
    # opção sem resposta aparece com 0
    assert linha(f, item="B3", opcao="Menos de 1 ano", recorte="total")["k"] == 0


def test_preparar_parte_do_csv_bruto(tmp_path):
    d = preparar(sintetico.salvar(tmp_path / "respostas.csv", n=30))
    assert {"grupo", "NIV", "IMP", "POS", "PRA", "DIST", "C4_raw"} <= set(d.columns)
    assert d["resp_id"].is_unique


def test_frequencia_usa_a_resposta_marcada_nos_invertidos():
    # C4 "Concordo totalmente" vira 1 depois da inversão, mas a frequência mostra o que foi marcado
    f = frequencias(dados(resposta(C4=LIKERT[4])))
    assert linha(f, item="C4", opcao=LIKERT[4], recorte="total")["k"] == 1
    assert linha(f, item="C4", opcao=LIKERT[0], recorte="total")["k"] == 0


def test_nao_sei_e_opcao_na_frequencia():
    d = dados(resposta(_hora(0), C1=NSA, E2=NAO_SEI, D5=NAO_SEI, E8=NAO_SEI),
              resposta(_hora(1)))
    f = frequencias(d)
    for item, texto in (("C1", NSA), ("E2", NAO_SEI), ("D5", NAO_SEI), ("E8", NAO_SEI)):
        r = linha(f, item=item, opcao=texto, recorte="total")
        assert (r["n"], r["k"]) == (2, 1), item
    ns = nao_sei(f)
    assert set(ns["opcao"]) <= {NSA, NAO_SEI}
    assert linha(ns, item="C1", recorte="total")["pct"] == 50


def test_b2_outro_aparece_so_como_outro():
    f = frequencias(dados(resposta(B2="Engenheiro de software na Empresa X")))
    b2 = f[(f["item"] == "B2") & (f["recorte"] == "total")]
    assert "Engenheiro de software na Empresa X" not in set(f["opcao"])
    assert linha(b2, opcao="Outro")["k"] == 1


def test_grupo_pendente_aparece_no_perfil_e_so_no_total():
    f = frequencias(dados(resposta(_hora(0)), resposta(_hora(1), B2="CTO")))
    p = perfil(f)
    assert linha(p, item="grupo", opcao=SEM_GRUPO)["k"] == 1
    assert set(p.loc[p["item"] == "grupo", "recorte"]) == {"total"}
    # a resposta sem grupo conta no total, mas em nenhum grupo
    b3_total = f[(f["item"] == "B3") & (f["recorte"] == "total")]["k"].sum()
    b3_grupos = f[(f["item"] == "B3") & (f["recorte"] != "total")]["k"].sum()
    assert (b3_total, b3_grupos) == (2, 1)


def test_c6_multipla_escolha():
    d = dados(
        resposta(_hora(0), C6="Código;Testes"),
        resposta(_hora(1), C6="Código"),
        resposta(_hora(2), C6="Nenhum"),
        resposta(_hora(3), C6=NAO_SEI),
    )
    f = frequencias(d)
    # tipos: n exclui quem marcou só "Não sei" (3 de 4)
    codigo = linha(f, item="C6", opcao="Código", recorte="total")
    assert (codigo["n"], codigo["k"]) == (3, 2)
    assert linha(f, item="C6", opcao="Testes", recorte="total")["k"] == 1
    # "Nenhum" e "Não sei": n são todas as respostas
    for opcao in ("Nenhum", NAO_SEI):
        r = linha(f, item="C6", opcao=opcao, recorte="total")
        assert (r["n"], r["k"]) == (4, 1), opcao


def test_escala_numerica_tem_todas_as_opcoes():
    f = frequencias(dados(resposta(C5="0"), resposta(_hora(1), C5="10")))
    c5 = f[(f["item"] == "C5") & (f["recorte"] == "total")]
    assert c5["opcao"].tolist() == [str(i) for i in range(11)]
    assert c5.set_index("opcao").loc[["0", "10"], "k"].tolist() == [1, 1]


# ---------------------------------------------------------------------------
# Concordância Likert
# ---------------------------------------------------------------------------
def test_concordancia_conta_4_e_5_e_ignora_nao_sei():
    # C1: Concordo totalmente, Concordo parcialmente, Neutro, Discordo, Não sei avaliar
    d = dados(*(resposta(_hora(i), C1=v) for i, v in
                enumerate([LIKERT[4], LIKERT[3], LIKERT[2], LIKERT[0], NSA])))
    c1 = linha(concordancia_likert(d), item="C1", recorte="total")
    assert (c1["n"], c1["k"], c1["pct"]) == (4, 2, 50)
    assert c1["margem_pp"] == pytest.approx(100 * 1.96 * math.sqrt(0.25 / 4))


def test_concordancia_nos_invertidos_e_com_a_frase_do_formulario():
    d = dados(resposta(_hora(0), D2=LIKERT[4]), resposta(_hora(1), D2=LIKERT[0]))
    d2 = linha(concordancia_likert(d), item="D2", recorte="total")
    assert bool(d2["invertido"])
    assert (d2["n"], d2["k"]) == (2, 1)  # só quem marcou "Concordo totalmente"


def test_concordancia_por_grupo():
    d = dados(resposta(_hora(0), C2=LIKERT[4]), resposta(_hora(1), C2=LIKERT[1], B2=GESTOR))
    c = concordancia_likert(d)
    assert linha(c, item="C2", recorte="técnico")["pct"] == 100
    assert linha(c, item="C2", recorte="gestão")["pct"] == 0


def test_distribuicao_likert_a_mao():
    # C1: totalmente, parcialmente, neutro, discordo totalmente, não sei -> n = 4 (sem o "não sei")
    d = dados(*(resposta(_hora(i), C1=v) for i, v in
                enumerate([LIKERT[4], LIKERT[3], LIKERT[2], LIKERT[0], NSA])))
    dist = distribuicao_likert(frequencias(d))
    c1 = dist[(dist["item"] == "C1") & (dist["recorte"] == "total")].set_index("opcao")
    assert c1["k"].tolist() == [1, 0, 1, 1, 1]
    assert (c1["n"] == 4).all() and (c1["nao_sei"] == 1).all()
    assert c1.loc[LIKERT[2], "pct"] == 25
    assert NSA not in c1.index


def test_distribuicao_bate_com_concordancia(sintetico_bruto):
    _, d = sintetico_bruto
    dist = distribuicao_likert(frequencias(d))
    conc = concordancia_likert(d).set_index(["item", "recorte"])
    soma = dist.groupby(["item", "recorte"])["pct"].sum()
    assert soma.round(6).eq(100).all()
    concordam = dist[dist["opcao"].isin(LIKERT[3:])].groupby(["item", "recorte"])
    for chave, pct in concordam["pct"].sum().items():
        assert pct == pytest.approx(conc.loc[chave, "pct"]), chave
        assert concordam["n"].first()[chave] == conc.loc[chave, "n"], chave


# ---------------------------------------------------------------------------
# Escores
# ---------------------------------------------------------------------------
def test_mediana_e_iqr_a_mao():
    # C5 = 1..6: mediana 3,5; Q1 = 1 + 0,25·5 = 2,25; Q3 = 1 + 0,75·5 = 4,75; IQR 2,5
    d = dados(*(resposta(_hora(i), C5=str(v)) for i, v in enumerate([1, 2, 3, 4, 5, 6])))
    r = linha(resumo_escores(d), escore="C5", recorte="total")
    assert (r["n"], r["mediana"], r["q1"], r["q3"], r["iqr"]) == (6, 3.5, 2.25, 4.75, 2.5)


def test_escore_ausente_conta_em_ausentes():
    d = dados(resposta(_hora(0)), resposta(_hora(1), C1=NSA, C2=NSA, C3=NSA))
    r = linha(resumo_escores(d), escore="NIV", recorte="total")
    assert (r["n"], r["ausentes"]) == (1, 1)


def test_escores_por_grupo():
    d = dados(resposta(_hora(0), E1=VINHETAS[1][3], E3=VINHETAS[2][3], E5=VINHETAS[3][3]),
              resposta(_hora(1), B2=GESTOR, E1=VINHETAS[1][0], E3=VINHETAS[2][0],
                       E5=VINHETAS[3][0]))
    r = resumo_escores(d)
    assert linha(r, escore="POS", recorte="técnico")["mediana"] == 4
    assert linha(r, escore="POS", recorte="gestão")["mediana"] == 1
    assert linha(r, escore="POS", recorte="total")["mediana"] == 2.5


# ---------------------------------------------------------------------------
# Conferência com cálculo manual na amostra sintética
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def sintetico_bruto(tmp_path_factory):
    caminho = sintetico.salvar(tmp_path_factory.mktemp("sint") / "respostas.csv", n=150)
    validas = limpar(carregar(caminho)).validas
    recodificados, _ = recodificar(validas)
    return validas, calcular_escores(recodificados)


def test_frequencias_batem_com_contagem_do_texto_bruto(sintetico_bruto):
    """Conta direto no texto do CSV (sem recodificação) e compara com a tabela."""
    validas, d = sintetico_bruto
    f = frequencias(d).query("recorte == 'total'").set_index(["item", "opcao"])
    for item in ("B3", "B6", "C1", "C4", "D2", "E2", "E7", "E8", "D5"):
        for opcao, k in validas[item].value_counts().items():
            assert f.loc[(item, opcao), "k"] == k, (item, opcao)
            assert f.loc[(item, opcao), "n"] == validas[item].notna().sum()


def test_concordancia_bate_com_contagem_do_texto_bruto(sintetico_bruto):
    validas, d = sintetico_bruto
    c = concordancia_likert(d).query("recorte == 'total'").set_index("item")
    for item in ("C1", "C4", "D2", "D4"):
        respostas = validas[item]
        k = respostas.isin(LIKERT[3:]).sum()
        n = respostas.isin(LIKERT).sum()  # "Não sei avaliar" fica fora
        assert (c.loc[item, "k"], c.loc[item, "n"]) == (k, n), item
        assert c.loc[item, "pct"] == pytest.approx(100 * k / n)


def test_mediana_bate_com_calculo_direto(sintetico_bruto):
    validas, d = sintetico_bruto
    r = resumo_escores(d).query("recorte == 'total'").set_index("escore")
    c5 = pd.to_numeric(validas["C5"]).sort_values().reset_index(drop=True)
    n = len(c5)
    meio = c5[n // 2] if n % 2 else (c5[n // 2 - 1] + c5[n // 2]) / 2
    assert r.loc["C5", "mediana"] == meio


def test_tabelas_consistentes_no_sintetico(sintetico_bruto):
    _, d = sintetico_bruto
    f = frequencias(d)
    assert set(f["item"]) == set(ITENS_FREQUENCIA)
    # itens de uma opção: as opções somam n e 100% em cada recorte
    uma_opcao = f[f["item"] != "C6"].groupby(["item", "recorte"])
    assert (uma_opcao["k"].sum() == uma_opcao["n"].first()).all()
    assert uma_opcao["pct"].sum().round(6).eq(100).all()
    # técnico + gestão + sem grupo = total
    b3 = f[f["item"] == "B3"].groupby("recorte")["k"].sum()
    sem_grupo = linha(f, item="grupo", opcao=SEM_GRUPO)["k"]
    assert b3["técnico"] + b3["gestão"] + sem_grupo == b3["total"]


def test_salvar_todas_as_tabelas(tmp_path, sintetico_bruto):
    _, d = sintetico_bruto
    geradas = tabelas(d)
    salvar_tabelas(geradas, tmp_path)
    for nome in ("frequencias", "perfil", "nao_sei", "concordancia_likert", "distribuicao_likert",
                 "escores_por_grupo", "confiabilidade", "confiabilidade_itens",
                 "validade_convergente"):
        assert len(pd.read_csv(tmp_path / f"{nome}.csv")) == len(geradas[nome]), nome
