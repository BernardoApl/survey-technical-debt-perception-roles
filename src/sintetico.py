"""Gerador de CSV sintético no formato do Google Forms.

Serve para desenvolver e testar o pipeline e o dashboard sem o CSV real.
Os respondentes são fictícios e as respostas, aleatórias: nenhum resultado
deve ser tirado daqui.

Cabeçalhos e textos de opção copiados do script do Google Apps Script que
gerou o formulário oficial (criarFormularioOficial). Se o formulário mudar,
atualizar aqui e em src/config.py (COLUNAS).

Uso: python -m src.sintetico [--n 80] [--saida data/raw/sintetico.csv]
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from src.config import (
    CODIGOS,
    LIKERT,
    NAO,
    NAO_SEI,
    NSA,
    PAPEIS_GESTAO,
    PAPEIS_TECNICOS,
    RAIZ,
    SEED,
    SIM,
)

# Cabeçalhos completos (o começo de cada um bate com src/config.py:COLUNAS).
CABECALHOS = [
    "Carimbo de data/hora",
    "Li o termo de consentimento e aceito participar.",
    "Você trabalha hoje em uma equipe de desenvolvimento de software, há pelo menos 3 meses?",
    "Qual é o seu papel principal na equipe?",
    "Há quanto tempo você trabalha com TI?",
    "Há quanto tempo você está na equipe atual?",
    "Quantos funcionários a empresa tem?",
    "Em que tipo de empresa você trabalha?",
    "Quantas pessoas há na sua equipe?",
    "Antes desta pesquisa, quão familiarizado(a) você estava com o termo \"dívida técnica\"?",
    "O sistema em que trabalho tem partes que precisam ser refeitas para facilitar a manutenção.",
    "Atalhos técnicos para cumprir prazo são comuns na minha equipe.",
    "Os testes automatizados do sistema são insuficientes para dar segurança ao fazer mudanças.",
    "O sistema em que trabalho é fácil de modificar sem gerar novos problemas.",
    "De 0 a 10, qual é o nível de dívida técnica do seu projeto principal?",
    "Quais tipos de dívida técnica existem no seu projeto? (marque todas que se aplicam)",
    "Nos últimos 3 meses, problemas no código ou na arquitetura atrasaram entregas da minha equipe.",
    "Nos últimos 3 meses, problemas técnicos no sistema quase não causaram defeitos em produção.",
    "Nos últimos 3 meses, fazer mudanças no sistema exigiu mais esforço do que deveria por causa de problemas técnicos acumulados.",
    "Para confirmar que está lendo, marque \"Discordo parcialmente\" nesta pergunta.",
    "Nos últimos 3 meses, problemas técnicos no sistema deixaram pessoas da equipe desmotivadas ou frustradas.",
    "Qual é o MAIOR efeito da dívida técnica na sua equipe?",
    "No cenário 1, o que a equipe deveria fazer?",
    "No cenário 1, o que normalmente acontece na sua equipe?",
    "No cenário 2, depois de aplicar a correção, o que a equipe deveria fazer?",
    "No cenário 2, o que normalmente acontece na sua equipe?",
    "No cenário 3, o que a equipe deveria fazer?",
    "No cenário 3, o que normalmente acontece na sua equipe?",
    "Com que frequência sua equipe dedica tempo para reduzir dívida técnica?",
    "Quem decide, na prática, quando reduzir a dívida técnica?",
    "Descreva um exemplo recente em que a dívida técnica afetou seu trabalho.",
    "O que mais dificulta a redução da dívida técnica na sua equipe?",
]

PAPEIS_OUTRO = ["Engenheiro de software", "Designer UX", "Analista de TI", "CTO"]

B3 = ["Menos de 1 ano", "1 a 2 anos", "3 a 5 anos", "6 a 10 anos", "Mais de 10 anos"]
B4 = ["3 a 11 meses", "1 a 2 anos", "3 a 5 anos", "Mais de 5 anos"]
B5 = ["Até 49", "50 a 249", "250 a 999", "1.000 ou mais"]
B6 = [
    "Produto próprio",
    "Consultoria / fábrica de software",
    "Setor público",
    "Startup",
    "TI interna de empresa não-TI",
    "Outro",
]
B7 = ["1 a 5 pessoas", "6 a 10 pessoas", "11 a 20 pessoas", "Mais de 20 pessoas"]
C6 = [
    "Código",
    "Arquitetura",
    "Testes",
    "Documentação",
    "Infraestrutura / build",
    "Requisitos",
]
D5 = [
    "Atraso de entregas",
    "Defeitos em produção",
    "Custo de manutenção",
    "Desmotivação",
    "Tempo para novos membros aprenderem o sistema",
    "Nenhum efeito relevante",
    NAO_SEI,
]
VINHETAS = {
    1: [
        "Seguir o padrão do código atual e entregar no prazo",
        "Seguir o padrão atual e registrar a melhoria no backlog para depois",
        "Melhorar só a parte que vai ser mexida, mesmo que leve um pouco mais",
        "Reorganizar o módulo antes, mesmo que a entrega atrase",
    ],
    2: [
        "Seguir para as próximas tarefas, mantendo a solução improvisada no código",
        "Anotar no backlog, sem prazo, e seguir com o planejado",
        "Agendar a correção para algumas sprints depois, convivendo com o risco",
        "Refazer já na próxima sprint, atrasando outras tarefas",
    ],
    3: [
        "Adiar e manter o foco nas funcionalidades até perto do fim do suporte",
        "Registrar no backlog e decidir depois, sem mexer no planejado",
        "Atualizar aos poucos, deixando as entregas mais lentas por vários meses",
        "Parar duas semanas e atualizar agora, adiando funcionalidades",
    ],
}
E7 = [
    "Nunca",
    "Raramente (algumas vezes por ano)",
    "Às vezes (cerca de uma vez por mês)",
    "Frequentemente (na maioria das sprints ou ciclos)",
    "Sempre (há tempo reservado em todo ciclo)",
    NAO_SEI,
]
E8 = [
    "Devs",
    "Tech lead",
    "PO / PM",
    "Gerente",
    "Decisão conjunta",
    "Ninguém formalmente",
    NAO_SEI,
]
F1_EXEMPLOS = [
    "Uma mudança simples levou uma semana porque o módulo não tinha testes.",
    "O deploy quebrou duas vezes por causa de configuração duplicada.\nTivemos que voltar a versão.",
    'O time chama aquele serviço de "monstro" porque ninguém quer mexer nele.',
]
F2_EXEMPLOS = [
    "Pressão de prazo.",
    "Falta de apoio da gestão para reservar tempo.",
    "Código legado sem documentação.",
]

INICIO_COLETA = datetime(2026, 11, 13, 8, 0, 0)


def formatar_data(momento: datetime) -> str:
    """Formato do Forms: '2026/11/16 9:23:49 AM GMT-3'."""
    hora12 = momento.hour % 12 or 12
    ampm = "AM" if momento.hour < 12 else "PM"
    return f"{momento:%Y/%m/%d} {hora12}:{momento:%M:%S} {ampm} GMT-3"


def _resposta(rng: np.random.Generator, momento: datetime) -> list[str]:
    def escolha(opcoes):
        return str(rng.choice(opcoes))

    gestao = rng.random() < 0.3
    papel = escolha(PAPEIS_GESTAO if gestao else PAPEIS_TECNICOS)
    if rng.random() < 0.05:
        papel = escolha(PAPEIS_OUTRO)

    def likert():
        return NSA if rng.random() < (0.15 if gestao else 0.05) else escolha(LIKERT)

    tipos = [t for t in C6 if rng.random() < 0.4] or [escolha(C6 + ["Nenhum", NAO_SEI])]
    linha = [
        formatar_data(momento),
        SIM,
        SIM,
        papel,
        escolha(B3),
        escolha(B4),
        escolha(B5),
        escolha(B6),
        escolha(B7),
        str(rng.integers(1, 6)),
        likert(), likert(), likert(), likert(),
        str(rng.integers(0, 11)),
        ";".join(tipos),
        likert(), likert(), likert(),
        LIKERT[1],  # ATN correto
        likert(),
        escolha(D5),
    ]
    for cenario in (1, 2, 3):
        linha.append(escolha(VINHETAS[cenario]))
        linha.append(escolha(VINHETAS[cenario] + [NAO_SEI]))
    linha += [
        escolha(E7),
        escolha(E8),
        escolha(F1_EXEMPLOS) if rng.random() < 0.5 else "",
        escolha(F2_EXEMPLOS) if rng.random() < 0.5 else "",
    ]
    return linha


def gerar(n: int = 80, seed: int = SEED) -> list[list[str]]:
    """Gera `n` respostas comuns mais casos especiais para testar a limpeza."""
    rng = np.random.default_rng(seed)
    duracao = timedelta(days=12, hours=15)  # 13/11 08:00 até ~25/11 23:00
    momentos = sorted(
        INICIO_COLETA + duracao * float(rng.random()) for _ in range(n)
    )
    linhas = [_resposta(rng, m) for m in momentos]

    def especial(momento, **trocas):
        linha = _resposta(rng, momento)
        for codigo, valor in trocas.items():
            linha[_POS[codigo]] = valor
        linhas.append(linha)
        return linha

    # Casos especiais para os testes da limpeza (#4) e da recodificação (#3).
    especial(datetime(2026, 11, 12, 23, 30))                         # antes da coleta
    especial(datetime(2026, 11, 26, 0, 30))                          # depois da prorrogação
    especial(datetime(2026, 11, 24, 14, 0))                          # só na análise principal
    # "Não" em A1 ou B1 envia o formulário na hora: o resto da linha fica vazio.
    vazio_a1 = {c: "" for c in CODIGOS[2:]}
    vazio_b1 = {c: "" for c in CODIGOS[3:]}
    especial(datetime(2026, 11, 14, 10, 0), A1=NAO, **vazio_a1)      # sem consentimento
    especial(datetime(2026, 11, 14, 11, 0), B1=NAO, **vazio_b1)      # fora da população
    especial(datetime(2026, 11, 15, 9, 0), ATN=LIKERT[3])            # falha no item de atenção
    especial(datetime(2026, 11, 15, 10, 0),                          # straightlining
             **{c: LIKERT[3] for c in ("C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4")})
    especial(datetime(2026, 11, 16, 13, 0),                          # >50% "Não sei avaliar" em NIV
             C1=NSA, C2=NSA, C3=NSA)
    especial(datetime(2026, 11, 17, 15, 0), C6="Código;Nenhum")      # inconsistência em C6
    especial(datetime(2026, 11, 17, 16, 0), B2="Analista de TI")     # papel "Outro"
    especial(datetime(2026, 11, 18, 9, 0),                           # texto com quebra de linha e aspas
             F1='Primeira linha.\nSegunda linha com "aspas".')
    original = especial(datetime(2026, 11, 19, 9, 0))                # duplicata a menos de 60 min
    copia = list(original)
    copia[0] = formatar_data(datetime(2026, 11, 19, 9, 40))
    linhas.append(copia)
    return linhas


_POS = {codigo: i for i, codigo in enumerate(CODIGOS)}


def salvar(caminho: str | Path, n: int = 80, seed: int = SEED) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, quoting=csv.QUOTE_MINIMAL)
        escritor.writerow(CABECALHOS)
        escritor.writerows(gerar(n, seed))
    return caminho


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=80)
    parser.add_argument("--saida", default=str(RAIZ / "data" / "raw" / "sintetico.csv"))
    args = parser.parse_args()
    print(f"CSV sintético salvo em {salvar(args.saida, args.n)}")
