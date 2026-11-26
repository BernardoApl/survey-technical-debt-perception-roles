"""Respostas abertas F1 e F2: anonimização, codificação temática e frequências.

Protocolo, Seções 5.7 e 6; docs/decisoes-analise.md, itens 3 e 4.
Passo a passo para quem revisa e codifica: docs/procedimento-abertas.md.

Cada etapa só recebe o que a anterior liberou:
1. Anonimização: cada F1/F2 não vazio das respostas válidas vira uma linha de
   data/manual/revisao_anonimizacao.csv. Quem revisa edita `texto_anonimizado`,
   preenche `revisado_por` e troca `status` para "aprovado".
2. Codificação: cada texto aprovado entra na planilha de cada codificador
   (data/manual/codificacao_<nome>.csv), que preenche `codigos` sem ver a do outro.
3. Consenso: o que os dois codificaram diferente vai para
   data/manual/codificacao_consenso.csv; a dupla preenche `codigos_final` e
   `justificativa` juntos.
4. Saídas: textos aprovados e códigos finais em data/processed/; concordância,
   frequências e pendências em outputs/.

Os arquivos de data/manual/ com texto do respondente ficam fora do Git.

Uso: python -m src.abertas   (rodar de novo depois de cada rodada de revisão)
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config import (
    CODIFICADORES,
    CSV_ANONIMIZACAO,
    CSV_CONSENSO,
    CSV_LIVRO_CODIGOS,
    CSV_RECLASSIFICACAO,
    DIR_MANUAL,
    DIR_PROCESSADO,
    DIR_SAIDAS,
    ITENS_ABERTOS,
    PERIODO_PREREGISTRADO,
    PERIODO_PRINCIPAL,
    RECORTES,
    RQ_ABERTAS,
    csv_codificacao,
)
from src.describe import margem_erro

CHAVE = ["resp_id", "item"]
PENDENTE, APROVADO = "pendente", "aprovado"

COLUNAS_ANONIMIZACAO = [
    "resp_id", "item", "texto_original", "alertas",
    "texto_anonimizado", "status", "revisado_por", "observacao",
]
COLUNAS_CODIFICACAO = ["resp_id", "item", "texto", "codigos", "observacao"]
COLUNAS_CONSENSO = [
    "resp_id", "item", "texto",
    *(f"codigos_{nome}" for nome in CODIFICADORES),
    "codigos_final", "justificativa",
]
COLUNAS_LIVRO = ["codigo", "itens", "nome", "definicao", "exemplo"]


class ErroPreenchimento(ValueError):
    """Um arquivo preenchido à mão em data/manual/ tem valor inválido ou incompleto."""


# ---------------------------------------------------------------------------
# Leitura e escrita dos arquivos manuais
# ---------------------------------------------------------------------------
def ler_tabela(caminho: str | Path, colunas: list[str]) -> pd.DataFrame:
    """CSV preenchido à mão -> tabela só com `colunas` (vazia se o arquivo não existe)."""
    caminho = Path(caminho)
    if not caminho.exists():
        return pd.DataFrame(columns=colunas, dtype=str)
    tabela = pd.read_csv(caminho, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    faltam = [c for c in colunas if c not in tabela.columns]
    if faltam:
        raise ErroPreenchimento(f"{caminho.name} sem as colunas {faltam}")
    return tabela[colunas].reset_index(drop=True)


def salvar_tabela(tabela: pd.DataFrame, caminho: Path, colunas: list[str]) -> None:
    # utf-8 com BOM para o Excel reconhecer os acentos.
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tabela[colunas].to_csv(caminho, index=False, encoding="utf-8-sig")


def _chaves(tabela: pd.DataFrame) -> str:
    return ", ".join(f"{r}/{i}" for r, i in zip(tabela["resp_id"], tabela["item"]))


def _texto(valor) -> str:
    return "" if pd.isna(valor) else str(valor).replace("\r\n", "\n").strip()


def _sem_chaves(tabela: pd.DataFrame, chaves) -> pd.DataFrame:
    """Linhas de `tabela` cuja (resp_id, item) não está em `chaves`."""
    chaves = set(chaves)
    fora = [k not in chaves for k in zip(tabela["resp_id"], tabela["item"])]
    return tabela.loc[pd.Series(fora, index=tabela.index, dtype=bool)]


def _falhar(arquivo: str, problemas: list[str]) -> None:
    if problemas:
        raise ErroPreenchimento(f"{arquivo}:\n  " + "\n  ".join(problemas))


# ---------------------------------------------------------------------------
# 1. Anonimização
# ---------------------------------------------------------------------------
def textos_abertos(validas: pd.DataFrame) -> pd.DataFrame:
    """Respostas válidas -> uma linha por F1/F2 não vazio (resp_id, item, texto)."""
    longo = validas.melt(
        id_vars="resp_id", value_vars=ITENS_ABERTOS, var_name="item", value_name="texto"
    )
    longo["texto"] = longo["texto"].map(_texto)
    longo = longo[longo["texto"] != ""]
    return longo.sort_values(CHAVE, kind="mergesort").reset_index(drop=True)


# Não podem sobrar num texto aprovado.
PADROES_PROIBIDOS = {
    "e-mail": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    "link": re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE),
}
# Só chamam a atenção de quem revisa; a revisão é sempre manual.
PADROES_ALERTA = {
    **PADROES_PROIBIDOS,
    "@perfil": re.compile(r"(?<![\w.])@\w+"),
    "número longo": re.compile(r"\d[\d.\-/ ]{6,}\d"),
}
# Termos técnicos genéricos que costumam vir com maiúscula e podem ficar
# (docs/decisoes-analise.md, item 3). Em minúsculas.
TERMOS_GENERICOS = {
    "java", "javascript", "typescript", "python", "kotlin", "swift", "go", "golang",
    "php", "ruby", "rails", "c", "net", "dotnet", "react", "angular", "vue", "node",
    "nodejs", "spring", "django", "flutter", "android", "ios", "linux", "windows",
    "aws", "azure", "gcp", "cloud", "docker", "kubernetes", "k8s", "terraform",
    "jenkins", "git", "github", "gitlab", "bitbucket", "jira", "sql", "nosql",
    "mysql", "postgres", "postgresql", "oracle", "mongodb", "redis", "kafka",
    "api", "apis", "rest", "graphql", "ci", "cd", "devops", "sre", "qa", "po",
    "pm", "ux", "ui", "mvp", "dt", "ti", "erp", "crm", "sprint", "sprints",
    "scrum", "kanban", "backlog", "legado", "front", "back", "end", "frontend",
    "backend", "mobile", "microsserviços", "monolito", "deploy", "pr", "prs",
}
_PALAVRA = re.compile(r"[^\W\d_][\w\-]*")


def _palavras_com_maiuscula(texto: str) -> list[str]:
    """Palavras com maiúscula fora do início de frase, e siglas em qualquer lugar."""
    achadas = []
    for m in _PALAVRA.finditer(texto):
        palavra = m.group()
        if not palavra[0].isupper() or palavra.casefold() in TERMOS_GENERICOS:
            continue
        antes = texto[: m.start()].rstrip(" \t\"'(“«-")
        inicio_frase = antes == "" or antes[-1] in ".!?:\n"
        sigla = len(palavra) >= 2 and palavra.isupper()
        if sigla or not inicio_frase:
            achadas.append(palavra)
    return list(dict.fromkeys(achadas))


def alertas(texto: str) -> str:
    """Trechos que podem identificar alguém, para quem revisa conferir primeiro."""
    achados = [
        f"{nome}: {m.group()}" for nome, padrao in PADROES_ALERTA.items()
        for m in padrao.finditer(texto)
    ]
    palavras = _palavras_com_maiuscula(texto)
    if palavras:
        achados.append("maiúscula: " + ", ".join(palavras))
    return " | ".join(achados)


def atualizar_revisao(revisao: pd.DataFrame, textos: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta à revisão os textos novos, como pendentes, sem mexer no que já foi revisado.

    Linhas de respostas que deixaram de ser válidas ficam no arquivo, mas não
    saem nas saídas.
    """
    _falhar(CSV_ANONIMIZACAO.name, _repetidas(revisao))
    original = {
        (r, i): _texto(t)
        for r, i, t in zip(revisao["resp_id"], revisao["item"], revisao["texto_original"])
    }
    mudou = [
        f"{r}/{i}" for r, i, t in zip(textos["resp_id"], textos["item"], textos["texto"])
        if (r, i) in original and original[(r, i)] != t
    ]
    _falhar(CSV_ANONIMIZACAO.name, [
        f"o texto de {', '.join(mudou)} no CSV bruto é diferente do texto_original "
        "revisado. O CSV mudou? A numeração resp_id depende do CSV final do formulário."
    ] if mudou else [])

    novos = _sem_chaves(textos, original)
    linhas = pd.DataFrame({
        "resp_id": novos["resp_id"], "item": novos["item"],
        "texto_original": novos["texto"], "alertas": novos["texto"].map(alertas),
        "texto_anonimizado": novos["texto"], "status": PENDENTE,
        "revisado_por": "", "observacao": "",
    }, columns=COLUNAS_ANONIMIZACAO)
    juntas = pd.concat([revisao, linhas], ignore_index=True) if len(revisao) else linhas
    return juntas.sort_values(CHAVE, kind="mergesort").reset_index(drop=True)


