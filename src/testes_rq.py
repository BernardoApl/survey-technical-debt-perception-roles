"""Testes confirmatórios da seção 5.5. Entrada: dados recodificados com escores.

Uso: python -m src.testes_rq. Nenhuma observação individual é exportada.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import gammaln, logsumexp

from src.config import DIR_SAIDAS, MINIMO_GESTAO, SEED
from src.describe import margem_erro, preparar

GRUPOS = ("técnico", "gestão")
LIMITE_TABELAS = 200_000
PERMUTACOES = 99_999


def holm(p_valores, familia=14):
    """Holm conservador: hipóteses não executáveis permanecem na família (p=1)."""
    p = np.asarray(p_valores, dtype=float)
    if len(p) > familia or np.any((p[np.isfinite(p)] < 0) | (p[np.isfinite(p)] > 1)):
        raise ValueError("p-valores inválidos ou família insuficiente")
    validos = np.flatnonzero(np.isfinite(p))
    ordem = validos[np.argsort(p[validos], kind="stable")]
    resultado = np.full(len(p), np.nan)
    ajustados = np.minimum(1, np.maximum.accumulate(p[ordem] * (familia - np.arange(len(ordem)))))
    resultado[ordem] = ajustados
    return resultado


def _contar_tabelas(colunas, total):
    contagens = [0] * (total + 1)
    contagens[0] = 1
    for c in colunas:
        novo = [0] * (total + 1)
        for s, qtd in enumerate(contagens):
            if qtd:
                for x in range(min(c, total - s) + 1):
                    novo[s + x] = min(LIMITE_TABELAS + 1, novo[s + x] + qtd)
        contagens = novo
    return contagens[total]


def _fisher_exato(tabela):
    """Fisher-Freeman-Halton bilateral, condicionado às margens, por enumeração."""
    colunas = tabela.sum(axis=0).astype(int)
    total = int(tabela[0].sum())
    log_comb = lambda n, k: gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1)
    observado = float(np.sum(log_comb(colunas, tabela[0])))
    logs = []

    def visitar(i, restante, peso):
        if i == len(colunas) - 1:
            if 0 <= restante <= colunas[i]:
                valor = peso + log_comb(colunas[i], restante)
                if valor <= observado + 1e-10:
                    logs.append(valor)
            return
        minimo = max(0, restante - int(sum(colunas[i + 1:])))
        for x in range(minimo, min(int(colunas[i]), restante) + 1):
            visitar(i + 1, restante - x, peso + log_comb(colunas[i], x))

    visitar(0, total, 0.0)
    return min(1.0, float(np.exp(logsumexp(logs) - log_comb(int(colunas.sum()), total))))


def _nominal(sub, item):
    contagem = sub[item].value_counts()
    raras = set(contagem[contagem < 5].index)
    categorias = sub[item].map(lambda v: "Outras categorias (<5)" if v in raras else v)
    tabela = pd.crosstab(sub["grupo"], categorias).reindex(GRUPOS, fill_value=0)
    proporcoes = {}
    for grupo in GRUPOS:
        n = int(tabela.loc[grupo].sum())
        proporcoes[grupo] = {str(c): {"k": int(k), "n": n, "pct": 100 * k / n,
                                      "margem_pp": 100 * margem_erro(k / n, n)}
                             for c, k in tabela.loc[grupo].items()} if n else {}
    info = {"proporcoes": json.dumps(proporcoes, ensure_ascii=False),
            "categorias_agrupadas": json.dumps(sorted(raras), ensure_ascii=False)}
    if tabela.shape[1] < 2 or (tabela.sum(axis=1) == 0).any():
        return {**info, "motivo": "É necessário ter dois grupos e ao menos duas categorias após o agrupamento."}
    valores = tabela.to_numpy()
    chi2, _, _, _ = stats.chi2_contingency(valores, correction=False)
    v = math.sqrt(chi2 / valores.sum())  # tabela 2 x k
    if _contar_tabelas(valores.sum(axis=0).tolist(), int(valores[0].sum())) <= LIMITE_TABELAS:
        return {**info, "teste": "Fisher-Freeman-Halton exato", "estatistica": chi2,
                "estatistica_nome": "qui-quadrado de Pearson (descritivo)",
                "p_bruto": _fisher_exato(valores), "efeito": v}
    resultado = stats.chi2_contingency(
        valores, correction=False,
        method=stats.PermutationMethod(n_resamples=PERMUTACOES, rng=np.random.default_rng(SEED)))
    return {**info, "teste": "qui-quadrado por permutação", "estatistica": chi2,
            "estatistica_nome": "qui-quadrado de Pearson", "p_bruto": resultado.pvalue,
            "efeito": v, "desvio": "Permutação do qui-quadrado; ver DEVIATIONS.md"}


def _mann(sub, item):
    x, y = (sub.loc[sub.grupo.eq(g), item].to_numpy(dtype=float) for g in GRUPOS)
    if not len(x) or not len(y):
        return {"motivo": "Um dos grupos não tem respostas válidas."}
    n = len(x) + len(y)
    u = stats.mannwhitneyu(x, y, alternative="two-sided", method="asymptotic")
    _, empates = np.unique(np.concatenate([x, y]), return_counts=True)
    variancia = len(x) * len(y) / 12 * ((n + 1) - (sum(empates ** 3 - empates) / (n * (n - 1))))
    z = (u.statistic - len(x) * len(y) / 2) / math.sqrt(variancia) if variancia else 0.0
    return {"estatistica": u.statistic, "estatistica_nome": "U (técnico)",
            "p_bruto": u.pvalue, "efeito": z / math.sqrt(n)}


def _wilcoxon(sub):
    if len(sub) < 2:
        return {"motivo": "Menos de dois pares válidos."}
    dif = sub.POS.to_numpy(dtype=float) - sub.PRA.to_numpy(dtype=float)
    if np.all(dif == 0):
        return {"motivo": "Todas as diferenças entre POS e PRA são zero."}
    resultado = stats.wilcoxon(dif, alternative="two-sided", method="asymptotic", correction=False)
    return {"estatistica": resultado.statistic, "estatistica_nome": "W",
            "p_bruto": resultado.pvalue, "efeito": abs(resultado.zstatistic) / math.sqrt(len(dif))}


def _spearman(sub, x, y):
    if len(sub) < 3 or sub[x].nunique() < 2 or sub[y].nunique() < 2:
        return {"motivo": "Menos de três pares válidos ou variável constante."}
    resultado = stats.spearmanr(sub[x], sub[y], alternative="two-sided")
    return {"estatistica": resultado.statistic, "estatistica_nome": "rho de Spearman",
            "p_bruto": resultado.pvalue, "efeito": resultado.statistic}


def testes_por_cenario(dados: pd.DataFrame, confiabilidade: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """RQ3 exploratória por vinheta se alfa POS ou PRA for menor que 0,70.

    Três comparações por cenário, fora dos 14 testes confirmatórios de Holm.
    """
    from src.config import META_ALFA

    alfas = confiabilidade.set_index("construto")["alfa"].reindex(["POS", "PRA"])
    baixos = [nome for nome, valor in alfas.items() if pd.notna(valor) and valor < META_ALFA]
    indefinidos = [nome for nome, valor in alfas.items() if pd.isna(valor)]
    colunas = ["cenario", "comparacao", "teste", "n", "n_tecnico", "n_gestao",
               "n_sem_grupo", "estatistica_nome", "estatistica", "p_bruto", "efeito_nome",
               "efeito", "motivo"]
    linhas = []
    if baixos:
        for numero, (pos, pra) in enumerate((("E1", "E2"), ("E3", "E4"), ("E5", "E6")), 1):
            for comparacao, tipo, cols in ((f"{pos} × grupo", "mann", [pos]),
                                            (f"{pos} × {pra}", "pareado", [pos, pra]),
                                            (f"{pos} − {pra} × grupo", "distancia", [pos, pra])):
                base = dados[dados.grupo.isin(GRUPOS)] if tipo != "pareado" else dados
                sub = base.dropna(subset=cols).copy()
                ns = {g: int(sub.grupo.eq(g).sum()) for g in GRUPOS}
                linha = {"cenario": numero, "comparacao": comparacao,
                         "teste": "Wilcoxon pareado" if tipo == "pareado" else "Mann-Whitney U",
                         "n": len(sub), "n_tecnico": ns["técnico"], "n_gestao": ns["gestão"],
                         "n_sem_grupo": len(sub) - sum(ns.values()), "estatistica_nome": "",
                         "estatistica": np.nan, "p_bruto": np.nan,
                         "efeito_nome": "|Z|/sqrt(N)" if tipo == "pareado" else "r = Z/sqrt(N)",
                         "efeito": np.nan, "motivo": ""}
                if tipo == "pareado":
                    resultado = _wilcoxon(sub.assign(POS=sub[pos], PRA=sub[pra]))
                elif tipo == "distancia":
                    sub["distancia_cenario"] = sub[pos] - sub[pra]
                    resultado = _mann(sub, "distancia_cenario")
                else:
                    resultado = _mann(sub, pos)
                linha.update(resultado)
                linhas.append(linha)
    return pd.DataFrame(linhas, columns=colunas), {
        "executada": bool(baixos), "alfa_abaixo_meta": baixos,
        "alfa_indefinido": indefinidos, "fora_do_holm": True,
        "observacao": "Exploratória; p-valores sem correção de Holm." if baixos else
                      ("Alfa não calculável; condição não pôde ser totalmente avaliada." if indefinidos
                       else "Nenhum alfa de vinheta abaixo da meta."),
    }


def testes_rq(dados: pd.DataFrame) -> pd.DataFrame:
    """Retorna 14 linhas, incluindo testes impossíveis e seus motivos."""
    specs = [("RQ1", "NIV", None, "mann"), ("RQ2", "IMP", None, "mann"),
             ("RQ2", "D5", None, "nominal"), ("RQ3", "POS", None, "mann"),
             ("RQ3", "POS", "PRA", "wilcoxon"), ("RQ3", "DIST", None, "mann"),
             ("RQ3", "E7", None, "mann"), ("RQ3", "E8", None, "nominal")]
    specs += [("RQ4", x, y, "spearman") for x in ("NIV", "IMP", "POS") for y in ("B3", "B5")]
    linhas = []
    for i, (rq, x, y, tipo) in enumerate(specs, 1):
        cols = [x] + ([y] if y else [])
        # Comparações por papel precisam de grupo conhecido; testes globais incluem pendentes.
        base = dados[dados.grupo.isin(GRUPOS)] if tipo in ("mann", "nominal") else dados
        sub = base.dropna(subset=cols)
        ns = {g: int(sub.grupo.eq(g).sum()) for g in GRUPOS}
        linha = {"id": i, "rq": rq, "variavel": x, "comparacao": y or "grupo",
                 "teste": {"mann": "Mann-Whitney U", "nominal": "Fisher-Freeman-Halton exato",
                           "wilcoxon": "Wilcoxon pareado", "spearman": "Spearman"}[tipo],
                 "n": len(sub), "n_tecnico": ns["técnico"], "n_gestao": ns["gestão"],
                 "n_sem_grupo": len(sub) - sum(ns.values()),
                 "margem_tecnico_pp": 100 * margem_erro(.5, ns["técnico"]),
                 "margem_gestao_pp": 100 * margem_erro(.5, ns["gestão"]),
                 "baixo_poder": int(dados.grupo.eq("gestão").sum()) < MINIMO_GESTAO,
                 "efeito_nome": {"mann": "r = Z/sqrt(N)", "nominal": "V de Cramér",
                                 "wilcoxon": "|Z|/sqrt(N)", "spearman": "rho"}[tipo],
                 "estatistica": np.nan, "estatistica_nome": "", "p_bruto": np.nan,
                 "efeito": np.nan, "motivo": "", "proporcoes": "", "categorias_agrupadas": "", "desvio": ""}
        if tipo == "mann": resultado = _mann(sub, x)
        elif tipo == "nominal": resultado = _nominal(sub, x)
        elif tipo == "wilcoxon": resultado = _wilcoxon(sub)
        else: resultado = _spearman(sub, x, y)
        linha.update(resultado)
        linhas.append(linha)
    tabela = pd.DataFrame(linhas)
    tabela["p_holm"] = holm(tabela.p_bruto)
    return tabela


def salvar_testes(dados: pd.DataFrame, dir_saidas: Path = DIR_SAIDAS) -> Path:
    dir_saidas = Path(dir_saidas)
    dir_saidas.mkdir(parents=True, exist_ok=True)
    caminho = dir_saidas / "testes_rq.csv"
    testes_rq(dados).to_csv(caminho, index=False)
    return caminho


if __name__ == "__main__":
    print(f"Testes gravados em {salvar_testes(preparar())}")
