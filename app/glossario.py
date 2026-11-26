"""O que cada sigla mede: usado na página "O que foi medido" e nas explicações das outras páginas.

Para mostrar a explicação de uma sigla ao passar o mouse:

    st.metric("NIV", valor, help=ajuda("NIV"))
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.config import ITENS_CONSTRUTO


@dataclass
class Construto:
    sigla: str
    nome: str
    mede: str
    escala: str
    itens: list[str]
    invertidos: list[str] = field(default_factory=list)


CONSTRUTOS = {
    "NIV": Construto("NIV", "Nível percebido de dívida técnica",
                     "Quanta dívida técnica a pessoa enxerga no sistema em que trabalha.",
                     "Likert de 1 (discordo totalmente) a 5 (concordo totalmente)",
                     ITENS_CONSTRUTO["NIV"], ["C4"]),
    "IMP": Construto("IMP", "Impacto percebido",
                     "Quanto a dívida técnica atrapalhou a equipe nos últimos 3 meses.",
                     "Likert de 1 (discordo totalmente) a 5 (concordo totalmente)",
                     ITENS_CONSTRUTO["IMP"], ["D2"]),
    "POS": Construto("POS", "Postura de priorização",
                     "O que a pessoa acha que a equipe deveria fazer diante da dívida técnica.",
                     "1 (prioriza a entrega) a 4 (prioriza pagar a dívida)",
                     ITENS_CONSTRUTO["POS"]),
    "PRA": Construto("PRA", "Prática percebida",
                     "O que normalmente acontece na equipe nas mesmas situações.",
                     "1 (prioriza a entrega) a 4 (prioriza pagar a dívida); \"Não sei\" fica ausente",
                     ITENS_CONSTRUTO["PRA"]),
}

# Frase curta de cada sigla, para explicações ao passar o mouse.
SIGLAS = {
    **{c.sigla: f"{c.nome}: {c.mede[0].lower()}{c.mede[1:]}" for c in CONSTRUTOS.values()},
    "DIST": "Distância POS − PRA: quanto o que se acha certo se afasta do que acontece. "
            "Positivo = a equipe paga menos dívida do que a pessoa acha que deveria.",
}

# Vinhetas do bloco E (texto do formulário oficial).
CENARIOS = [
    ("Código legado",
     "A equipe precisa adicionar uma funcionalidade em um módulo antigo, com código confuso e "
     "poucos testes. O prazo é apertado.", ("E1", "E2")),
    ("Correção urgente",
     "Um defeito em produção precisa ser corrigido hoje. A correção rápida funciona, mas deixa "
     "uma solução improvisada no código.", ("E3", "E4")),
    ("Dependência desatualizada",
     "Uma biblioteca central está várias versões atrás e vai perder suporte em cerca de um ano. "
     "Atualizar levaria duas semanas, sem nenhuma funcionalidade nova para o cliente.", ("E5", "E6")),
]

# Como ler cada escore.
LEITURA = [
    ("NIV", "Mediana de C1–C4", "1 a 5", "Maior = mais dívida técnica percebida"),
    ("IMP", "Mediana de D1–D4", "1 a 5", "Maior = mais impacto percebido"),
    ("POS", "Mediana de E1, E3, E5", "1 a 4", "Maior = acha que deveria priorizar pagar a dívida"),
    ("PRA", "Mediana de E2, E4, E6", "1 a 4", "Maior = a equipe prioriza pagar a dívida na prática"),
    ("DIST", "POS − PRA", "−3 a +3", "Positivo = a prática fica aquém do que se acha certo"),
]


def ajuda(sigla: str) -> str:
    """Explicação curta de uma sigla (NIV, IMP, POS, PRA, DIST) para o parâmetro `help`."""
    return SIGLAS[sigla]
