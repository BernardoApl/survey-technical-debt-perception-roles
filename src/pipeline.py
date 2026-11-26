"""Pipeline da análise principal: python -m src.pipeline.

Arquivos manuais são entradas persistentes: o pipeline cria as pendências sem
inventar classificações, anonimizações, códigos ou consensos humanos.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src import abertas, describe
from src.clean import ler_reclassificacao, limpar, salvar_limpeza, salvar_reclassificacao
from src.config import (CSV_BRUTO, CSV_LIVRO_CODIGOS, CSV_RECLASSIFICACAO,
                        DIR_MANUAL, DIR_PROCESSADO, DIR_SAIDAS, META_GESTAO,
                        MINIMO_GESTAO, MINIMO_VALIDAS, PERIODO_PREREGISTRADO,
                        PERIODO_PRINCIPAL, SEED)
from src.load import carregar
from src.recode import recodificar
from src.score import calcular_escores
from src.testes_rq import testes_por_cenario, testes_rq


def executar(caminho: Path = CSV_BRUTO, dir_manual: Path = DIR_MANUAL,
             dir_processado: Path = DIR_PROCESSADO, dir_saidas: Path = DIR_SAIDAS) -> dict:
    """Gera saídas a partir do CSV e das decisões humanas existentes."""
    caminho, dir_manual = Path(caminho), Path(dir_manual)
    dir_processado, dir_saidas = Path(dir_processado), Path(dir_saidas)
    bruto = carregar(caminho)
    reclass = ler_reclassificacao(dir_manual / CSV_RECLASSIFICACAO.name)
    limpeza = limpar(bruto, PERIODO_PRINCIPAL, reclass)
    sensibilidade = limpar(bruto, PERIODO_PREREGISTRADO, reclass)
    dados, inconsistencias = recodificar(limpeza.validas, limpeza.reclassificacao)
    dados = calcular_escores(dados)
    resumo = limpeza.resumo
    resumo["validas_por_grupo"] = {
        "técnico": int(dados.grupo.eq("técnico").sum()),
        "gestão": int(dados.grupo.eq("gestão").sum()),
        "sem_grupo": int(dados.grupo.isna().sum()),
    }
    if resumo["recebidas"] != resumo["validas"] + resumo["descartadas"]:
        raise ValueError("Inconsistência na limpeza: recebidas != válidas + descartadas")
    if sum(resumo["validas_por_grupo"].values()) != resumo["validas"]:
        raise ValueError("Inconsistência: grupos não somam o número de respostas válidas")

    revisao, planilhas, consenso = abertas.ler_manuais(dir_manual)
    livro = abertas.ler_livro(dir_manual / CSV_LIVRO_CODIGOS.name)
    resultado_abertas = abertas.processar(limpeza.validas, livro, revisao, planilhas,
                                          consenso, limpeza.reclassificacao,
                                          sensibilidade.validas)
    tabelas = describe.tabelas(dados)
    testes = testes_rq(dados)
    cenarios, estado_cenarios = testes_por_cenario(dados, tabelas["confiabilidade"])

    # Calcula ocorrências independentemente do resultado dos testes.
    inicio = PERIODO_PREREGISTRADO[1] + pd.Timedelta(seconds=1)
    fim = PERIODO_PRINCIPAL[1]
    recebidas_prorrogacao = int(bruto.timestamp.between(inicio, fim).sum())
    validas_prorrogacao = int(limpeza.validas.timestamp.between(inicio, fim).sum())
    gestao = resumo["validas_por_grupo"]["gestão"]
    desvios = {
        "semente": SEED,
        "prorrogacao": {"inicio": inicio.isoformat(), "fim": fim.isoformat(),
                         "recebidas": recebidas_prorrogacao, "validas": validas_prorrogacao},
        "amostra": {"validas": resumo["validas"], "minimo": MINIMO_VALIDAS,
                    "abaixo_minimo": resumo["validas"] < MINIMO_VALIDAS},
        "gestao": {"validas": gestao, "meta": META_GESTAO, "minimo": MINIMO_GESTAO,
                   "abaixo_meta": gestao < META_GESTAO, "abaixo_minimo": gestao < MINIMO_GESTAO,
                   "sem_grupo_pendente": resumo["validas_por_grupo"]["sem_grupo"]},
        "testes_nao_executaveis": testes.loc[testes.motivo.ne(""),
                                               ["id", "rq", "variavel", "comparacao", "motivo"]].to_dict("records"),
        "testes_por_permutacao": testes.loc[testes.desvio.ne(""),
                                              ["id", "rq", "variavel", "desvio"]].to_dict("records"),
        "pendencias_abertas": resultado_abertas.pendencias,
        "testes_por_cenario": estado_cenarios,
    }

    # Nenhum arquivo é gravado antes da validação das entradas e dos cálculos.
    salvar_limpeza(limpeza, dir_saidas=dir_saidas, dir_processado=dir_processado)
    salvar_reclassificacao(limpeza.reclassificacao, dir_manual / CSV_RECLASSIFICACAO.name)
    abertas.salvar_abertas(resultado_abertas, dir_manual, dir_processado, dir_saidas)
    describe.salvar_tabelas(tabelas, dir_saidas)
    testes.to_csv(dir_saidas / "testes_rq.csv", index=False)
    cenarios.to_csv(dir_saidas / "testes_cenarios_exploratorios.csv", index=False)
    inconsistencias.to_csv(dir_saidas / "inconsistencias_recodificacao.csv", index=False)
    (dir_saidas / "desvios.json").write_text(
        json.dumps(desvios, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"resumo": resumo, "desvios": desvios, "pendencias": resultado_abertas.pendencias}


def main():
    resultado = executar()
    resumo = resultado["resumo"]
    print(f"Recebidas: {resumo['recebidas']}; válidas: {resumo['validas']}; "
          f"descartadas: {resumo['descartadas']}.")
    print(f"Recebidas na prorrogação: {resultado['desvios']['prorrogacao']['recebidas']}.")
    print(abertas.relatorio(resultado["pendencias"], resumo["outro_pendentes"]))
    print(f"Saídas regeneradas em {DIR_SAIDAS} e {DIR_PROCESSADO}.")


if __name__ == "__main__":
    main()
