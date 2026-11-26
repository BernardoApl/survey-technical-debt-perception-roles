"""Filtros por segmento (barra lateral) e rótulos das categorias."""

from __future__ import annotations

import pandas as pd

from src.config import OPCOES_B3, OPCOES_B4, OPCOES_B5, OPCOES_B6, OPCOES_B7

GRUPOS = ["técnico", "gestão"]

# coluna -> (rótulo do filtro, opções na ordem, True se a coluna está codificada 1, 2, ...)
FILTROS = {
    "grupo": ("Grupo de papel", GRUPOS, False),
    "B3": ("Tempo de experiência em TI", OPCOES_B3, True),
    "B5": ("Porte da empresa (funcionários)", OPCOES_B5, True),
    "B6": ("Tipo de empresa", OPCOES_B6, False),
    "B7": ("Tamanho da equipe", OPCOES_B7, True),
}
ROTULOS_ORDINAIS = {"B3": OPCOES_B3, "B4": OPCOES_B4, "B5": OPCOES_B5, "B7": OPCOES_B7}


def rotular(dados: pd.DataFrame, coluna: str) -> pd.Series:
    """Troca o código ordinal (1, 2, ...) pelo texto da opção."""
    if coluna in ROTULOS_ORDINAIS:
        opcoes = ROTULOS_ORDINAIS[coluna]
        return dados[coluna].map(lambda v: opcoes[int(v) - 1] if pd.notna(v) else v)
    return dados[coluna]


def _ativo(coluna: str, escolhidas: list[str], disponiveis: dict[str, list[str]] | None) -> bool:
    """Ativo quando a seleção deixa de fora alguma opção presente nos dados.

    Sem `disponiveis`, compara com todas as opções do formulário. Opções que ninguém
    marcou não contam: deixá-las fora do filtro não restringe nada.
    """
    opcoes = disponiveis[coluna] if disponiveis and coluna in disponiveis else FILTROS[coluna][1]
    return bool(escolhidas) and not set(escolhidas) >= set(opcoes)


def aplicar_filtros(dados: pd.DataFrame, selecao: dict[str, list[str]],
                    disponiveis: dict[str, list[str]] | None = None) -> pd.DataFrame:
    """Mantém as linhas cujas categorias estão na seleção.

    Filtro com todas as opções (ou nenhuma selecionada) não restringe nada.
    Com o filtro de grupo ativo, "Outro" pendente (sem grupo) sai.
    """
    manter = pd.Series(True, index=dados.index)
    for coluna, escolhidas in selecao.items():
        if _ativo(coluna, escolhidas, disponiveis):
            manter &= rotular(dados, coluna).isin(escolhidas)
    return dados[manter]


def filtros_ativos(selecao: dict[str, list[str]],
                   disponiveis: dict[str, list[str]] | None = None) -> list[str]:
    return [FILTROS[c][0] for c, escolhidas in selecao.items() if _ativo(c, escolhidas, disponiveis)]
