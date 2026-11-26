"""Questões de pesquisa (#11, Bernardo). Página reservada: substituir o conteúdo abaixo.

Use cabecalho_pagina, secao (cartão numerado) e mostrar (gráficos), como em perfil.py.
"""

from app import contexto
from app.componentes import cabecalho_pagina, pendente, secao

ctx = contexto.obter()
cabecalho_pagina("Questões de pesquisa", "Uma seção por RQ com pergunta, H0, gráfico, teste, p bruto, p Holm, tamanho de efeito e margem de erro. Usa sempre a amostra completa (ctx.analise.dados), sem filtros.", ctx)
with secao(1, "Em construção", chave="rqs-pendente"):
    pendente("Esta página é da issue #11 (Bernardo).")
