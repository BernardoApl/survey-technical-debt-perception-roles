import pandas as pd
import pytest

from src import sintetico
from src.clean import limpar
from src.config import LIKERT, NAO_SEI, NSA, VINHETAS
from src.load import carregar
from src.recode import recodificar
from src.score import calcular_escores
from tests.fabrica import resposta, tabela


def escores(**trocas):
    dados, _ = recodificar(tabela(resposta(**trocas)))
    return calcular_escores(dados).iloc[0]


def test_niv_usa_c4_invertido():
    # C1=5, C2=5, C3=5, C4="Discordo totalmente"=1 -> invertido 5 -> mediana 5
    linha = escores(C1=LIKERT[4], C2=LIKERT[4], C3=LIKERT[4], C4=LIKERT[0])
    assert linha["NIV"] == 5


def test_imp_usa_d2_invertido():
    # D1=1, D2="Concordo totalmente"=5 -> invertido 1, D3=1, D4=1 -> mediana 1
    linha = escores(D1=LIKERT[0], D2=LIKERT[4], D3=LIKERT[0], D4=LIKERT[0])
    assert linha["IMP"] == 1


def test_mediana_par_pode_dar_meio():
    # C1=2, C2=3, C3=4, C4="Discordo parcialmente"=2 -> invertido 4 -> {2,3,4,4} -> 3,5
    linha = escores(C1=LIKERT[1], C2=LIKERT[2], C3=LIKERT[3], C4=LIKERT[1])
    assert linha["NIV"] == 3.5


def test_mediana_ignora_nao_sei():
    # C1=NSA, C2=2, C3=4, C4=invertido 4 -> {2,4,4} -> 4
    linha = escores(C1=NSA, C2=LIKERT[1], C3=LIKERT[3], C4=LIKERT[1])
    assert linha["NIV"] == 4


def test_metade_de_nao_sei_ainda_tem_escore():
    linha = escores(C1=NSA, C2=NSA, C3=LIKERT[3], C4=LIKERT[1])
    assert linha["NIV"] == 4


def test_mais_da_metade_de_nao_sei_fica_ausente():
    assert pd.isna(escores(C1=NSA, C2=NSA, C3=NSA)["NIV"])
    assert pd.isna(escores(E2=NAO_SEI, E4=NAO_SEI)["PRA"])


def test_pra_com_um_nao_sei_usa_os_outros_dois():
    linha = escores(E2=NAO_SEI, E4=VINHETAS[2][0], E6=VINHETAS[3][2])
    assert linha["PRA"] == 2  # mediana de {1, 3}


def test_pos_pra_e_dist():
    linha = escores(
        E1=VINHETAS[1][3], E3=VINHETAS[2][2], E5=VINHETAS[3][3],  # 4, 3, 4 -> POS 4
        E2=VINHETAS[1][0], E4=VINHETAS[2][1], E6=VINHETAS[3][1],  # 1, 2, 2 -> PRA 2
    )
    assert (linha["POS"], linha["PRA"], linha["DIST"]) == (4, 2, 2)
    assert (linha["DIST1"], linha["DIST2"], linha["DIST3"]) == (3, 1, 2)


def test_dist_ausente_quando_pra_ausente():
    linha = escores(E2=NAO_SEI, E4=NAO_SEI)
    assert pd.isna(linha["DIST"]) and pd.isna(linha["DIST1"])
    assert not pd.isna(linha["DIST3"])


def test_atn_nao_entra_em_escore():
    base = escores()
    com_atn = escores(ATN=LIKERT[1])
    assert base[["NIV", "IMP"]].equals(com_atn[["NIV", "IMP"]])


def test_construto_ausente_bate_com_a_limpeza(tmp_path):
    df = carregar(sintetico.salvar(tmp_path / "respostas.csv", n=150))
    limpeza = limpar(df)
    dados, _ = recodificar(limpeza.validas, limpeza.reclassificacao)
    resultado = calcular_escores(dados).set_index("resp_id")
    log_6 = limpeza.log[limpeza.log["etapa"] == 6]
    for construto in ("NIV", "IMP", "POS", "PRA"):
        no_log = set(log_6.loc[log_6["motivo"].str.contains(f"({construto}:", regex=False),
                               "resp_id"])
        sem_escore = set(resultado.index[resultado[construto].isna()])
        assert no_log == sem_escore, construto


@pytest.mark.parametrize("construto, minimo, maximo",
                         [("NIV", 1, 5), ("IMP", 1, 5), ("POS", 1, 4), ("PRA", 1, 4)])
def test_escores_dentro_da_escala(tmp_path, construto, minimo, maximo):
    df = carregar(sintetico.salvar(tmp_path / "respostas.csv", n=60))
    limpeza = limpar(df)
    dados, _ = recodificar(limpeza.validas, limpeza.reclassificacao)
    valores = calcular_escores(dados)[construto].dropna()
    assert valores.between(minimo, maximo).all()
