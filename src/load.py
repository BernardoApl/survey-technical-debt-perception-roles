"""Leitura e conferência do CSV bruto exportado do Google Forms."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import COLUNAS, CSV_BRUTO, FUSO

FORMATO_DATA = "%Y/%m/%d %I:%M:%S %p"


class ErroFormulario(ValueError):
    """O CSV não corresponde ao formulário esperado."""


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", str(texto)).lstrip("﻿")
    return re.sub(r"\s+", " ", texto).strip().casefold()


def conferir_cabecalho(cabecalho: list[str]) -> None:
    """Gera ErroFormulario se o número ou o começo das colunas não bater."""
    if len(cabecalho) != len(COLUNAS):
        raise ErroFormulario(
            f"O CSV tem {len(cabecalho)} colunas; o formulário tem {len(COLUNAS)} "
            "(carimbo de data/hora + 31 itens)."
        )
    erros = [
        f"  posição {pos} ({codigo}): esperado começar com {prefixo!r}, encontrado {texto!r}"
        for pos, ((codigo, prefixo), texto) in enumerate(zip(COLUNAS, cabecalho))
        if not _normalizar(texto).startswith(_normalizar(prefixo))
    ]
    if erros:
        raise ErroFormulario("Cabeçalho diferente do esperado:\n" + "\n".join(erros))


def converter_data(serie: pd.Series) -> pd.Series:
    """'2026/11/16 9:23:49 AM GMT-3' -> Timestamp em America/Sao_Paulo."""
    texto = serie.str.replace(r"\s*GMT[+-]\d+\s*$", "", regex=True).str.strip()
    datas = pd.to_datetime(texto, format=FORMATO_DATA, errors="coerce")
    invalidas = serie[datas.isna()]
    if not invalidas.empty:
        raise ErroFormulario(
            f"Data/hora em formato inesperado em {len(invalidas)} linha(s), "
            f"ex.: {invalidas.iloc[0]!r}"
        )
    return datas.dt.tz_localize(FUSO)


def carregar(caminho: str | Path = CSV_BRUTO) -> pd.DataFrame:
    """Lê o CSV bruto e devolve colunas `resp_id, timestamp, A1, ..., F2`.

    Não descarta nem recodifica nada: só confere o formato, ignora linhas
    totalmente vazias, converte a data, troca vazios por NaN e numera as
    respostas pela ordem de envio.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(
            f"CSV não encontrado em {caminho}. Exporte as respostas do Forms "
            "e salve como data/raw/respostas.csv."
        )
    df = pd.read_csv(
        caminho, dtype=str, keep_default_na=False, encoding="utf-8-sig"
    )
    conferir_cabecalho(list(df.columns))
    df.columns = [codigo for codigo, _ in COLUNAS]

    # Linhas totalmente vazias (sobras de planilha) não são respostas.
    df = df[df.apply(lambda col: col.str.strip() != "").any(axis=1)]

    df["timestamp"] = converter_data(df["timestamp"])
    df = df.replace(r"^\s*$", np.nan, regex=True)

    df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
    df.insert(0, "resp_id", [f"R{i:03d}" for i in range(1, len(df) + 1)])
    return df


if __name__ == "__main__":
    dados = carregar()
    print(f"{len(dados)} respostas, {dados.shape[1]} colunas")
