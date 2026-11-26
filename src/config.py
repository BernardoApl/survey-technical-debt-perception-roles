"""Constantes do pipeline de análise.

Fonte da verdade: protocolo pré-registrado (planejamento_survey.pdf) e
decisões em docs/decisoes-analise.md.
"""

from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[1]
CSV_BRUTO = RAIZ / "data" / "raw" / "respostas.csv"
DIR_MANUAL = RAIZ / "data" / "manual"
DIR_PROCESSADO = RAIZ / "data" / "processed"
DIR_SAIDAS = RAIZ / "outputs"

# ---------------------------------------------------------------------------
# Reprodutibilidade e datas
# ---------------------------------------------------------------------------
SEED = 2026
FUSO = "America/Sao_Paulo"

# Análise principal: coleta prorrogada até 25/11 (docs/decisoes-analise.md, item 1).
PERIODO_PRINCIPAL = (
    pd.Timestamp("2026-11-13 00:00:00", tz=FUSO),
    pd.Timestamp("2026-11-25 23:59:59", tz=FUSO),
)
# Análise de sensibilidade: período pré-registrado (protocolo, Seção 8).
PERIODO_PREREGISTRADO = (
    pd.Timestamp("2026-11-13 00:00:00", tz=FUSO),
    pd.Timestamp("2026-11-22 23:59:59", tz=FUSO),
)

# ---------------------------------------------------------------------------
# Mapeamento das colunas do CSV exportado do Google Forms
# (posição -> código do protocolo, começo do cabeçalho para conferência).
# Se o formulário mudar, src/load.py falha em vez de mapear errado.
# ---------------------------------------------------------------------------
COLUNAS = [
    ("timestamp", "Carimbo de data/hora"),
    ("A1", "Li o termo de consentimento"),
    ("B1", "Você trabalha hoje em uma equipe"),
    ("B2", "Qual é o seu papel principal"),
    ("B3", "Há quanto tempo você trabalha com TI"),
    ("B4", "Há quanto tempo você está na equipe atual"),
    ("B5", "Quantos funcionários a empresa tem"),
    ("B6", "Em que tipo de empresa"),
    ("B7", "Quantas pessoas há na sua equipe"),
    ("B8", "Antes desta pesquisa, quão familiarizado"),
    ("C1", "O sistema em que trabalho tem partes"),
    ("C2", "Atalhos técnicos para cumprir prazo"),
    ("C3", "Os testes automatizados do sistema"),
    ("C4", "O sistema em que trabalho é fácil de modificar"),
    ("C5", "De 0 a 10"),
    ("C6", "Quais tipos de dívida técnica"),
    ("D1", "Nos últimos 3 meses, problemas no código"),
    ("D2", "Nos últimos 3 meses, problemas técnicos no sistema quase não"),
    ("D3", "Nos últimos 3 meses, fazer mudanças"),
    ("ATN", "Para confirmar que está lendo"),
    ("D4", "Nos últimos 3 meses, problemas técnicos no sistema deixaram"),
    ("D5", "Qual é o MAIOR efeito"),
    ("E1", "No cenário 1, o que a equipe deveria"),
    ("E2", "No cenário 1, o que normalmente acontece"),
    ("E3", "No cenário 2, depois de aplicar"),
    ("E4", "No cenário 2, o que normalmente acontece"),
    ("E5", "No cenário 3, o que a equipe deveria"),
    ("E6", "No cenário 3, o que normalmente acontece"),
    ("E7", "Com que frequência sua equipe"),
    ("E8", "Quem decide, na prática"),
    ("F1", "Descreva um exemplo recente"),
    ("F2", "O que mais dificulta a redução"),
]
CODIGOS = [codigo for codigo, _ in COLUNAS]

# ---------------------------------------------------------------------------
# Textos do formulário usados por mais de uma etapa (#3 e #4).
# Copiados do script do Apps Script que gerou o formulário oficial.
# ---------------------------------------------------------------------------
SIM, NAO = "Sim", "Não"
LIKERT = [
    "Discordo totalmente",
    "Discordo parcialmente",
    "Neutro",
    "Concordo parcialmente",
    "Concordo totalmente",
]
NSA = "Não sei avaliar"  # Likert (blocos C e D)
NAO_SEI = "Não sei"  # vinhetas "acontece", D5, E7, E8 e C6

PAPEIS_TECNICOS = [
    "Desenvolvedor(a) (front-end, back-end, mobile ou full stack)",
    "Arquiteto(a) de software",
    "Tech lead",
    "QA / testador(a)",
    "DevOps / SRE",
    "Engenheiro(a) de dados",
]
PAPEIS_GESTAO = [
    "Product Owner",
    "Product Manager",
    "Analista de negócios / requisitos",
    "Scrum Master / agilista",
    "Gerente de projeto",
    "Coordenador(a) / gerente de engenharia",
]

# Itens de cada construto (protocolo, Seção 3) e regra de "Não sei" (Seção 5.1, etapa 6).
ITENS_CONSTRUTO = {
    "NIV": ["C1", "C2", "C3", "C4"],
    "IMP": ["D1", "D2", "D3", "D4"],
    "POS": ["E1", "E3", "E5"],
    "PRA": ["E2", "E4", "E6"],
}
LIMITE_NAO_SEI = 0.5  # construto ausente se a fração de "Não sei" passar disso

# ---------------------------------------------------------------------------
# Limpeza (protocolo, Seção 5.1; docs/decisoes-analise.md, item 7)
# ---------------------------------------------------------------------------
ATN_CORRETO = "Discordo parcialmente"
ITENS_STRAIGHTLINING = ITENS_CONSTRUTO["NIV"] + ITENS_CONSTRUTO["IMP"]
JANELA_DUPLICATA = pd.Timedelta(minutes=60)
CSV_RECLASSIFICACAO = DIR_MANUAL / "reclassificacao_outro.csv"
GRUPOS_RECLASSIFICACAO = ("técnico", "gestão", "fora")

# ---------------------------------------------------------------------------
# Recodificação (texto -> número): responsabilidade da issue #3.
# ---------------------------------------------------------------------------
