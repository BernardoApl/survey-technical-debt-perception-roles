"""Recodificação das respostas válidas: texto -> número (protocolo, Seções 3 e 5.2).

O valor de cada opção é a posição dela na lista do formulário (src/config.py).
Qualquer texto que não seja uma opção do formulário gera ValorDesconhecido,
em vez de virar ausente sem aviso. "Não sei" / "Não sei avaliar" viram
ausente e ficam marcados em `<item>_nao_sei`.
"""

from __future__ import annotations

import pandas as pd

from src.config import (
    C6_NENHUM,
    GRUPOS_RECLASSIFICACAO,
    ITENS_CONSTRUTO,
    LIKERT,
    NAO_SEI,
    NSA,
    OPCOES_B3,
    OPCOES_B4,
    OPCOES_B5,
    OPCOES_B6,
    OPCOES_B7,
    OPCOES_D5,
    OPCOES_E7,
    OPCOES_E8,
    PAPEIS_GESTAO,
    PAPEIS_TECNICOS,
    TIPOS_C6,
    VINHETAS,
)

ITENS_INVERTIDOS = ["C4", "D2"]
COLUNAS_C6 = dict(
    zip(
        [*TIPOS_C6, C6_NENHUM, NAO_SEI],
        ["C6_codigo", "C6_arquitetura", "C6_testes", "C6_documentacao",
         "C6_infra_build", "C6_requisitos", "C6_nenhum", "C6_nao_sei"],
        strict=True,
    )
)
COLUNAS_TIPOS_C6 = [COLUNAS_C6[t] for t in TIPOS_C6]
COLUNAS_INCONSISTENCIAS = ["resp_id", "item", "motivo"]


def _sem_nao_sei(opcoes):
    return [o for o in opcoes if o != NAO_SEI]


# item -> (opções em ordem, texto que vira ausente ou None)
ORDINAIS = {
    **{c: (LIKERT, NSA) for c in ITENS_CONSTRUTO["NIV"] + ITENS_CONSTRUTO["IMP"] + ["ATN"]},
    "E1": (VINHETAS[1], None), "E2": (VINHETAS[1], NAO_SEI),
    "E3": (VINHETAS[2], None), "E4": (VINHETAS[2], NAO_SEI),
    "E5": (VINHETAS[3], None), "E6": (VINHETAS[3], NAO_SEI),
    "E7": (_sem_nao_sei(OPCOES_E7), NAO_SEI),
    "B3": (OPCOES_B3, None),
    "B4": (OPCOES_B4, None),
    "B5": (OPCOES_B5, None),
    "B7": (OPCOES_B7, None),
}
# item -> (mínimo, máximo) das escalas numéricas do formulário
INTEIROS = {"B8": (1, 5), "C5": (0, 10)}
# item -> (opções válidas, texto que vira ausente ou None)
NOMINAIS = {
    "B6": (OPCOES_B6, None),
    "D5": (_sem_nao_sei(OPCOES_D5), NAO_SEI),
    "E8": (_sem_nao_sei(OPCOES_E8), NAO_SEI),
}


class ValorDesconhecido(ValueError):
    """Um texto que não é opção do formulário apareceu numa coluna de opções fixas."""


def _conferir(serie: pd.Series, validos: set[str]) -> None:
    desconhecidos = sorted(set(serie.dropna()) - validos)
    if desconhecidos:
        raise ValorDesconhecido(
            f"{serie.name}: valor(es) que não são opção do formulário: {desconhecidos}"
        )


def mapear(serie: pd.Series, opcoes: list[str], ausente: str | None = None) -> pd.Series:
    """Texto -> posição na lista (1, 2, ...); `ausente` -> NaN; texto desconhecido -> erro."""
    _conferir(serie, set(opcoes) | ({ausente} if ausente else set()))
    valores = {texto: float(i) for i, texto in enumerate(opcoes, start=1)}
    return serie.map(valores).astype(float)


def inteiro(serie: pd.Series, minimo: int, maximo: int) -> pd.Series:
    numeros = pd.to_numeric(serie, errors="coerce")
    invalidos = serie[serie.notna() & (numeros.isna() | ~numeros.between(minimo, maximo))]
    if not invalidos.empty:
        raise ValorDesconhecido(
            f"{serie.name}: esperado inteiro de {minimo} a {maximo}, "
            f"encontrado {sorted(set(invalidos))}"
        )
    return numeros.astype(float)


