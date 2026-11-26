import json
import shutil

import pandas as pd

from src import sintetico
from src.config import CSV_LIVRO_CODIGOS
from src.pipeline import executar


def preparar(tmp_path):
    manual = tmp_path / "manual"
    manual.mkdir()
    shutil.copyfile(CSV_LIVRO_CODIGOS, manual / CSV_LIVRO_CODIGOS.name)
    bruto = sintetico.salvar(tmp_path / "bruto.csv", n=35)
    return bruto, manual, tmp_path / "processado", tmp_path / "saidas"


def test_pipeline_regenera_e_respeita_privacidade(tmp_path):
    bruto, manual, processado, saidas = preparar(tmp_path)
    resultado = executar(bruto, manual, processado, saidas)
    resumo = json.loads((saidas / "resumo_amostra.json").read_text(encoding="utf-8"))
    desvios = json.loads((saidas / "desvios.json").read_text(encoding="utf-8"))
    assert resumo["recebidas"] == resumo["validas"] + resumo["descartadas"]
    assert sum(resumo["validas_por_grupo"].values()) == resumo["validas"]
    assert isinstance(resumo["outro_pendentes"], int)
    assert desvios["amostra"]["abaixo_minimo"]
    assert desvios["gestao"]["abaixo_minimo"]
    assert desvios["prorrogacao"]["recebidas"] > 0
    assert desvios["prorrogacao"]["validas"] <= desvios["prorrogacao"]["recebidas"]
    assert len(pd.read_csv(saidas / "testes_rq.csv")) == 14
    assert resultado["pendencias"]["anonimizacao"] > 0
    for nome in ("frequencias.csv", "confiabilidade.csv", "testes_rq.csv",
                 "frequencia_codigos.csv", "pendencias_abertas.json", "desvios.json"):
        assert (saidas / nome).exists()
    for arquivo in [*saidas.iterdir(), *processado.iterdir()]:
        assert "Analista de TI" not in arquivo.read_text(encoding="utf-8-sig")
    anteriores = {p.name: p.read_bytes() for p in saidas.iterdir()}
    executar(bruto, manual, processado, saidas)
    assert anteriores == {p.name: p.read_bytes() for p in saidas.iterdir()}


def test_pipeline_preserva_classificacao_manual(tmp_path):
    bruto, manual, processado, saidas = preparar(tmp_path)
    executar(bruto, manual, processado, saidas)
    arquivo = manual / "reclassificacao_outro.csv"
    reclass = pd.read_csv(arquivo, keep_default_na=False)
    linha = reclass.texto_original.eq("Analista de TI")
    reclass.loc[linha, ["grupo", "decidido_por", "justificativa"]] = [
        "gestão", "Bernardo", "decide prioridades"]
    reclass.to_csv(arquivo, index=False)
    resultado = executar(bruto, manual, processado, saidas)
    nova = pd.read_csv(arquivo, keep_default_na=False)
    assert nova.loc[linha, "grupo"].iloc[0] == "gestão"
    assert resultado["resumo"]["validas_por_grupo"]["gestão"] >= 1


def test_nao_executaveis_sao_registrados(tmp_path):
    bruto, manual, processado, saidas = preparar(tmp_path)
    sintetico.salvar(bruto, n=0)
    resultado = executar(bruto, manual, processado, saidas)
    testes = pd.read_csv(saidas / "testes_rq.csv")
    nao_executados = testes[testes.motivo.notna()]
    assert len(nao_executados) > 0
    assert len(resultado["desvios"]["testes_nao_executaveis"]) == len(nao_executados)


def test_cenarios_sao_condicionais_e_fora_do_holm():
    from src.testes_rq import testes_por_cenario

    dados = pd.DataFrame({"grupo": ["técnico", "técnico", "gestão", "gestão"],
                          "E1": [1, 2, 3, 4], "E2": [2, 1, 4, 3],
                          "E3": [2, 3, 1, 4], "E4": [1, 3, 2, 4],
                          "E5": [4, 2, 3, 1], "E6": [3, 1, 2, 2]})
    alfa = pd.DataFrame({"construto": ["POS", "PRA"], "alfa": [0.5, 0.8]})
    tabela, estado = testes_por_cenario(dados, alfa)
    assert len(tabela) == 9
    assert estado["executada"] and estado["fora_do_holm"]
    assert estado["alfa_abaixo_meta"] == ["POS"]
    assert "p_holm" not in tabela
    alfa["alfa"] = [0.7, 0.8]
    tabela, estado = testes_por_cenario(dados, alfa)
    assert tabela.empty and not estado["executada"]
    alfa.loc[0, "alfa"] = float("nan")
    _, estado = testes_por_cenario(dados, alfa)
    assert estado["alfa_indefinido"] == ["POS"]
