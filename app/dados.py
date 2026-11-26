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
from src.config import (
    CODIFICADORES,
    CSV_ANONIMIZACAO,
    CSV_BRUTO,
    CSV_CONSENSO,
    CSV_LIVRO_CODIGOS,
    CSV_RECLASSIFICACAO,
    PERIODO_PRINCIPAL,
    csv_codificacao,
)
from src.load import carregar
from src.recode import recodificar
from src.score import calcular_escores

CSV_SINTETICO = CSV_BRUTO.with_name("sintetico.csv")
NOME_PERIODO = (
    f"Respostas de {PERIODO_PRINCIPAL[0]:%d/%m} a {PERIODO_PRINCIPAL[1]:%d/%m/%Y} "
    "(coleta prorrogada até 25/11)"
)
# Decisões humanas lidas junto com o CSV: editar qualquer uma também atualiza o dashboard.
ENTRADAS_MANUAIS = [
    CSV_RECLASSIFICACAO, CSV_ANONIMIZACAO, CSV_CONSENSO, CSV_LIVRO_CODIGOS,
    *(csv_codificacao(nome) for nome in CODIFICADORES),
]


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


def versao_das_entradas(caminho: Path) -> tuple[int, ...]:
    """Data de modificação do CSV e de cada arquivo de data/manual/ (0 se não existe).

    Entra na chave do cache: trocar o CSV ou editar uma decisão humana (por
    exemplo, a reclassificação de "Outro") recalcula tudo na próxima execução.
    """
    return tuple(p.stat().st_mtime_ns if p.exists() else 0 for p in (caminho, *ENTRADAS_MANUAIS))


@st.cache_data(show_spinner="Lendo e preparando os dados brutos...")
def _preparar_com_cache(caminho: str, versao: tuple[int, ...]) -> Analise:
    # `versao` invalida o cache quando o CSV ou um arquivo manual muda.
    return preparar_analise(Path(caminho))


def preparar() -> tuple[Analise, bool]:
    caminho, e_sintetico = fonte_dos_dados()
    return _preparar_com_cache(str(caminho), versao_das_entradas(caminho)), e_sintetico


@st.cache_data(show_spinner="Calculando os desvios do protocolo...")
def _estudo_com_cache(caminho: str, versao: tuple[int, ...]) -> dict:
    from src.pipeline import calcular

    resultado = calcular(Path(caminho))
    return {"desvios": resultado["desvios"],
            "pendencias_abertas": resultado["abertas"].pendencias,
            # Só a contagem: o texto digitado em "Outro" é do respondente e não aparece na tela.
            "outro_pendentes": len(resultado["resumo"]["outro_pendentes"])}


def preparar_estudo() -> dict:
    """Desvios calculados pelo mesmo código do pipeline (src.pipeline.calcular), sem gravar nada."""
    caminho, _ = fonte_dos_dados()
    return _estudo_com_cache(str(caminho), versao_das_entradas(caminho))
