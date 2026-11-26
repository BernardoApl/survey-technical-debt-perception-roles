"""Itens Likert (#10, Gabriel). Página reservada: substituir o conteúdo abaixo.

Use cabecalho_pagina, secao (cartão numerado) e mostrar (gráficos), como em perfil.py.
"""

from app import contexto
from app.componentes import cabecalho_pagina, pendente, secao

ctx = contexto.obter()
cabecalho_pagina("Itens Likert", "Barras divergentes de C1–C4 e D1–D4, com % de concordância e margem de erro, total e por grupo. Respeita os filtros (use ctx.filtrados).", ctx)
with secao(1, "Em construção", chave="likert-pendente"):
    pendente("Esta página é da issue #10 (Gabriel).")