def _repetidas(tabela: pd.DataFrame) -> list[str]:
    repetidas = tabela.duplicated(CHAVE, keep="first")
    return [f"linhas repetidas: {_chaves(tabela[repetidas])}"] if repetidas.any() else []


def validar_revisao(revisao: pd.DataFrame) -> None:
    problemas = _repetidas(revisao)
    status = revisao["status"].map(_texto).str.lower()
    invalido = ~status.isin([PENDENTE, APROVADO, ""])
    if invalido.any():
        problemas.append(
            f"status inválido em {_chaves(revisao[invalido])}; use \"{PENDENTE}\" ou \"{APROVADO}\""
        )
    aprovado = status.eq(APROVADO)
    texto = revisao["texto_anonimizado"].map(_texto)
    checagens = {
        "aprovado sem revisado_por": revisao["revisado_por"].map(_texto).eq(""),
        "aprovado com texto_anonimizado vazio (use [removido])": texto.eq(""),
        "aprovado ainda com e-mail ou link": texto.map(
            lambda t: any(p.search(t) for p in PADROES_PROIBIDOS.values())
        ),
    }
    for descricao, falhou in checagens.items():
        if (aprovado & falhou).any():
            problemas.append(f"{descricao}: {_chaves(revisao[aprovado & falhou])}")
    _falhar(CSV_ANONIMIZACAO.name, problemas)


