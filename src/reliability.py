"""Confiabilidade e validade convergente (protocolo, Seção 5.3; issue #6).

- Alfa de Cronbach de NIV, IMP, POS e PRA, com IC 95% de Feldt (a mesma
  fórmula de `pingouin.cronbach_alpha`), n, alfa se o item for removido e
  correlação item-total corrigida. Os itens chegam já recodificados: C4 e D2
  invertidos (src.recode). "Não sei" é ausente, e o alfa usa só as respostas
  com todos os itens do construto (listwise), para que n seja um número só.
- Validade convergente: Spearman NIV × C5 e PRA × E7. Espera-se correlação
  positiva. Esses dois testes ficam fora da família de 14 do Holm (Seção 5.6).
"""

from __future__ import annotations

import math

import pandas as pd
from scipy import stats

from src.config import ITENS_CONSTRUTO, META_ALFA
from src.recode import ITENS_INVERTIDOS

NIVEL_IC = 0.95
PARES_VALIDADE = [("NIV", "C5"), ("PRA", "E7")]


def alfa_cronbach(itens: pd.DataFrame) -> float:
    """α = k / (k − 1) · (1 − Σ var(item) / var(soma)), variâncias amostrais (ddof = 1).

    Espera uma tabela sem ausentes. NaN se houver menos de 2 itens ou 2 respostas,
    ou se a soma não variar.
    """
    n, k = itens.shape
    if k < 2 or n < 2:
        return math.nan
    variancia_total = itens.sum(axis=1).var(ddof=1)
    if variancia_total == 0:
        return math.nan
    return float(k / (k - 1) * (1 - itens.var(ddof=1).sum() / variancia_total))


def ic_feldt(alfa: float, n: int, k: int, nivel: float = NIVEL_IC) -> tuple[float, float]:
    """IC do alfa pela distribuição F (Feldt, 1965), com gl n − 1 e (n − 1)(k − 1)."""
    if math.isnan(alfa) or n < 2 or k < 2:
        return math.nan, math.nan
    gl1, gl2 = n - 1, (n - 1) * (k - 1)
    inferior = 1 - (1 - alfa) * stats.f.isf((1 - nivel) / 2, gl1, gl2)
    superior = 1 - (1 - alfa) * stats.f.isf((1 + nivel) / 2, gl1, gl2)
    return float(inferior), float(superior)


def _rotulo(item: str) -> str:
    return f"{item} (R)" if item in ITENS_INVERTIDOS else item


def confiabilidade(dados: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(uma linha por construto, uma linha por item).

    Alfa sem o item e correlação item-total usam as mesmas respostas do alfa
    do construto, para que os números sejam comparáveis.
    """
    construtos, itens_linhas = [], []
    for construto, itens in ITENS_CONSTRUTO.items():
        completas = dados[itens].dropna()
        n, k = len(completas), len(itens)
        alfa = alfa_cronbach(completas)
        inferior, superior = ic_feldt(alfa, n, k)
        construtos.append({
            "construto": construto, "itens": ", ".join(map(_rotulo, itens)), "k": k,
            "n": n, "excluidas": len(dados) - n, "alfa": alfa,
            "ic95_inferior": inferior, "ic95_superior": superior,
            "atinge_meta": bool(alfa >= META_ALFA) if not math.isnan(alfa) else pd.NA,
        })
        for item in itens:
            outros = [i for i in itens if i != item]
            itens_linhas.append({
                "construto": construto, "item": _rotulo(item), "n": n,
                "alfa_sem_item": alfa_cronbach(completas[outros]),
                "r_item_total": _correlacao(completas[item], completas[outros].sum(axis=1)),
            })
    return (
        pd.DataFrame(construtos, columns=["construto", "itens", "k", "n", "excluidas", "alfa",
                                          "ic95_inferior", "ic95_superior", "atinge_meta"]),
        pd.DataFrame(itens_linhas, columns=["construto", "item", "n", "alfa_sem_item",
                                            "r_item_total"]),
    )


def _correlacao(x: pd.Series, y: pd.Series) -> float:
    """Pearson do item com a soma dos demais (item-total corrigida); NaN se algum for constante."""
    if len(x) < 2 or x.nunique() < 2 or y.nunique() < 2:
        return math.nan
    return float(x.corr(y))


def validade_convergente(dados: pd.DataFrame) -> pd.DataFrame:
    """Spearman bilateral de cada par, só com as respostas que têm os dois valores."""
    linhas = []
    for x, y in PARES_VALIDADE:
        pares = dados[[x, y]].dropna()
        n = len(pares)
        constante = pares[x].nunique() < 2 or pares[y].nunique() < 2
        if n < 3 or constante:
            rho, p = math.nan, math.nan
        else:
            resultado = stats.spearmanr(pares[x], pares[y])
            rho, p = float(resultado.statistic), float(resultado.pvalue)
        linhas.append({"par": f"{x} × {y}", "x": x, "y": y, "n": n, "rho": rho,
                       "p_valor": p, "sinal_esperado": "+", "no_holm": False})
    return pd.DataFrame(linhas, columns=["par", "x", "y", "n", "rho", "p_valor",
                                         "sinal_esperado", "no_holm"])
