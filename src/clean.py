"""Limpeza e descarte das respostas (protocolo, Seção 5.1).

Cada resposta passa pelas etapas na ordem abaixo e recebe só o motivo da
primeira que falhar. A etapa 6 não descarta: só registra o construto que
fica sem escore para aquela pessoa.

Uso: python -m src.clean   (lê data/raw/respostas.csv e grava as saídas)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config import (
    ATN_CORRETO,
    CODIGOS,
    CSV_RECLASSIFICACAO,
    DIR_PROCESSADO,
    DIR_SAIDAS,
    GRUPOS_RECLASSIFICACAO,
    ITENS_CONSTRUTO,
    ITENS_STRAIGHTLINING,
    JANELA_DUPLICATA,
    LIMITE_NAO_SEI,
    NAO,
    NAO_SEI,
    NSA,
    PAPEIS_GESTAO,
    PAPEIS_TECNICOS,
    PERIODO_PREREGISTRADO,
    PERIODO_PRINCIPAL,
)

ETAPAS = {
    0: "fora do período da análise",
    1: "sem consentimento",
    2: "fora da população",
    3: "falha no item de atenção",
    4: "straightlining",
    5: "duplicata",
    6: "construto ausente",
}
COLUNAS_RECLASSIFICACAO = ["texto_original", "grupo", "decidido_por", "justificativa"]
COLUNAS_LOG = ["resp_id", "etapa", "motivo", "descartada"]
ITENS_RESPOSTA = CODIGOS[1:]  # A1 a F2, sem o carimbo de data/hora


@dataclass
class ResultadoLimpeza:
    validas: pd.DataFrame
    log: pd.DataFrame
    resumo: dict
    reclassificacao: pd.DataFrame  # com linhas novas pendentes, se houver


# ---------------------------------------------------------------------------
# Reclassificação de "Outro" (decisão humana, issue #5)
# ---------------------------------------------------------------------------
def ler_reclassificacao(caminho: str | Path = CSV_RECLASSIFICACAO) -> pd.DataFrame:
    caminho = Path(caminho)
    if not caminho.exists():
        return pd.DataFrame(columns=COLUNAS_RECLASSIFICACAO)
    tabela = pd.read_csv(caminho, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    faltam = set(COLUNAS_RECLASSIFICACAO) - set(tabela.columns)
    if faltam:
        raise ValueError(f"{caminho.name} sem as colunas: {sorted(faltam)}")
    grupos = tabela["grupo"].str.strip()
    invalidos = sorted(set(grupos) - set(GRUPOS_RECLASSIFICACAO) - {""})
    if invalidos:
        raise ValueError(
            f"{caminho.name}: grupo inválido {invalidos}; use {GRUPOS_RECLASSIFICACAO} "
            "ou deixe vazio enquanto estiver pendente."
        )
    # Toda decisão precisa de autor e justificativa (docs/decisoes-analise.md, item 2).
    decidida = grupos != ""
    sem_justificativa = decidida & (
        tabela["decidido_por"].str.strip().eq("")
        | tabela["justificativa"].str.strip().eq("")
        | tabela["justificativa"].str.strip().str.startswith("pendente")
    )
    if sem_justificativa.any():
        raise ValueError(
            f"{caminho.name}: classificação sem decidido_por ou justificativa para "
            f"{sorted(tabela.loc[sem_justificativa, 'texto_original'])}"
        )
    return tabela.assign(grupo=grupos)


def papeis_outro(df: pd.DataFrame) -> list[str]:
    """Textos digitados em B2 que não são uma das 12 opções do formulário."""
    papeis = df["B2"].dropna()
    return sorted(set(papeis) - set(PAPEIS_TECNICOS) - set(PAPEIS_GESTAO))


def _atualizar_reclassificacao(reclassificacao, textos):
    novos = sorted(set(textos) - set(reclassificacao["texto_original"]))
    if not novos:
        return reclassificacao
    pendentes = pd.DataFrame(
        {"texto_original": novos, "grupo": "", "decidido_por": "",
         "justificativa": "pendente: classificar como técnico, gestão ou fora"}
    )
    return pd.concat([reclassificacao, pendentes], ignore_index=True)


# ---------------------------------------------------------------------------
# Etapas
# ---------------------------------------------------------------------------
def _duplicatas(df: pd.DataFrame, candidatas: pd.Series) -> pd.Series:
    """Etapa 5: igual em A1–F2 a uma resposta anterior ainda válida, até 60 min antes."""
    duplicada = pd.Series(False, index=df.index)
    ultima_mantida: dict[tuple, pd.Timestamp] = {}
    conteudo = df[ITENS_RESPOSTA].astype("string").fillna("")
    for idx in df.loc[candidatas].sort_values("timestamp", kind="mergesort").index:
        chave = tuple(conteudo.loc[idx])
        momento = df.at[idx, "timestamp"]
        anterior = ultima_mantida.get(chave)
        if anterior is not None and momento - anterior <= JANELA_DUPLICATA:
            duplicada[idx] = True
        else:
            ultima_mantida[chave] = momento
    return duplicada


def _construtos_ausentes(df: pd.DataFrame) -> pd.DataFrame:
    """Etapa 6: True quando mais de 50% dos itens do construto são "Não sei"."""
    return pd.DataFrame(
        {
            nome: df[itens].isin([NSA, NAO_SEI]).sum(axis=1) > LIMITE_NAO_SEI * len(itens)
            for nome, itens in ITENS_CONSTRUTO.items()
        },
        index=df.index,
    )


def limpar(
    df: pd.DataFrame,
    periodo: tuple[pd.Timestamp, pd.Timestamp] = PERIODO_PRINCIPAL,
    reclassificacao: pd.DataFrame | None = None,
) -> ResultadoLimpeza:
    """Aplica as etapas 0 a 6 a uma tabela vinda de `src.load.carregar`."""
    if reclassificacao is None:
        reclassificacao = pd.DataFrame(columns=COLUNAS_RECLASSIFICACAO)
    textos_outro = papeis_outro(df)
    reclassificacao = _atualizar_reclassificacao(reclassificacao, textos_outro)
    decididos = reclassificacao.set_index("texto_original")["grupo"]
    fora = set(decididos[decididos == "fora"].index)
    pendentes = [t for t in textos_outro if decididos.get(t, "") == ""]

    etapa = pd.Series(pd.NA, index=df.index, dtype="Int64")
    motivo = pd.Series(pd.NA, index=df.index, dtype=object)

    def marcar(numero, falhou, texto):
        novas = falhou.fillna(False).astype(bool) & etapa.isna()
        etapa[novas] = numero
        motivo[novas] = texto[novas] if isinstance(texto, pd.Series) else texto

    inicio, fim = periodo
    marcar(0, ~df["timestamp"].between(inicio, fim),
           f"{ETAPAS[0]} ({inicio:%d/%m/%Y} a {fim:%d/%m/%Y})")
    marcar(1, df["A1"].eq(NAO), f"{ETAPAS[1]} (A1 = Não)")
    motivo_2 = pd.Series(f"{ETAPAS[2]} (B1 = Não)", index=df.index).where(
        df["B1"].eq(NAO), f"{ETAPAS[2]} (papel \"Outro\" classificado como fora)"
    )
    marcar(2, df["B1"].eq(NAO) | df["B2"].isin(fora), motivo_2)
    marcar(3, df["ATN"].ne(ATN_CORRETO), f"{ETAPAS[3]} (ATN diferente de \"{ATN_CORRETO}\")")
    itens_sl = df[ITENS_STRAIGHTLINING]
    marcar(4, itens_sl.notna().all(axis=1) & itens_sl.nunique(axis=1).eq(1),
           f"{ETAPAS[4]} (mesma resposta nos 8 itens de NIV e IMP)")
    marcar(5, _duplicatas(df, etapa.isna()),
           f"{ETAPAS[5]} (igual a uma resposta enviada até 60 min antes)")

    descartada = etapa.notna()
    log = pd.DataFrame(
        {"resp_id": df["resp_id"], "etapa": etapa, "motivo": motivo, "descartada": True}
    )[descartada]

    validas = df[~descartada].copy()
    ausentes = _construtos_ausentes(validas)
    log_6 = [
        {"resp_id": validas.at[idx, "resp_id"], "etapa": 6,
         "motivo": f"{ETAPAS[6]} ({nome}: mais de 50% de \"Não sei\")", "descartada": False}
        for nome in ausentes.columns
        for idx in ausentes.index[ausentes[nome]]
    ]
    log = pd.concat([log, pd.DataFrame(log_6, columns=COLUNAS_LOG)], ignore_index=True)
    log = log.astype({"etapa": "int64", "descartada": bool})
    log = log.sort_values(["resp_id", "etapa"], kind="mergesort").reset_index(drop=True)

    resumo = {
        "periodo": [f"{inicio:%Y-%m-%d %H:%M:%S}", f"{fim:%Y-%m-%d %H:%M:%S}"],
        "recebidas": int(len(df)),
        "descartadas": int(descartada.sum()),
        "validas": int(len(validas)),
        "descartes_por_etapa": {
            f"{n} - {ETAPAS[n]}": int((etapa == n).sum()) for n in range(6)
        },
        "construtos_ausentes": {nome: int(ausentes[nome].sum()) for nome in ausentes},
        "outro_pendentes": [t for t in pendentes if t in set(validas["B2"])],
        "validas_por_grupo": None,  # preenchido quando a recodificação (#3) entrar
    }
    return ResultadoLimpeza(validas.reset_index(drop=True), log, resumo, reclassificacao)


# ---------------------------------------------------------------------------
# Saídas
# ---------------------------------------------------------------------------
def salvar_limpeza(
    resultado: ResultadoLimpeza,
    sufixo: str = "",
    dir_saidas: Path = DIR_SAIDAS,
    dir_processado: Path = DIR_PROCESSADO,
) -> None:
    """Grava log e resumo em outputs/ e as válidas em data/processed/.

    O arquivo público sai sem horário, sem F1/F2 e com o cargo digitado em "Outro"
    trocado por "Outro" (docs/decisoes-analise.md, item 9).
    """
    dir_saidas.mkdir(parents=True, exist_ok=True)
    dir_processado.mkdir(parents=True, exist_ok=True)
    resultado.log.to_csv(dir_saidas / f"log_descartes{sufixo}.csv", index=False)
    (dir_saidas / f"resumo_amostra{sufixo}.json").write_text(
        json.dumps(resultado.resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    publicas = resultado.validas.drop(columns=["timestamp", "F1", "F2"])
    # Cargo digitado em "Outro" é texto livre do respondente: não vai para o Git.
    publicas["B2"] = publicas["B2"].where(
        publicas["B2"].isin(PAPEIS_TECNICOS + PAPEIS_GESTAO) | publicas["B2"].isna(), "Outro"
    )
    publicas.to_csv(dir_processado / f"respostas_validas{sufixo}.csv", index=False)


def salvar_reclassificacao(tabela: pd.DataFrame, caminho: Path = CSV_RECLASSIFICACAO) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tabela[COLUNAS_RECLASSIFICACAO].to_csv(caminho, index=False, encoding="utf-8")


if __name__ == "__main__":
    from src.load import carregar

    dados = carregar()
    reclass = ler_reclassificacao()
    principal = limpar(dados, PERIODO_PRINCIPAL, reclass)
    sensibilidade = limpar(dados, PERIODO_PREREGISTRADO, reclass)
    salvar_limpeza(principal)
    salvar_limpeza(sensibilidade, sufixo="_sensibilidade")
    salvar_reclassificacao(principal.reclassificacao)
    for nome, r in (("principal", principal), ("sensibilidade", sensibilidade)):
        print(f"{nome}: {r.resumo['recebidas']} recebidas, "
              f"{r.resumo['descartadas']} descartadas, {r.resumo['validas']} válidas")
    if principal.resumo["outro_pendentes"]:
        print(f"{len(principal.resumo['outro_pendentes'])} papel(is) \"Outro\" pendente(s) em "
              f"{CSV_RECLASSIFICACAO.relative_to(CSV_RECLASSIFICACAO.parents[2])}")