def textos_aprovados(revisao: pd.DataFrame, textos: pd.DataFrame) -> pd.DataFrame:
    """Só os textos atuais com status aprovado, já anonimizados (resp_id, item, texto)."""
    aprovado = revisao[revisao["status"].map(_texto).str.lower().eq(APROVADO)]
    juntos = textos[CHAVE].merge(aprovado[CHAVE + ["texto_anonimizado"]], on=CHAVE)
    juntos["texto"] = juntos.pop("texto_anonimizado").map(_texto)
    return juntos.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. Livro de códigos e codificação
# ---------------------------------------------------------------------------
def separar_codigos(valor) -> frozenset[str]:
    """'a; b' ou 'a, b' -> {'a', 'b'}."""
    return frozenset(c.strip().lower() for c in re.split(r"[;,]", _texto(valor)) if c.strip())


def juntar_codigos(codigos) -> str:
    return ";".join(sorted(codigos))


def ler_livro(caminho: str | Path = CSV_LIVRO_CODIGOS) -> pd.DataFrame:
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Livro de códigos não encontrado em {caminho}")
    livro = ler_tabela(caminho, COLUNAS_LIVRO)
    livro["codigo"] = livro["codigo"].str.strip()
    problemas = []
    invalidos = livro.loc[~livro["codigo"].str.fullmatch(r"[a-z0-9_]+"), "codigo"]
    if len(invalidos):
        problemas.append(f"código fora do padrão [a-z0-9_]: {invalidos.tolist()}")
    if livro["codigo"].duplicated().any():
        problemas.append(f"código repetido: {livro.loc[livro['codigo'].duplicated(), 'codigo'].tolist()}")
    itens = livro["itens"].map(separar_codigos)
    sem_item = livro.loc[itens.map(lambda s: not s or not s <= {i.lower() for i in ITENS_ABERTOS}),
                         "codigo"]
    if len(sem_item):
        problemas.append(f"coluna itens deve ser F1, F2 ou F1;F2 em: {sem_item.tolist()}")
    _falhar(caminho.name, problemas)
    return livro