def separar_c6(c6: pd.Series, resp_id: pd.Series) -> tuple[pd.DataFrame, list[dict]]:
    """C6 (múltipla escolha separada por ';') -> 8 colunas binárias.

    - "Nenhum" ou "Não sei" junto com um tipo: valem os tipos marcados (inconsistência).
    - Só "Não sei": colunas de tipo ausentes (fora do denominador do M3).
    """
    marcados = c6.fillna("").str.split(";").map(lambda l: {t.strip() for t in l} - {""})
    desconhecidos = sorted(set().union(*marcados) - set(COLUNAS_C6))
    if desconhecidos:
        raise ValorDesconhecido(f"C6: valor(es) que não são opção do formulário: {desconhecidos}")

    tabela = pd.DataFrame(
        {col: marcados.map(lambda m, t=texto: t in m) for texto, col in COLUNAS_C6.items()},
        index=c6.index,
    ).astype("boolean")
    tem_tipo = tabela[COLUNAS_TIPOS_C6].any(axis=1)
    sem_tipo = tabela["C6_nenhum"] | tabela["C6_nao_sei"]

    inconsistencias = [
        {"resp_id": resp_id[i], "item": "C6",
         "motivo": "\"Nenhum\" ou \"Não sei\" marcado junto com um tipo; valem os tipos"}
        for i in tabela.index[tem_tipo & sem_tipo]
    ] + [
        {"resp_id": resp_id[i], "item": "C6",
         "motivo": "\"Nenhum\" e \"Não sei\" marcados juntos; tratado como \"Não sei\""}
        for i in tabela.index[~tem_tipo & tabela["C6_nenhum"] & tabela["C6_nao_sei"]]
    ]
    tabela.loc[tem_tipo, ["C6_nenhum", "C6_nao_sei"]] = False
    tabela.loc[~tem_tipo & tabela["C6_nao_sei"], "C6_nenhum"] = False

    so_nao_sei = tabela["C6_nao_sei"] | marcados.map(len).eq(0)
    tabela.loc[so_nao_sei, COLUNAS_TIPOS_C6] = pd.NA
    return tabela, inconsistencias


def grupo_papel(b2: pd.Series, reclassificacao: pd.DataFrame | None = None) -> pd.DataFrame:
    """B2 -> grupo ('técnico' ou 'gestão'); "Outro" usa a reclassificação da #5."""
    decididos = (
        reclassificacao.set_index("texto_original")["grupo"]
        if reclassificacao is not None and not reclassificacao.empty
        else pd.Series(dtype=object)
    )
    tecnico = b2.isin(PAPEIS_TECNICOS)
    gestao = b2.isin(PAPEIS_GESTAO)
    outro = b2.notna() & ~tecnico & ~gestao
    decisao = b2[outro].map(decididos).astype(object).fillna("")
    if decisao.eq("fora").any():
        raise ValueError(
            "Há resposta válida com papel \"Outro\" classificado como fora; "
            "rode a limpeza (src.clean) com a mesma reclassificação antes da recodificação."
        )
    grupo = pd.Series(pd.NA, index=b2.index, dtype=object)
    grupo[tecnico] = "técnico"
    grupo[gestao] = "gestão"
    decidido = decisao[decisao.isin([g for g in GRUPOS_RECLASSIFICACAO if g != "fora"])]
    grupo[decidido.index] = decidido
    return pd.DataFrame({"grupo": grupo, "grupo_pendente": outro & grupo.isna()})


def recodificar(
    validas: pd.DataFrame, reclassificacao: pd.DataFrame | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recodifica as respostas válidas da limpeza.

    Devolve (dados, inconsistencias). `dados` mantém resp_id, timestamp, B2, F1 e F2
    como texto; os demais itens viram número ou categoria validada.
    """
    dados = validas[["resp_id", "timestamp", "B2"]].copy()
    dados = dados.join(grupo_papel(validas["B2"], reclassificacao))

    for item, (opcoes, ausente) in ORDINAIS.items():
        dados[item] = mapear(validas[item].rename(item), opcoes, ausente)
        if ausente:
            dados[f"{item}_nao_sei"] = validas[item].eq(ausente)
    for item, (minimo, maximo) in INTEIROS.items():
        dados[item] = inteiro(validas[item].rename(item), minimo, maximo)
    for item, (opcoes, ausente) in NOMINAIS.items():
        _conferir(validas[item].rename(item), set(opcoes) | ({ausente} if ausente else set()))
        dados[item] = validas[item].where(validas[item] != ausente) if ausente else validas[item]
        if ausente:
            dados[f"{item}_nao_sei"] = validas[item].eq(ausente)

    for item in ITENS_INVERTIDOS:
        dados[f"{item}_raw"] = dados[item]
        dados[item] = 6 - dados[item]

    c6, inconsistencias = separar_c6(validas["C6"], validas["resp_id"])
    dados = dados.join(c6)
    dados[["F1", "F2"]] = validas[["F1", "F2"]]
    return dados, pd.DataFrame(inconsistencias, columns=COLUNAS_INCONSISTENCIAS)
