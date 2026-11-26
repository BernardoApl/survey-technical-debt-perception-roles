"""Escores dos construtos (protocolo, Seção 5.2; métricas M1, M4, M6, M7 e M8).

Escore = mediana dos itens respondidos, depois da inversão de C4 e D2.
Fica ausente quando mais de 50% dos itens do construto são "Não sei".
"""

from __future__ import annotations

import pandas as pd

from src.config import ITENS_CONSTRUTO, LIMITE_NAO_SEI

PARES_CENARIO = {"DIST1": ("E1", "E2"), "DIST2": ("E3", "E4"), "DIST3": ("E5", "E6")}


def calcular_escores(dados: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta NIV, IMP, POS, PRA, DIST (POS − PRA) e DIST1–DIST3 (por cenário)."""
    resultado = dados.copy()
    for nome, itens in ITENS_CONSTRUTO.items():
        respostas = dados[itens]
        ausente = respostas.isna().sum(axis=1) > LIMITE_NAO_SEI * len(itens)
        resultado[nome] = respostas.median(axis=1, skipna=True).mask(ausente)
    resultado["DIST"] = resultado["POS"] - resultado["PRA"]
    for nome, (deveria, acontece) in PARES_CENARIO.items():
        resultado[nome] = dados[deveria] - dados[acontece]
    return resultado