def codigos_por_item(livro: pd.DataFrame) -> dict[str, list[str]]:
    """item -> códigos válidos, na ordem do livro."""
    itens = livro["itens"].map(separar_codigos)
    return {
        item: [c for c, s in zip(livro["codigo"], itens) if item.lower() in s]
        for item in ITENS_ABERTOS
    }


def atualizar_codificacao(planilha: pd.DataFrame, aprovados: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta os textos aprovados que faltam e atualiza o texto dos que já estão."""
    planilha = planilha.copy()
    texto = {(r, i): t for r, i, t in zip(aprovados["resp_id"], aprovados["item"],
                                         aprovados["texto"])}
    chaves = list(zip(planilha["resp_id"], planilha["item"]))
    planilha["texto"] = [texto.get(k, t) for k, t in zip(chaves, planilha["texto"])]
    novos = _sem_chaves(aprovados, chaves)
    linhas = pd.DataFrame({
        "resp_id": novos["resp_id"], "item": novos["item"], "texto": novos["texto"],
        "codigos": "", "observacao": "",
    }, columns=COLUNAS_CODIFICACAO)
    juntas = pd.concat([planilha, linhas], ignore_index=True) if len(planilha) else linhas
    return juntas.sort_values(CHAVE, kind="mergesort").reset_index(drop=True)


def _codigos_invalidos(chaves_itens_codigos, validos: dict[str, list[str]]) -> list[str]:
    problemas = []
    for resp_id, item, codigos in chaves_itens_codigos:
        fora = sorted(codigos - set(validos.get(item, [])))
        if fora:
            problemas.append(f"{resp_id}/{item}: código(s) fora do livro para {item}: {fora}")
    return problemas


def validar_codificacao(planilha: pd.DataFrame, validos: dict[str, list[str]],
                        arquivo: str) -> None:
    problemas = _repetidas(planilha) + _codigos_invalidos(
        zip(planilha["resp_id"], planilha["item"], planilha["codigos"].map(separar_codigos)),
        validos,
    )
    _falhar(arquivo, problemas)


# ---------------------------------------------------------------------------
# 3. Comparação, consenso e concordância
# ---------------------------------------------------------------------------
def comparar(aprovados: pd.DataFrame, planilhas: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Textos aprovados com o conjunto de códigos de cada codificador (vazio = não codificou)."""
    base = aprovados[CHAVE + ["texto"]].copy()
    chaves = list(zip(base["resp_id"], base["item"]))
    for nome in CODIFICADORES:
        p = planilhas[nome]
        codigos = dict(zip(zip(p["resp_id"], p["item"]), p["codigos"].map(separar_codigos)))
        base[nome] = pd.Series([codigos.get(k, frozenset()) for k in chaves],
                               index=base.index, dtype=object)
    return base


def consolidar(
    base: pd.DataFrame, consenso: pd.DataFrame, validos: dict[str, list[str]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devolve (finais, consenso atualizado).

    `finais` tem uma linha por texto já resolvido: os dois codificaram igual
    (origem "concordância") ou a dupla decidiu a divergência ("consenso").
    O consenso mantém também decisões de respostas que deixaram de ser ativas.
    """
    _falhar(CSV_CONSENSO.name, _repetidas(consenso))
    decisoes = {(r.resp_id, r.item): r._asdict() for r in consenso.itertuples(index=False)}
    a, b = CODIFICADORES
    finais, linhas_consenso, decididas = [], [], []
    for linha in base.itertuples(index=False):
        cod_a, cod_b = getattr(linha, a), getattr(linha, b)
        if not cod_a or not cod_b:
            continue
        chave = {"resp_id": linha.resp_id, "item": linha.item}
        if cod_a == cod_b:
            finais.append({**chave, "codigos": cod_a, "origem": "concordância"})
            continue
        anterior = decisoes.get((linha.resp_id, linha.item), {})
        final = separar_codigos(anterior.get("codigos_final", ""))
        justificativa = _texto(anterior.get("justificativa", ""))
        if final and (separar_codigos(anterior.get(f"codigos_{a}", "")) != cod_a
                      or separar_codigos(anterior.get(f"codigos_{b}", "")) != cod_b
                      or _texto(anterior.get("texto", "")) != _texto(linha.texto)):
            raise ErroPreenchimento(
                f"{CSV_CONSENSO.name}: {linha.resp_id}/{linha.item} tem consenso anterior "
                "com texto ou codificação alterados; revise a decisão manualmente antes de continuar."
            )
        linhas_consenso.append({
            **chave, "texto": linha.texto, f"codigos_{a}": juntar_codigos(cod_a),
            f"codigos_{b}": juntar_codigos(cod_b), "codigos_final": juntar_codigos(final),
            "justificativa": justificativa,
        })
        if final:
            decididas.append((linha.resp_id, linha.item, final, justificativa))
            finais.append({**chave, "codigos": final, "origem": "consenso"})

    problemas = _codigos_invalidos(((r, i, f) for r, i, f, _ in decididas), validos)
    sem_justificativa = [f"{r}/{i}" for r, i, _, j in decididas if not j]
    if sem_justificativa:
        problemas.append(f"codigos_final sem justificativa: {', '.join(sem_justificativa)}")
    _falhar(CSV_CONSENSO.name, problemas)

    finais = pd.DataFrame(finais, columns=CHAVE + ["codigos", "origem"])
    atuais = {(r["resp_id"], r["item"]) for r in linhas_consenso}
    anteriores = _sem_chaves(consenso, atuais)
    consenso = pd.concat([anteriores, pd.DataFrame(linhas_consenso, columns=COLUNAS_CONSENSO)],
                         ignore_index=True).sort_values(CHAVE, kind="mergesort").reset_index(drop=True)
    return finais, consenso


def kappa_cohen(x: pd.Series, y: pd.Series) -> float:
    """Kappa de Cohen para dois vetores binários (NaN se a concordância esperada for 1)."""
    n = len(x)
    if n == 0:
        return math.nan
    x, y = x.astype(bool), y.astype(bool)
    observada = (x == y).mean()
    px, py = x.mean(), y.mean()
    esperada = px * py + (1 - px) * (1 - py)
    return math.nan if esperada == 1 else float((observada - esperada) / (1 - esperada))


def concordancia(base: pd.DataFrame, validos: dict[str, list[str]]) -> pd.DataFrame:
    """Concordância entre os codificadores, antes do consenso (descritiva, não é critério).

    Por item: % de textos com exatamente os mesmos códigos e, por código,
    % de concordância e kappa de Cohen sobre presença/ausência.
    """
    a, b = CODIFICADORES
    ambos = base[base[a].map(bool) & base[b].map(bool)]
    linhas = []
    for item in ITENS_ABERTOS:
        sub = ambos[ambos["item"] == item]
        iguais = pd.Series([x == y for x, y in zip(sub[a], sub[b])], dtype=bool)
        linhas.append({"item": item, "codigo": "(conjunto inteiro)", "n": len(sub),
                       "concordancia_pct": 100 * iguais.mean() if len(sub) else math.nan,
                       "kappa": math.nan})
        for codigo in validos[item]:
            x = sub[a].map(lambda s, c=codigo: c in s)
            y = sub[b].map(lambda s, c=codigo: c in s)
            linhas.append({
                "item": item, "codigo": codigo, "n": len(sub),
                "concordancia_pct": 100 * (x == y).mean() if len(sub) else math.nan,
                "kappa": kappa_cohen(x, y),
            })
    return pd.DataFrame(linhas, columns=["item", "codigo", "n", "concordancia_pct", "kappa"])


# ---------------------------------------------------------------------------
# 4. Frequências com margem de erro (margem_erro vem de src.describe)
# ---------------------------------------------------------------------------
def frequencias(finais: pd.DataFrame, grupo_por_resp: pd.Series,
                livro: pd.DataFrame) -> pd.DataFrame:
    """Frequência de cada código por item, no total e por grupo de papel.

    n = textos daquele item com códigos finais no recorte (inclui
    nao_codificavel); k = textos com o código. Um texto pode ter vários
    códigos, então os % de um item não somam 100. Respostas com papel "Outro"
    ainda sem grupo entram só no total.
    """
    nomes = dict(zip(livro["codigo"], livro["nome"]))
    validos = codigos_por_item(livro)
    linhas = []
    for item in ITENS_ABERTOS:
        do_item = finais[finais["item"] == item]
        grupos = do_item["resp_id"].map(grupo_por_resp)
        for recorte in RECORTES:
            sub = do_item if recorte == "total" else do_item[grupos == recorte]
            n = len(sub)
            for codigo in validos[item]:
                k = int(sub["codigos"].map(lambda s, c=codigo: c in s).sum())
                p = k / n if n else math.nan
                linhas.append({
                    "item": item, "rq": RQ_ABERTAS[item], "codigo": codigo,
                    "nome": nomes[codigo], "recorte": recorte, "n": n, "k": k,
                    "pct": 100 * p, "margem_pp": 100 * margem_erro(p, n),
                })
    return pd.DataFrame(linhas, columns=["item", "rq", "codigo", "nome", "recorte",
                                         "n", "k", "pct", "margem_pp"])


# ---------------------------------------------------------------------------
# Tudo junto
# ---------------------------------------------------------------------------
@dataclass
class ResultadoAbertas:
    revisao: pd.DataFrame
    planilhas: dict[str, pd.DataFrame]
    consenso: pd.DataFrame
    textos_aprovados: pd.DataFrame  # resp_id, item, texto (anonimizado); uso interno
    textos_publicos: pd.DataFrame  # item, grupo, codigos, texto; sem resp_id
    finais: pd.DataFrame  # resp_id, item, codigos (frozenset), origem
    concordancia: pd.DataFrame
    frequencias: pd.DataFrame
    pendencias: dict
    # Período pré-registrado (protocolo, Seção 8; docs/decisoes-analise.md, item 1).
    frequencias_sensibilidade: pd.DataFrame | None = None

    @property
    def codigos_longos(self) -> pd.DataFrame:
        """Uma linha por (resp_id, item, codigo): formato público de data/processed/."""
        linhas = [
            {"resp_id": r, "item": i, "codigo": c}
            for r, i, cs in zip(self.finais["resp_id"], self.finais["item"], self.finais["codigos"])
            for c in sorted(cs)
        ]
        return pd.DataFrame(linhas, columns=["resp_id", "item", "codigo"])


def _vazia(colunas):
    return pd.DataFrame(columns=colunas, dtype=str)


COLUNAS_TEXTOS_PUBLICOS = ["item", "grupo", "codigos", "texto"]


def textos_publicos(aprovados: pd.DataFrame, finais: pd.DataFrame,
                    grupo_por_resp: pd.Series) -> pd.DataFrame:
    """Textos aprovados sem resp_id, para não ligar o texto ao perfil (protocolo, Seção 6).

    Ficam só o grupo de papel e os códigos finais, que o dashboard usa para
    escolher exemplos. A ordem é por item, grupo, códigos e texto, e não pela
    ordem de envio. `grupo` vazio = papel "Outro" ainda sem classificação;
    `codigos` vazio = codificação ainda não resolvida.
    """
    codigos = {(r, i): juntar_codigos(c)
               for r, i, c in zip(finais["resp_id"], finais["item"], finais["codigos"])}
    publicos = pd.DataFrame({
        "item": aprovados["item"],
        "grupo": aprovados["resp_id"].map(grupo_por_resp).astype(object).fillna(""),
        "codigos": [codigos.get(k, "") for k in zip(aprovados["resp_id"], aprovados["item"])],
        "texto": aprovados["texto"],
    }, columns=COLUNAS_TEXTOS_PUBLICOS)
    return publicos.sort_values(COLUNAS_TEXTOS_PUBLICOS, kind="mergesort").reset_index(drop=True)


def processar(
    validas: pd.DataFrame,
    livro: pd.DataFrame,
    revisao: pd.DataFrame | None = None,
    planilhas: dict[str, pd.DataFrame] | None = None,
    consenso: pd.DataFrame | None = None,
    reclassificacao: pd.DataFrame | None = None,
    validas_sensibilidade: pd.DataFrame | None = None,
) -> ResultadoAbertas:
    """Roda as etapas 1 a 4 sobre as respostas válidas de `src.clean.limpar`.

    `validas` vem da análise principal. Se `validas_sensibilidade` (período
    pré-registrado, um subconjunto) for dada, as frequências também saem só para ela.
    """
    from src.recode import grupo_papel

    revisao = _vazia(COLUNAS_ANONIMIZACAO) if revisao is None else revisao
    consenso = _vazia(COLUNAS_CONSENSO) if consenso is None else consenso
    planilhas = planilhas or {}
    planilhas = {n: planilhas.get(n, _vazia(COLUNAS_CODIFICACAO)) for n in CODIFICADORES}
    validos = codigos_por_item(livro)

    textos = textos_abertos(validas)
    revisao = atualizar_revisao(revisao, textos)
    validar_revisao(revisao)
    aprovados = textos_aprovados(revisao, textos)

    planilhas = {n: atualizar_codificacao(p, aprovados) for n, p in planilhas.items()}
    for nome, planilha in planilhas.items():
        validar_codificacao(planilha, validos, csv_codificacao(nome).name)

    base = comparar(aprovados, planilhas)
    finais, consenso = consolidar(base, consenso, validos)
    grupos = grupo_papel(validas["B2"], reclassificacao)["grupo"]
    grupo_por_resp = pd.Series(grupos.to_numpy(), index=validas["resp_id"])

    pendencias = {
        "textos": len(textos),
        "anonimizacao": len(textos) - len(aprovados),
        "codificacao": {n: int((~base[n].map(bool)).sum()) for n in CODIFICADORES},
        "consenso": sum(1 for linha in base.itertuples(index=False)
                        if getattr(linha, CODIFICADORES[0]) and getattr(linha, CODIFICADORES[1])
                        and getattr(linha, CODIFICADORES[0]) != getattr(linha, CODIFICADORES[1])
                        and not any((r == linha.resp_id and i == linha.item)
                                    for r, i in zip(finais["resp_id"], finais["item"]))),
        "resolvidos": len(finais),
    }
    sensibilidade = None
    if validas_sensibilidade is not None:
        no_periodo = finais[finais["resp_id"].isin(validas_sensibilidade["resp_id"])]
        sensibilidade = frequencias(no_periodo, grupo_por_resp, livro)
    return ResultadoAbertas(
        revisao=revisao, planilhas=planilhas, consenso=consenso,
        textos_aprovados=aprovados,
        textos_publicos=textos_publicos(aprovados, finais, grupo_por_resp),
        finais=finais,
        concordancia=concordancia(base, validos),
        frequencias=frequencias(finais, grupo_por_resp, livro),
        pendencias=pendencias,
        frequencias_sensibilidade=sensibilidade,
    )


def ler_manuais(dir_manual: Path = DIR_MANUAL):
    """(revisão, planilhas dos codificadores, consenso) de data/manual/."""
    revisao = ler_tabela(dir_manual / CSV_ANONIMIZACAO.name, COLUNAS_ANONIMIZACAO)
    planilhas = {
        n: ler_tabela(dir_manual / csv_codificacao(n).name, COLUNAS_CODIFICACAO)
        for n in CODIFICADORES
    }
    consenso = ler_tabela(dir_manual / CSV_CONSENSO.name, COLUNAS_CONSENSO)
    return revisao, planilhas, consenso


def salvar_abertas(
    resultado: ResultadoAbertas,
    dir_manual: Path = DIR_MANUAL,
    dir_processado: Path = DIR_PROCESSADO,
    dir_saidas: Path = DIR_SAIDAS,
) -> None:
    """Grava os arquivos de trabalho (data/manual/, fora do Git) e as saídas.

    data/processed/ recebe só texto aprovado e códigos finais; o texto
    original nunca sai de data/manual/revisao_anonimizacao.csv. O arquivo de
    textos não tem resp_id, e o de códigos não tem texto: nenhum arquivo
    público liga um relato ao perfil completo de quem respondeu.
    """
    salvar_tabela(resultado.revisao, dir_manual / CSV_ANONIMIZACAO.name, COLUNAS_ANONIMIZACAO)
    for nome, planilha in resultado.planilhas.items():
        salvar_tabela(planilha, dir_manual / csv_codificacao(nome).name, COLUNAS_CODIFICACAO)
    salvar_tabela(resultado.consenso, dir_manual / CSV_CONSENSO.name, COLUNAS_CONSENSO)

    dir_processado.mkdir(parents=True, exist_ok=True)
    resultado.textos_publicos.to_csv(dir_processado / "respostas_abertas.csv", index=False)
    resultado.codigos_longos.to_csv(dir_processado / "codigos_abertas.csv", index=False)

    dir_saidas.mkdir(parents=True, exist_ok=True)
    resultado.concordancia.to_csv(dir_saidas / "concordancia_codificacao.csv", index=False)
    resultado.frequencias.to_csv(dir_saidas / "frequencia_codigos.csv", index=False)
    if resultado.frequencias_sensibilidade is not None:
        resultado.frequencias_sensibilidade.to_csv(
            dir_saidas / "frequencia_codigos_sensibilidade.csv", index=False
        )
    (dir_saidas / "pendencias_abertas.json").write_text(
        json.dumps(resultado.pendencias, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def relatorio(pendencias: dict, outro_pendentes: list[str]) -> str:
    p = pendencias
    codificacao = ", ".join(f"{n} {k}" for n, k in p["codificacao"].items())
    pronto = (not outro_pendentes and p["anonimizacao"] == 0 and p["consenso"] == 0
              and not any(p["codificacao"].values()))
    return "\n".join([
        f"Respostas abertas (análise principal): {p['textos']} texto(s) de F1/F2",
        f"  papel \"Outro\" sem classificação: {len(outro_pendentes)}  -> "
        f"data/manual/{CSV_RECLASSIFICACAO.name}",
        f"  anonimização pendente:           {p['anonimizacao']}  -> "
        f"data/manual/{CSV_ANONIMIZACAO.name}",
        f"  codificação pendente:            {codificacao}  -> data/manual/codificacao_<nome>.csv"
        " (só textos aprovados entram)",
        f"  divergências sem consenso:       {p['consenso']}  -> data/manual/{CSV_CONSENSO.name}",
        f"  textos com códigos finais:       {p['resolvidos']}",
        f"  pronto: {'sim' if pronto else 'não'}",
    ])


if __name__ == "__main__":
    from src.clean import ler_reclassificacao, limpar, salvar_reclassificacao
    from src.load import carregar

    dados, reclass = carregar(), ler_reclassificacao()
    limpeza = limpar(dados, PERIODO_PRINCIPAL, reclass)
    sensibilidade = limpar(dados, PERIODO_PREREGISTRADO, reclass)
    salvar_reclassificacao(limpeza.reclassificacao)
    revisao, planilhas, consenso = ler_manuais()
    resultado = processar(limpeza.validas, ler_livro(), revisao, planilhas, consenso,
                          limpeza.reclassificacao, sensibilidade.validas)
    salvar_abertas(resultado)
    print(relatorio(resultado.pendencias, limpeza.resumo["outro_pendentes"]))
