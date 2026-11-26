"""Leitura dos dados brutos para o dashboard.

O dashboard sempre parte do CSV bruto: carregar -> limpar -> recodificar -> escores.
Sem data/raw/respostas.csv, usa um CSV sintético e avisa em todas as páginas.
Quando a #8 criar src/pipeline.py, só `preparar` precisa mudar.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from src import sintetico
from src.clean import ler_reclassificacao, limpar
from src.config import CSV_BRUTO, PERIODO_PRINCIPAL
from src.load import carregar
from src.recode import recodificar
from src.score import calcular_escores

CSV_SINTETICO = CSV_BRUTO.with_name("sintetico.csv")
NOME_PERIODO = (
    f"Respostas de {PERIODO_PRINCIPAL[0]:%d/%m} a {PERIODO_PRINCIPAL[1]:%d/%m/%Y} "
    "(coleta prorrogada até 25/11)"
)


@dataclass
class Analise:
    dados: pd.DataFrame  # respostas válidas recodificadas, com escores
    log: pd.DataFrame  # log de descartes (sem horário)
    resumo: dict
    inconsistencias: pd.DataFrame


def fonte_dos_dados() -> tuple[Path, bool]:
    """(caminho do CSV, True se for sintético)."""
    if CSV_BRUTO.exists():
        return CSV_BRUTO, False
    if not CSV_SINTETICO.exists():
        sintetico.salvar(CSV_SINTETICO)
    return CSV_SINTETICO, True


def preparar_analise(caminho: Path) -> Analise:
    limpeza = limpar(carregar(caminho), PERIODO_PRINCIPAL, ler_reclassificacao())
    dados, inconsistencias = recodificar(limpeza.validas, limpeza.reclassificacao)
    return Analise(calcular_escores(dados), limpeza.log, limpeza.resumo, inconsistencias)


@st.cache_data(show_spinner="Lendo e preparando os dados brutos...")
def _preparar_com_cache(caminho: str, modificado_em: float) -> Analise:
    # `modificado_em` invalida o cache quando o CSV é trocado.
    return preparar_analise(Path(caminho))


def preparar() -> tuple[Analise, bool]:
    caminho, e_sintetico = fonte_dos_dados()
    return _preparar_com_cache(str(caminho), caminho.stat().st_mtime), e_sintetico
