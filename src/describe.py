"""Estatística descritiva (protocolo, Seção 5.4; issue #6).

Recebe a tabela de `src.score.calcular_escores` (respostas válidas recodificadas,
com escores) e devolve tabelas longas, uma linha por item × opção × recorte:

- `frequencias`: cada opção de cada item fechado, com n, k, % e margem de erro.
  O perfil da amostra são as linhas de `grupo` e de B2 a B8.
- `concordancia_likert`: % de respostas 4 ou 5 em C1–C4 e D1–D4, com margem.
- `resumo_escores`: mediana e IQR de NIV, IMP, POS, PRA, DIST e C5.
- `nao_sei`: uso de "Não sei" e "Não sei avaliar" por item.

Recortes: total, técnico e gestão. Papel "Outro" ainda sem grupo entra só no total.
Confiabilidade e validade convergente ficam em `src.reliability`.

Uso: python -m src.describe   (grava as tabelas da #6 em outputs/)
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from src.config import (
    DIR_SAIDAS,
    ITENS_CONSTRUTO,
    NAO_SEI,
    NSA,
    PAPEIS_GESTAO,
    PAPEIS_TECNICOS,
    RECORTES,
    Z_95,
)
from src.recode import COLUNAS_C6, INTEIROS, ITENS_INVERTIDOS, NOMINAIS, ORDINAIS

ITENS_LIKERT = ITENS_CONSTRUTO["NIV"] + ITENS_CONSTRUTO["IMP"]
SEM_GRUPO = "sem grupo (\"Outro\" pendente)"
# Itens fechados, na ordem do formulário. Ficam de fora A1 e B1 (todas as
# válidas responderam "Sim") e ATN (todas as válidas marcaram a opção pedida).
ITENS_FREQUENCIA = [
    "grupo", "B2", "B3", "B4", "B5", "B6", "B7", "B8",
    "C1", "C2", "C3", "C4", "C5", "C6",
    "D1", "D2", "D3", "D4", "D5",
    "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8",
]
ITENS_PERFIL = ["grupo", "B2", "B3", "B4", "B5", "B6", "B7", "B8"]
VARIAVEIS_ESCORE = ["NIV", "IMP", "POS", "PRA", "DIST", "C5"]
COLUNAS_PROPORCAO = ["n", "k", "pct", "margem_pp"]


# ---------------------------------------------------------------------------
# Proporções e recortes
# ---------------------------------------------------------------------------
def margem_erro(p: float, n: int) -> float:
    """e = 1,96 * sqrt(p(1 - p) / n), em proporção (protocolo, Seção 2)."""
    return Z_95 * math.sqrt(p * (1 - p) / n) if n else math.nan


def proporcao(k: int, n: int) -> dict:
    """{n, k, pct, margem_pp}; pct e margem em pontos percentuais (NaN se n = 0)."""
    p = k / n if n else math.nan
    return {"n": int(n), "k": int(k), "pct": 100 * p, "margem_pp": 100 * margem_erro(p, n)}


def recortes(dados: pd.DataFrame):
    """(nome, máscara) para total, técnico e gestão."""
    for nome in RECORTES:
        yield nome, (pd.Series(True, index=dados.index) if nome == "total"
                     else dados["grupo"].eq(nome))


# ---------------------------------------------------------------------------
# Frequências
# ---------------------------------------------------------------------------
def rotulos(dados: pd.DataFrame, item: str) -> tuple[pd.Series, list[str]]:
    """Valor recodificado -> texto da opção, como a pessoa marcou; e as opções em ordem.

    Itens invertidos (C4, D2) usam o valor antes da inversão. "Não sei" volta a
    ser uma opção. NaN = item não respondido.
    """
    if item == "grupo":
        return (dados["grupo"].astype(object).where(dados["grupo"].notna(), SEM_GRUPO),
                ["técnico", "gestão", SEM_GRUPO])
    if item == "B2":  # cargo digitado em "Outro" é texto livre: aparece só como "Outro"
        papeis = PAPEIS_TECNICOS + PAPEIS_GESTAO
        b2 = dados["B2"].astype(object)
        return b2.where(b2.isin(papeis) | b2.isna(), "Outro"), papeis + ["Outro"]
    if item in ORDINAIS:
        opcoes, ausente = ORDINAIS[item]
        coluna = f"{item}_raw" if item in ITENS_INVERTIDOS else item
        texto = dados[coluna].map(lambda v: opcoes[int(v) - 1] if pd.notna(v) else None)
    elif item in INTEIROS:
        minimo, maximo = INTEIROS[item]
        opcoes, ausente = [str(i) for i in range(minimo, maximo + 1)], None
        texto = dados[item].map(lambda v: str(int(v)) if pd.notna(v) else None)
    elif item in NOMINAIS:
        opcoes, ausente = NOMINAIS[item]
        texto = dados[item].astype(object)
    else:
        raise KeyError(f"{item} não é um item fechado de uma opção")
    texto = texto.astype(object)
    if ausente:
        texto[dados[f"{item}_nao_sei"].fillna(False).astype(bool)] = ausente
        opcoes = [*opcoes, ausente]
    return texto, list(opcoes)


def _frequencias_c6(dados: pd.DataFrame) -> list[dict]:
    """C6 é múltipla escolha: cada opção é uma proporção separada.

    Nos 6 tipos, n exclui quem marcou só "Não sei" (as colunas de tipo ficam
    ausentes, como no M3); em "Nenhum" e "Não sei", n são todas as respostas.
    """
    linhas = []
    for recorte, mascara in recortes(dados):
        sub = dados[mascara]
        for ordem, (opcao, coluna) in enumerate(COLUNAS_C6.items(), start=1):
            valores = sub[coluna]
            linhas.append({
                "item": "C6", "opcao": opcao, "ordem": ordem, "recorte": recorte,
                **proporcao(int(valores.fillna(False).astype(bool).sum()),
                            int(valores.notna().sum())),
            })
    return linhas


def frequencias(dados: pd.DataFrame) -> pd.DataFrame:
    """Frequência e % de cada opção de cada item fechado, total e por grupo.

    n = respostas do recorte que responderam ao item, incluindo "Não sei" (que
    aqui é uma opção como as outras). Opções sem nenhuma resposta aparecem com k = 0.
    """
    linhas = []
    for item in ITENS_FREQUENCIA:
        if item == "C6":
            linhas += _frequencias_c6(dados)
            continue
        texto, opcoes = rotulos(dados, item)
        for recorte, mascara in recortes(dados):
            if item == "grupo" and recorte != "total":
                continue
            respondidas = texto[mascara].dropna()
            contagem = respondidas.value_counts()
            for ordem, opcao in enumerate(opcoes, start=1):
                linhas.append({
                    "item": item, "opcao": opcao, "ordem": ordem, "recorte": recorte,
                    **proporcao(int(contagem.get(opcao, 0)), len(respondidas)),
                })
    return pd.DataFrame(linhas, columns=["item", "opcao", "ordem", "recorte",
                                         *COLUNAS_PROPORCAO])


def perfil(tabela_frequencias: pd.DataFrame) -> pd.DataFrame:
    """Perfil da amostra: grupo e B2 a B8."""
    return tabela_frequencias[tabela_frequencias["item"].isin(ITENS_PERFIL)].reset_index(drop=True)


def nao_sei(tabela_frequencias: pd.DataFrame) -> pd.DataFrame:
    """Uso de "Não sei" / "Não sei avaliar" por item e recorte (protocolo, Seção 3).

    n = respostas que responderam ao item; k = respostas "Não sei".
    """
    linhas = tabela_frequencias[tabela_frequencias["opcao"].isin([NSA, NAO_SEI])]
    return linhas.drop(columns="ordem").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Likert e escores
# ---------------------------------------------------------------------------
def concordancia_likert(dados: pd.DataFrame) -> pd.DataFrame:
    """% de concordância (4 Concordo parcialmente ou 5 Concordo totalmente) por item.

    Usa a resposta como foi marcada: em C4 e D2 (invertidos) é a concordância
    com a frase do formulário, antes da inversão. "Não sei avaliar" fica fora
    do n, como ausente (protocolo, Seção 3).
    """
    linhas = []
    for item in ITENS_LIKERT:
        coluna = f"{item}_raw" if item in ITENS_INVERTIDOS else item
        for recorte, mascara in recortes(dados):
            valores = dados.loc[mascara, coluna].dropna()
            linhas.append({
                "item": item, "invertido": item in ITENS_INVERTIDOS, "recorte": recorte,
                **proporcao(int((valores >= 4).sum()), len(valores)),
            })
    return pd.DataFrame(linhas, columns=["item", "invertido", "recorte", *COLUNAS_PROPORCAO])


def resumo_escores(dados: pd.DataFrame) -> pd.DataFrame:
    """Mediana, quartis e IQR (Q3 − Q1) de cada escore, total e por grupo.

    Quartis pelo método linear do pandas (o padrão, tipo 7 de Hyndman e Fan).
    n = respostas com escore; ausentes = sem escore (construto com mais de 50%
    de "Não sei").
    """
    linhas = []
    for variavel in VARIAVEIS_ESCORE:
        for recorte, mascara in recortes(dados):
            valores = dados.loc[mascara, variavel]
            validos = valores.dropna()
            q1, mediana, q3 = (validos.quantile([0.25, 0.5, 0.75]).tolist()
                               if len(validos) else [math.nan] * 3)
            linhas.append({
                "escore": variavel, "recorte": recorte, "n": len(validos),
                "ausentes": int(valores.isna().sum()), "mediana": mediana,
                "q1": q1, "q3": q3, "iqr": q3 - q1,
            })
    return pd.DataFrame(linhas, columns=["escore", "recorte", "n", "ausentes",
                                         "mediana", "q1", "q3", "iqr"])


# ---------------------------------------------------------------------------
# Todas as tabelas da #6
# ---------------------------------------------------------------------------
def tabelas(dados: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Nome do arquivo (sem .csv) -> tabela. Inclui confiabilidade e validade."""
    from src.reliability import confiabilidade, validade_convergente

    freq = frequencias(dados)
    alfa, alfa_itens = confiabilidade(dados)
    return {
        "frequencias": freq,
        "perfil": perfil(freq),
        "nao_sei": nao_sei(freq),
        "concordancia_likert": concordancia_likert(dados),
        "escores_por_grupo": resumo_escores(dados),
        "confiabilidade": alfa,
        "confiabilidade_itens": alfa_itens,
        "validade_convergente": validade_convergente(dados),
    }


def salvar_tabelas(tabelas_geradas: dict[str, pd.DataFrame],
                   dir_saidas: Path = DIR_SAIDAS) -> None:
    dir_saidas.mkdir(parents=True, exist_ok=True)
    for nome, tabela in tabelas_geradas.items():
        tabela.to_csv(dir_saidas / f"{nome}.csv", index=False)


def preparar(caminho=None, periodo=None) -> pd.DataFrame:
    """CSV bruto -> limpeza -> recodificação -> escores (respostas válidas)."""
    from src.clean import ler_reclassificacao, limpar
    from src.config import CSV_BRUTO, PERIODO_PRINCIPAL
    from src.load import carregar
    from src.recode import recodificar
    from src.score import calcular_escores

    limpeza = limpar(carregar(caminho or CSV_BRUTO), periodo or PERIODO_PRINCIPAL,
                     ler_reclassificacao())
    dados, _ = recodificar(limpeza.validas, limpeza.reclassificacao)
    return calcular_escores(dados)


if __name__ == "__main__":
    geradas = tabelas(preparar())
    salvar_tabelas(geradas)
    for nome, tabela in geradas.items():
        print(f"outputs/{nome}.csv: {len(tabela)} linhas")
