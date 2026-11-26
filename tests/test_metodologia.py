import json
import re
import shutil
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import app.dados as dados_app
from app.filtros import aplicar_filtros, filtros_ativos
from app.metodologia_dados import (
    A_PREENCHER,
    A_RESOLVER,
    ARQUIVO_DECISOES,
    ARQUIVO_DESVIOS,
    NAO_OCORREU,
    OCORREU,
    Desvio,
    estado,
    titulo_curto,
    ler_decisoes,
    ler_desvios,
)
from src import sintetico
from src.config import CSV_LIVRO_CODIGOS
from src.pipeline import calcular, executar

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


# ---------------------------------------------------------------------------
# Leitura dos documentos
# ---------------------------------------------------------------------------
def test_todo_desvio_do_arquivo_e_lido_com_os_tres_campos():
    titulos = re.findall(r"^## (.+)$", ARQUIVO_DESVIOS.read_text(encoding="utf-8"), flags=re.M)
    desvios = ler_desvios()
    assert [d.titulo for d in desvios] == [t.strip() for t in titulos]
    for d in desvios:
        assert d.resumo and d.o_que and d.por_que and d.impacto, d.titulo
        assert len(d.resumo) <= 120, d.titulo  # cartão enxuto: uma frase


def test_desvio_com_campo_em_varias_linhas(tmp_path):
    arquivo = tmp_path / "d.md"
    arquivo.write_text("# Desvios\n\n## Exemplo (condicional)\n\n- **O quê:** linha um\n  continua.\n"
                       "- **Por quê:** motivo.\n- **Impacto:** efeito.\n", encoding="utf-8")
    (d,) = ler_desvios(arquivo)
    assert d.o_que == "linha um continua."
    assert d.condicional


def test_todas_as_decisoes_numeradas_sao_lidas():
    numeros = re.findall(r"^#{2,3} (\d+)\.", ARQUIVO_DECISOES.read_text(encoding="utf-8"), flags=re.M)
    decisoes = ler_decisoes()
    assert decisoes["Nº"].tolist() == [int(n) for n in numeros]
    assert set(decisoes["É desvio?"]) <= {"Sim", "Não"}
    assert decisoes.loc[decisoes["Nº"] == 1, "É desvio?"].item() == "Sim"


# ---------------------------------------------------------------------------
# Estado de cada desvio a partir dos dados
# ---------------------------------------------------------------------------
def calculados(**trocas):
    base = {
        "prorrogacao": {"recebidas": 5, "validas": 4},
        "amostra": {"validas": 60, "minimo": 50, "abaixo_minimo": False},
        "gestao": {"validas": 22, "meta": 20, "minimo": 15, "abaixo_meta": False,
                   "abaixo_minimo": False, "sem_grupo_pendente": 0},
        "testes_nao_executaveis": [],
        "testes_por_permutacao": [],
        "testes_por_cenario": {"executada": False, "observacao": "Nenhum alfa de vinheta abaixo da meta."},
    }
    base.update(trocas)
    return base


def desvio(titulo, por_que="motivo"):
    return Desvio(titulo=titulo, resumo="r", o_que="x", por_que=por_que, impacto="y",
                  condicional="condicion" in titulo.lower())


def test_condicionais_nao_ocorrem_com_amostra_boa():
    for titulo in ("Permutação do qui-quadrado em D5 e E8 (condicional)",
                   "Amostra abaixo do mínimo e cota de gestão (condicionais)",
                   "Testes não executáveis (condicional)",
                   "Análises exploratórias por cenário (condicional)"):
        assert estado(desvio(titulo), calculados())[0] == NAO_OCORREU, titulo


@pytest.mark.parametrize("titulo, trocas", [
    ("Permutação do qui-quadrado em D5 e E8 (condicional)",
     {"testes_por_permutacao": [{"id": 3, "variavel": "D5"}]}),
    ("Amostra abaixo do mínimo e cota de gestão (condicionais)",
     {"gestao": {"validas": 12, "meta": 20, "minimo": 15, "abaixo_meta": True, "abaixo_minimo": True,
                 "sem_grupo_pendente": 0}}),
    ("Testes não executáveis (condicional)",
     {"testes_nao_executaveis": [{"id": 8, "variavel": "E8", "motivo": "um grupo vazio"}]}),
    ("Análises exploratórias por cenário (condicional)",
     {"testes_por_cenario": {"executada": True, "observacao": "Exploratória."}}),
])
def test_condicionais_ocorrem_quando_os_dados_mostram(titulo, trocas):
    situacao, detalhe = estado(desvio(titulo), calculados(**trocas))
    assert situacao == OCORREU
    assert detalhe


