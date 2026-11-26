"""Confiabilidade (#10, Gabriel). Página reservada: substituir o conteúdo abaixo.

Use cabecalho_pagina, secao (cartão numerado) e mostrar (gráficos), como em perfil.py.
"""

from app import contexto
from app.componentes import cabecalho_pagina, pendente, secao

ctx = contexto.obter()
cabecalho_pagina("Confiabilidade", "Alfa de Cronbach de NIV, IMP, POS e PRA com IC 95%, meta de 0,70, alfa se o item for removido e validade convergente.", ctx)
with secao(1, "Em construção", chave="confiabilidade-pendente"):
    pendente("Esta página é da issue #10 (Gabriel).")
