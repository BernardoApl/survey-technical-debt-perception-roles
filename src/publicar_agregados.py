"""Prepara uma fotografia agregada para o dashboard público, sem respostas individuais.

Uso: python -m src.publicar_agregados. Revise o arquivo antes de publicá-lo.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.clean import ler_reclassificacao, limpar
from src.config import CSV_BRUTO, PERIODO_PRINCIPAL, RAIZ
from src.describe import tabelas
from src.load import carregar
from src.recode import recodificar
from src.score import calcular_escores
from src.testes_rq import testes_rq

DESTINO = RAIZ / "data" / "publico" / "resultados.json"


def _registros(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", force_ascii=False))


def agregar(limpeza, dados: pd.DataFrame) -> dict:
    """Somente tabelas numéricas e categorias fechadas, sem textos nem IDs."""
    descricao = tabelas(dados)
    testes = testes_rq(dados)
    # Nomes de cargo livres nunca são exportados; frequências usa 'Outro'.
    resumo = limpeza.resumo
    perfis_rq4 = []
    for variavel in ("B3", "B5"):
        for escore in ("NIV", "IMP", "POS"):
            pares = dados[[variavel, escore]].dropna()
            for categoria, valores in pares.groupby(variavel)[escore]:
                perfis_rq4.append({"variavel": variavel, "escore": escore,
                                   "categoria": int(categoria), "n": int(valores.count()),
                                   "mediana": float(valores.median())})
    # A lista de pendências no resumo contém texto digitado, portanto só exportamos a quantidade.
    return {
        "versao": 1,
        "periodo": resumo["periodo"],
        "amostra": {"recebidas": resumo["recebidas"], "validas": resumo["validas"],
                    "descartadas": resumo["descartadas"],
                    "descartes_por_etapa": resumo["descartes_por_etapa"],
                    "tecnico": int(dados.grupo.eq("técnico").sum()),
                    "gestao": int(dados.grupo.eq("gestão").sum()),
                    "sem_grupo": int(dados.grupo.isna().sum())},
        "frequencias": _registros(descricao["frequencias"]),
        "concordancia_likert": _registros(descricao["concordancia_likert"]),
        "distribuicao_likert": _registros(descricao["distribuicao_likert"]),
        "escores_por_grupo": _registros(descricao["escores_por_grupo"]),
        "confiabilidade": _registros(descricao["confiabilidade"]),
        "confiabilidade_itens": _registros(descricao["confiabilidade_itens"]),
        "validade_convergente": _registros(descricao["validade_convergente"]),
        "testes_rq": _registros(testes.drop(columns=["proporcoes", "categorias_agrupadas"])),
        "rq4_medianas": perfis_rq4,
    }


def gerar(caminho: Path = CSV_BRUTO, destino: Path = DESTINO) -> Path:
    limpeza = limpar(carregar(caminho), PERIODO_PRINCIPAL, ler_reclassificacao())
    dados, _ = recodificar(limpeza.validas, limpeza.reclassificacao)
    conteudo = agregar(limpeza, calcular_escores(dados))
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


if __name__ == "__main__":
    print(f"Resultados agregados gravados em {gerar()}")
