"""Respostas fictícias para os testes, no formato devolvido por src.load.carregar."""

import numpy as np
import pandas as pd

from src.config import CODIGOS, FUSO, LIKERT, PAPEIS_TECNICOS, SIM, VINHETAS

VINHETA = VINHETAS


def resposta(momento="2026-11-15 10:00:00", **trocas):
    """Uma resposta válida, que não falha em nenhuma etapa."""
    base = {
        "timestamp": pd.Timestamp(momento, tz=FUSO),
        "A1": SIM, "B1": SIM, "B2": PAPEIS_TECNICOS[0],
        "B3": "3 a 5 anos", "B4": "1 a 2 anos", "B5": "50 a 249",
        "B6": "Startup", "B7": "6 a 10 pessoas", "B8": "4",
        "C1": LIKERT[3], "C2": LIKERT[2], "C3": LIKERT[4], "C4": LIKERT[1],
        "C5": "7", "C6": "Código;Testes",
        "D1": LIKERT[3], "D2": LIKERT[1], "D3": LIKERT[4], "ATN": LIKERT[1], "D4": LIKERT[2],
        "D5": "Atraso de entregas",
        "E1": VINHETA[1][2], "E2": VINHETA[1][1], "E3": VINHETA[2][2],
        "E4": VINHETA[2][1], "E5": VINHETA[3][1], "E6": VINHETA[3][0],
        "E7": "Raramente (algumas vezes por ano)", "E8": "Tech lead",
        "F1": np.nan, "F2": np.nan,
    }
    base.update(trocas)
    return base


def tabela(*linhas):
    df = pd.DataFrame(list(linhas))[CODIGOS]
    df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
    df.insert(0, "resp_id", [f"R{i:03d}" for i in range(1, len(df) + 1)])
    return df
