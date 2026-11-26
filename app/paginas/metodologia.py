"""Metodologia e desvios (#12, Gabriel). Página reservada: substituir o conteúdo abaixo.

Use cabecalho_pagina, secao (cartão numerado) e mostrar (gráficos), como em perfil.py.
"""

from app import contexto
from app.componentes import cabecalho_pagina, pendente, secao

ctx = contexto.obter()
cabecalho_pagina("Metodologia e desvios", "Resumo do protocolo, desvios (o quê, por quê e impacto), incluindo a prorrogação da coleta de 22/11 para 25/11.", ctx)
with secao(1, "Em construção", chave="metodologia-pendente"):
    pendente("Esta página é da issue #12 (Gabriel).")
