"""Dados da página de metodologia e desvios (#12).

O texto dos desvios vem de DEVIATIONS.md e o das decisões de docs/decisoes-analise.md:
editar esses arquivos atualiza a página. O estado de cada desvio (ocorreu ou não) e os
números vêm do dicionário `desvios` calculado por src.pipeline.calcular a partir do CSV bruto.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config import RAIZ

ARQUIVO_DESVIOS = RAIZ / "DEVIATIONS.md"
ARQUIVO_DECISOES = RAIZ / "docs" / "decisoes-analise.md"

OCORREU, NAO_OCORREU, A_RESOLVER, A_PREENCHER = "Ocorreu", "Não ocorreu", "A resolver", "A preencher"


@dataclass
class Desvio:
    titulo: str
    resumo: str
    o_que: str
    por_que: str
    impacto: str
    condicional: bool


def _limpar_markdown(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def ler_desvios(caminho: Path = ARQUIVO_DESVIOS) -> list[Desvio]:
    """Uma entrada por seção `## ` de DEVIATIONS.md, com o quê, por quê e impacto."""
    texto = Path(caminho).read_text(encoding="utf-8")
    desvios = []
    for bloco in re.split(r"^## ", texto, flags=re.M)[1:]:
        titulo, _, corpo = bloco.partition("\n")
        campos = {}
        for nome, chave in (("Resumo", "resumo"), ("O quê", "o_que"), ("Por quê", "por_que"),
                            ("Impacto", "impacto")):
            achado = re.search(rf"\*\*{nome}:\*\*(.+?)(?=\n- \*\*|\Z)", corpo, flags=re.S)
            campos[chave] = _limpar_markdown(achado.group(1)) if achado else ""
        titulo = titulo.strip()
        desvios.append(Desvio(titulo=titulo, condicional="condicion" in titulo.lower(), **campos))
    return desvios


def ler_decisoes(caminho: Path = ARQUIVO_DECISOES) -> pd.DataFrame:
    """Uma linha por decisão numerada de docs/decisoes-analise.md."""
    texto = Path(caminho).read_text(encoding="utf-8")
    linhas = []
    for achado in re.finditer(r"^#{2,3} (\d+)\. (.+?)\n(.*?)(?=^#{2,3} |\Z)", texto, flags=re.S | re.M):
        numero, titulo, corpo = achado.groups()
        status = re.search(r"\*\*Status:\*\*\s*([^·\n]+)", corpo)
        desvio = re.search(r"\*\*Desvio:\*\*\s*(.+)", corpo)
        texto_desvio = _limpar_markdown(desvio.group(1)) if desvio else ""
        linhas.append({
            "Nº": int(numero),
            "Decisão": titulo.strip(),
            "Status": status.group(1).strip() if status else "Proposta",
            "É desvio?": "Sim" if texto_desvio.lower().startswith("sim") else "Não",
            "Detalhe": texto_desvio,
        })
    return pd.DataFrame(linhas, columns=["Nº", "Decisão", "Status", "É desvio?", "Detalhe"])


def titulo_curto(titulo: str) -> str:
    """Sem "(condicional)" nem o que vem depois de dois-pontos."""
    return re.sub(r"\s*\(condiciona[a-z]*\)", "", titulo).split(":")[0].strip()


def estado(desvio: Desvio, calculados: dict) -> tuple[str, str]:
    """(estado, o que os dados mostram) de um desvio, a partir de `desvios` do pipeline."""
    titulo = desvio.titulo.lower()
    if "[a preencher" in (desvio.o_que + desvio.por_que + desvio.impacto).lower():
        situacao_texto = A_PREENCHER
    else:
        situacao_texto = None

    if "a resolver" in titulo:
        return A_RESOLVER, "Aguarda decisão do grupo, sem olhar os p-valores."
    if "prorroga" in titulo:
        p = calculados["prorrogacao"]
        return situacao_texto or OCORREU, f"{p['recebidas']} recebidas e {p['validas']} válidas de 23/11 a 25/11."
    if "divulga" in titulo:
        return situacao_texto or OCORREU, ""
    if "permuta" in titulo:
        usos = calculados["testes_por_permutacao"]
        if usos:
            return OCORREU, "Usada em " + ", ".join(sorted({u["variavel"] for u in usos})) + "."
        return NAO_OCORREU, "Não foi necessária."
    if "amostra abaixo" in titulo or "cota" in titulo:
        a, g = calculados["amostra"], calculados["gestao"]
        ocorreu = a["abaixo_minimo"] or g["abaixo_meta"]
        return (OCORREU if ocorreu else NAO_OCORREU), (
            f"{a['validas']} válidas (mín. {a['minimo']}) · gestão {g['validas']} "
            f"(meta {g['meta']}, mín. {g['minimo']}).")
    if "não executáveis" in titulo or "nao executaveis" in titulo:
        lista = calculados["testes_nao_executaveis"]
        if lista:
            return OCORREU, f"{len(lista)} sem p-valor: " + ", ".join(t["variavel"] for t in lista) + "."
        return NAO_OCORREU, "Os 14 testes rodaram."
    if "cenário" in titulo or "cenario" in titulo:
        c = calculados["testes_por_cenario"]
        if c["executada"]:
            return OCORREU, "Alfa abaixo de 0,70 em " + " e ".join(c.get("alfa_abaixo_meta", [])) + "."
        return NAO_OCORREU, "Alfas de POS e PRA na meta."
    return situacao_texto or (NAO_OCORREU if desvio.condicional else OCORREU), ""


# ---------------------------------------------------------------------------
# Texto fixo do protocolo (Seções 1, 2, 5 e 7). Não contém resultados.
# ---------------------------------------------------------------------------
OBJETIVO_GQM = [
    ("Analisar", "a dívida técnica em projetos de software"),
    ("com o propósito de", "caracterizar e comparar"),
    ("com respeito à", "percepção do seu nível, impacto e gestão"),
    ("do ponto de vista de", "profissionais de diferentes papéis em equipes de desenvolvimento"),
    ("no contexto de", "empresas brasileiras de diferentes portes"),
]

QUESTOES = pd.DataFrame([
    ("RQ1", "Técnicos e gestores percebem o mesmo nível de DT?",
     "O nível percebido (NIV) não difere entre papéis."),
    ("RQ2", "A percepção do impacto da DT difere entre papéis?",
     "O impacto percebido (IMP) não difere entre papéis."),
    ("RQ3", "Como cada papel acha que a DT deveria ser priorizada e como ela é tratada na prática?",
     "Postura (POS), prática (PRA), frequência (E7) e quem decide (E8) não diferem entre papéis; "
     "a postura não difere da prática."),
    ("RQ4", "A percepção de DT está associada à experiência e ao porte da empresa?",
     "Não há correlação entre nível, impacto e postura e a experiência ou o porte."),
], columns=["RQ", "Pergunta", "Hipótese nula (H0)"])

PLANO = [
    ("População", "Profissionais maiores de 18 anos em equipes de desenvolvimento no Brasil, "
                  "há pelo menos 3 meses na equipe atual."),
    ("Amostragem", "Não probabilística, por conveniência e bola de neve. Meta de 60 válidas "
                   "(mínimo 50), com 20 de gestão (mínimo 15)."),
    ("Instrumento", "Questionário anônimo de 31 itens em 6 blocos (≈10 min): perfil, nível (NIV), "
                    "impacto (IMP), vinhetas de postura e prática (POS/PRA) e perguntas abertas."),
    ("Análise", "Testes não paramétricos (Mann-Whitney, Wilcoxon, χ²/Fisher, Spearman), α = 0,05, "
                "tamanho de efeito em todos e correção de Holm sobre os 14 testes."),
    ("Qualidade", "Item de atenção, straightlining, duplicatas e alfa de Cronbach com meta de 0,70."),
]

AMEACAS = pd.DataFrame([
    ("Viés de amostragem (rede dos integrantes)", "Externa",
     "Canais variados, cota por papel, perfil da amostra no dashboard, conclusões limitadas à amostra."),
    ("Não resposta", "Externa", "Formulário curto, lembretes nos canais, prorrogação da coleta."),
    ("Autosseleção (quem sofre mais com DT responde mais)", "Externa / construto",
     "Convite neutro, sem sugerir que DT é um problema."),
    ("Desequilíbrio entre papéis (poucos gestores)", "Conclusão",
     "Cota de gestão, análise em 2 grupos, testes não paramétricos, tamanho de efeito."),
    ("Desejabilidade social", "Construto",
     "Anonimato, itens neutros e invertidos, período definido nos itens de impacto, vinhetas concretas."),
    ("Entendimentos diferentes de \"dívida técnica\"", "Construto",
     "Definição padronizada antes dos itens, familiaridade (B8), pré-teste."),
    ("Ancoragem: \"deveria\" antes de \"acontece\"", "Interna",
     "Ordem fixa e declarada; a distância POS − PRA é lida com essa limitação."),
    ("Respostas descuidadas, duplicadas ou não independentes", "Interna / conclusão",
     "Item de atenção, straightlining, checagem de duplicatas; mesma equipe declarada como limitação."),
    ("Muitos testes e baixo poder", "Conclusão", "Correção de Holm e tamanho de efeito sempre relatado."),
], columns=["Ameaça", "Tipo", "Como foi tratada"])
