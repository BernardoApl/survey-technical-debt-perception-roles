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

# Metas de amostra (protocolo, Seção 2)
META_VALIDAS, MINIMO_VALIDAS = 60, 50
META_GESTAO, MINIMO_GESTAO = 20, 15

# Análise principal: coleta prorrogada até 25/11 (docs/decisoes-analise.md, item 1).
PERIODO_PRINCIPAL = (
    pd.Timestamp("2026-11-13 00:00:00", tz=FUSO),
    pd.Timestamp("2026-11-25 23:59:59", tz=FUSO),
)
# Período pré-registrado (protocolo, Seção 8). Não é usado na análise: serve só para
# registrar o desvio da prorrogação (respostas recebidas entre 23/11 e 25/11).
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

# Enunciado completo de cada coluna, como no formulário oficial (script do Apps Script).
# O começo de cada um bate com COLUNAS. Usado pelo dashboard e pelo gerador sintético.
ENUNCIADOS = {
    "timestamp": "Carimbo de data/hora",
    "A1": "Li o termo de consentimento e aceito participar.",
    "B1": "Você trabalha hoje em uma equipe de desenvolvimento de software, há pelo menos 3 meses?",
    "B2": "Qual é o seu papel principal na equipe?",
    "B3": "Há quanto tempo você trabalha com TI?",
    "B4": "Há quanto tempo você está na equipe atual?",
    "B5": "Quantos funcionários a empresa tem?",
    "B6": "Em que tipo de empresa você trabalha?",
    "B7": "Quantas pessoas há na sua equipe?",
    "B8": "Antes desta pesquisa, quão familiarizado(a) você estava com o termo \"dívida técnica\"?",
    "C1": "O sistema em que trabalho tem partes que precisam ser refeitas para facilitar a manutenção.",
    "C2": "Atalhos técnicos para cumprir prazo são comuns na minha equipe.",
    "C3": "Os testes automatizados do sistema são insuficientes para dar segurança ao fazer mudanças.",
    "C4": "O sistema em que trabalho é fácil de modificar sem gerar novos problemas.",
    "C5": "De 0 a 10, qual é o nível de dívida técnica do seu projeto principal?",
    "C6": "Quais tipos de dívida técnica existem no seu projeto? (marque todas que se aplicam)",
    "D1": "Nos últimos 3 meses, problemas no código ou na arquitetura atrasaram entregas da minha equipe.",
    "D2": "Nos últimos 3 meses, problemas técnicos no sistema quase não causaram defeitos em produção.",
    "D3": "Nos últimos 3 meses, fazer mudanças no sistema exigiu mais esforço do que deveria por causa de problemas técnicos acumulados.",
    "ATN": "Para confirmar que está lendo, marque \"Discordo parcialmente\" nesta pergunta.",
    "D4": "Nos últimos 3 meses, problemas técnicos no sistema deixaram pessoas da equipe desmotivadas ou frustradas.",
    "D5": "Qual é o MAIOR efeito da dívida técnica na sua equipe?",
    "E1": "No cenário 1, o que a equipe deveria fazer?",
    "E2": "No cenário 1, o que normalmente acontece na sua equipe?",
    "E3": "No cenário 2, depois de aplicar a correção, o que a equipe deveria fazer?",
    "E4": "No cenário 2, o que normalmente acontece na sua equipe?",
    "E5": "No cenário 3, o que a equipe deveria fazer?",
    "E6": "No cenário 3, o que normalmente acontece na sua equipe?",
    "E7": "Com que frequência sua equipe dedica tempo para reduzir dívida técnica?",
    "E8": "Quem decide, na prática, quando reduzir a dívida técnica?",
    "F1": "Descreva um exemplo recente em que a dívida técnica afetou seu trabalho.",
    "F2": "O que mais dificulta a redução da dívida técnica na sua equipe?",
}

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

# Opções de resposta, na ordem do formulário (a posição define o valor ordinal).
OPCOES_B3 = ["Menos de 1 ano", "1 a 2 anos", "3 a 5 anos", "6 a 10 anos", "Mais de 10 anos"]
OPCOES_B4 = ["3 a 11 meses", "1 a 2 anos", "3 a 5 anos", "Mais de 5 anos"]
OPCOES_B5 = ["Até 49", "50 a 249", "250 a 999", "1.000 ou mais"]
OPCOES_B6 = [
    "Produto próprio",
    "Consultoria / fábrica de software",
    "Setor público",
    "Startup",
    "TI interna de empresa não-TI",
    "Outro",
]
OPCOES_B7 = ["1 a 5 pessoas", "6 a 10 pessoas", "11 a 20 pessoas", "Mais de 20 pessoas"]
C6_NENHUM = "Nenhum"
TIPOS_C6 = [  # sem "Nenhum" e "Não sei"
    "Código",
    "Arquitetura",
    "Testes",
    "Documentação",
    "Infraestrutura / build",
    "Requisitos",
]
OPCOES_D5 = [
    "Atraso de entregas",
    "Defeitos em produção",
    "Custo de manutenção",
    "Desmotivação",
    "Tempo para novos membros aprenderem o sistema",
    "Nenhum efeito relevante",
    NAO_SEI,
]
# E1/E2 usam o cenário 1, E3/E4 o 2, E5/E6 o 3. As perguntas "acontece" têm também "Não sei".
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
OPCOES_E7 = [
    "Nunca",
    "Raramente (algumas vezes por ano)",
    "Às vezes (cerca de uma vez por mês)",
    "Frequentemente (na maioria das sprints ou ciclos)",
    "Sempre (há tempo reservado em todo ciclo)",
    NAO_SEI,
]
OPCOES_E8 = [
    "Devs",
    "Tech lead",
    "PO / PM",
    "Gerente",
    "Decisão conjunta",
    "Ninguém formalmente",
    NAO_SEI,
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
# Respostas abertas (protocolo, Seções 5.7 e 6; docs/decisoes-analise.md, itens 3 e 4)
# Os arquivos com texto do respondente ficam fora do Git (.gitignore).
# ---------------------------------------------------------------------------
# Recortes de toda tabela descritiva. Papel "Outro" ainda sem grupo entra só no total.
RECORTES = ("total", "técnico", "gestão")
META_ALFA = 0.70  # protocolo, Seção 5.3

ITENS_ABERTOS = ["F1", "F2"]
RQ_ABERTAS = {"F1": "RQ2", "F2": "RQ3"}  # tabela da Seção 3 do protocolo
REMOVIDO = "[removido]"
CSV_ANONIMIZACAO = DIR_MANUAL / "revisao_anonimizacao.csv"
CSV_LIVRO_CODIGOS = DIR_MANUAL / "livro_codigos.csv"  # versionado: não tem texto de respondente
CODIFICADORES = ("gabriel", "bernardo")
CSV_CONSENSO = DIR_MANUAL / "codificacao_consenso.csv"
Z_95 = 1.96  # margem de erro: e = 1,96 * sqrt(p(1 - p) / n) (protocolo, Seção 2)


def csv_codificacao(codificador: str) -> Path:
    return DIR_MANUAL / f"codificacao_{codificador}.csv"

# ---------------------------------------------------------------------------
# Recodificação (texto -> número): responsabilidade da issue #3.
# ---------------------------------------------------------------------------