def test_prorrogacao_mostra_os_numeros():
    situacao, detalhe = estado(desvio("Prorrogação da coleta até 25/11/2026"), calculados())
    assert situacao == OCORREU
    assert "5 recebidas" in detalhe and "4 válidas" in detalhe


def test_conflito_e_campo_a_preencher():
    assert estado(desvio("Escolha do teste: conflito a resolver pelo grupo"), calculados())[0] == A_RESOLVER
    assert estado(desvio("Divulgação", por_que="[a preencher pelo grupo]."), calculados())[0] == A_PREENCHER


# ---------------------------------------------------------------------------
# Pipeline: o dashboard usa o mesmo cálculo de desvios
# ---------------------------------------------------------------------------
def test_calcular_e_executar_geram_os_mesmos_desvios(tmp_path):
    manual = tmp_path / "manual"
    manual.mkdir()
    shutil.copyfile(CSV_LIVRO_CODIGOS, manual / CSV_LIVRO_CODIGOS.name)
    bruto = sintetico.salvar(tmp_path / "bruto.csv", n=35)
    em_memoria = calcular(bruto, manual)["desvios"]
    executar(bruto, manual, tmp_path / "proc", tmp_path / "saidas")
    gravado = json.loads((tmp_path / "saidas" / "desvios.json").read_text(encoding="utf-8"))
    assert json.loads(json.dumps(em_memoria, ensure_ascii=False)) == gravado


# ---------------------------------------------------------------------------
# Filtros: opção que ninguém marcou não conta como filtro ativo
# ---------------------------------------------------------------------------
def test_filtro_com_todas_as_opcoes_presentes_nao_e_ativo():
    dados = pd.DataFrame({"B6": ["Startup", "Setor público"], "grupo": ["técnico", "gestão"]})
    presentes = {"B6": ["Setor público", "Startup"]}
    selecao = {"B6": ["Setor público", "Startup"]}
    assert filtros_ativos(selecao, presentes) == []
    assert len(aplicar_filtros(dados, selecao, presentes)) == 2
    assert filtros_ativos({"B6": ["Startup"]}, presentes) == ["Tipo de empresa"]


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------
@pytest.fixture
def pagina(tmp_path, monkeypatch):
    csv = sintetico.salvar(tmp_path / "respostas.csv", n=60)
    monkeypatch.setattr(dados_app, "CSV_BRUTO", csv)
    teste = AppTest.from_file(APP, default_timeout=120)
    teste.run()
    teste.switch_page("paginas/metodologia.py").run()
    return teste


def _html(teste):
    return " ".join(h.proto.body for h in teste.get("html"))


def test_pagina_mostra_so_os_desvios_que_ocorreram(pagina):
    assert not pagina.exception, pagina.exception
    corpo = _html(pagina).replace("&quot;", '"')
    calculados = calcular(dados_app.CSV_BRUTO)["desvios"]
    for d in ler_desvios():
        aparece = titulo_curto(d.titulo) in corpo
        assert aparece == (estado(d, calculados)[0] != NAO_OCORREU), d.titulo


def test_pagina_nao_mostra_texto_digitado_em_outro(pagina):
    textos = " ".join([_html(pagina), *(m.value for m in pagina.markdown),
                       *(str(t.value) for t in pagina.table)])
    for cargo in sintetico.PAPEIS_OUTRO:
        assert cargo not in textos


def test_cabecalho_sem_filtros_ativos_ao_abrir(pagina):
    assert "Filtros:" not in _html(pagina)


def test_trechos_entre_crases_viram_code(pagina):
    corpo = _html(pagina)
    assert "<code>outputs/desvios.json</code>" in corpo
    assert "\x01" not in corpo
