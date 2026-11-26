import json
import math

import pandas as pd
import pytest

from src import sintetico
from src.abertas import (
    APROVADO,
    COLUNAS_CONSENSO,
    ErroPreenchimento,
    alertas,
    codigos_por_item,
    kappa_cohen,
    ler_livro,
    ler_manuais,
    margem_erro,
    processar,
    salvar_abertas,
    separar_codigos,
)
from src.clean import COLUNAS_RECLASSIFICACAO, limpar
from src.config import CODIFICADORES, PAPEIS_GESTAO, csv_codificacao
from src.load import carregar
from tests.fabrica import resposta, tabela

GABRIEL, BERNARDO = CODIFICADORES
LIVRO = ler_livro()


def validas(*linhas):
    return tabela(*linhas)


def _aprovar(revisao, **trocas):
    """Aprova toda a revisão; `trocas` = {"R001_F1": "texto anonimizado"}."""
    revisao = revisao.copy()
    revisao["status"] = APROVADO
    revisao["revisado_por"] = "gabriel"
    for chave, texto in trocas.items():
        r, i = chave.split("_")
        revisao.loc[(revisao["resp_id"] == r) & (revisao["item"] == i), "texto_anonimizado"] = texto
    return revisao


def _codificar(planilha, **codigos):
    """codigos = {"R001_F1": "efeito_atraso;falta_testes"}."""
    planilha = planilha.copy()
    for chave, valor in codigos.items():
        r, i = chave.split("_")
        planilha.loc[(planilha["resp_id"] == r) & (planilha["item"] == i), "codigos"] = valor
    return planilha


def _ate_codificacao(df, **trocas):
    """Roda até as planilhas dos codificadores, com tudo aprovado."""
    r = processar(df, LIVRO)
    return processar(df, LIVRO, _aprovar(r.revisao, **trocas))


# ---------------------------------------------------------------------------
# Livro de códigos
# ---------------------------------------------------------------------------
def test_livro_do_repositorio_e_valido():
    validos = codigos_por_item(LIVRO)
    assert {"nao_codificavel", "outro"} <= set(validos["F1"]) & set(validos["F2"])
    assert "prioridade_funcionalidades" not in validos["F1"]


def test_livro_tem_as_categorias_da_secao_5_7_nos_dois_itens():
    # Protocolo, Seção 5.7: "pressão de prazo, falta de testes, falta de apoio da gestão".
    validos = codigos_por_item(LIVRO)
    for codigo in ("pressao_prazo", "falta_testes", "falta_apoio_gestao"):
        assert codigo in validos["F1"] and codigo in validos["F2"], codigo


def test_livro_com_codigo_repetido(tmp_path):
    caminho = tmp_path / "livro.csv"
    pd.DataFrame({"codigo": ["a", "a"], "itens": ["F1", "F2"], "nome": "x",
                  "definicao": "x", "exemplo": ""}).to_csv(caminho, index=False)
    with pytest.raises(ErroPreenchimento, match="repetido"):
        ler_livro(caminho)


@pytest.mark.parametrize("valor, esperado", [
    ("a;b", {"a", "b"}), (" a , B ", {"a", "b"}), ("", set()), ("a;;", {"a"}),
])
def test_separar_codigos(valor, esperado):
    assert separar_codigos(valor) == esperado


# ---------------------------------------------------------------------------
# Anonimização
# ---------------------------------------------------------------------------
def test_alertas_aponta_nomes_email_e_siglas():
    texto = "Na Empresa Xpto o João pediu ajuda por joao@x.com.br. Java quebrou. SAP caiu."
    achados = alertas(texto)
    assert "e-mail: joao@x.com.br" in achados
    for palavra in ("Empresa", "Xpto", "João", "SAP"):
        assert palavra in achados
    assert "Java" not in achados  # termo técnico genérico
    assert "Na" not in achados.split("maiúscula: ")[1]  # início de frase


def test_alertas_vazio_em_texto_comum():
    assert alertas("O deploy quebrou duas vezes. Tivemos que voltar a versão.") == ""


def test_so_textos_nao_vazios_entram_na_revisao():
    df = validas(resposta(F1="Exemplo.", F2="   "), resposta("2026-11-16 10:00"))
    r = processar(df, LIVRO)
    assert r.revisao[["resp_id", "item"]].values.tolist() == [["R001", "F1"]]
    assert r.revisao["status"].tolist() == ["pendente"]
    assert r.pendencias["anonimizacao"] == 1


def test_pendente_nao_vai_para_codificacao_nem_saida():
    r = processar(validas(resposta(F1="Exemplo.")), LIVRO)
    assert r.textos_aprovados.empty
    assert all(p.empty for p in r.planilhas.values())


def test_revisao_preserva_edicao_e_acrescenta_novos():
    df1 = validas(resposta(F1="O sistema Atlas caiu."))
    revisao = _aprovar(processar(df1, LIVRO).revisao, R001_F1="O sistema [removido] caiu.")
    df2 = validas(resposta(F1="O sistema Atlas caiu.", F2="Prazo."))
    r = processar(df2, LIVRO, revisao)
    linha = r.revisao.set_index(["resp_id", "item"])
    assert linha.at[("R001", "F1"), "texto_anonimizado"] == "O sistema [removido] caiu."
    assert linha.at[("R001", "F1"), "status"] == APROVADO
    assert linha.at[("R001", "F2"), "status"] == "pendente"
    assert r.textos_aprovados["texto"].tolist() == ["O sistema [removido] caiu."]


def test_texto_original_diferente_do_csv_gera_erro():
    revisao = processar(validas(resposta(F1="Texto A.")), LIVRO).revisao
    with pytest.raises(ErroPreenchimento, match="R001/F1"):
        processar(validas(resposta(F1="Texto B.")), LIVRO, revisao)


@pytest.mark.parametrize("coluna, valor, mensagem", [
    ("revisado_por", "", "sem revisado_por"),
    ("texto_anonimizado", " ", "vazio"),
    ("texto_anonimizado", "Fale com ana@empresa.com", "e-mail ou link"),
    ("texto_anonimizado", "Veja https://intranet.x/wiki", "e-mail ou link"),
    ("status", "ok", "status inválido"),
])
def test_revisao_invalida(coluna, valor, mensagem):
    df = validas(resposta(F1="Exemplo."))
    revisao = _aprovar(processar(df, LIVRO).revisao)
    revisao[coluna] = valor
    with pytest.raises(ErroPreenchimento, match=mensagem):
        processar(df, LIVRO, revisao)


# ---------------------------------------------------------------------------
# Codificação e consenso
# ---------------------------------------------------------------------------
def test_planilha_do_codificador_tem_so_o_texto_anonimizado():
    df = validas(resposta(F1="A Maria refez o módulo."))
    r = _ate_codificacao(df, R001_F1="A [removido] refez o módulo.")
    for planilha in r.planilhas.values():
        assert planilha["texto"].tolist() == ["A [removido] refez o módulo."]
        assert planilha["codigos"].tolist() == [""]
    assert r.pendencias["codificacao"] == {GABRIEL: 1, BERNARDO: 1}


def test_codigo_fora_do_livro_ou_do_item_gera_erro():
    df = validas(resposta(F1="Exemplo."))
    r = _ate_codificacao(df)
    for codigo in ("inventado", "prioridade_funcionalidades"):  # este é só de F2
        planilhas = {**r.planilhas,
                     GABRIEL: _codificar(r.planilhas[GABRIEL], R001_F1=codigo)}
        with pytest.raises(ErroPreenchimento, match=codigo):
            processar(df, LIVRO, r.revisao, planilhas)


def _codificado(df, cod_g, cod_b, consenso=None):
    r = _ate_codificacao(df)
    planilhas = {
        GABRIEL: _codificar(r.planilhas[GABRIEL], **cod_g),
        BERNARDO: _codificar(r.planilhas[BERNARDO], **cod_b),
    }
    return processar(df, LIVRO, r.revisao, planilhas, consenso)


def test_concordancia_vira_codigo_final():
    df = validas(resposta(F1="Exemplo."))
    r = _codificado(df, {"R001_F1": "efeito_atraso; falta_testes"},
                    {"R001_F1": "falta_testes,efeito_atraso"})
    assert r.consenso.empty
    assert r.finais["origem"].tolist() == ["concordância"]
    assert r.codigos_longos["codigo"].tolist() == ["efeito_atraso", "falta_testes"]


def test_so_um_codificou_fica_pendente():
    df = validas(resposta(F1="Exemplo."))
    r = _codificado(df, {"R001_F1": "efeito_atraso"}, {})
    assert r.finais.empty and r.consenso.empty
    assert r.pendencias["codificacao"] == {GABRIEL: 0, BERNARDO: 1}


def test_divergencia_vai_para_consenso_e_depois_resolve():
    df = validas(resposta(F1="Exemplo."))
    cod_g, cod_b = {"R001_F1": "efeito_atraso"}, {"R001_F1": "efeito_esforco"}
    r = _codificado(df, cod_g, cod_b)
    assert r.finais.empty
    assert r.pendencias["consenso"] == 1
    linha = r.consenso.iloc[0]
    assert (linha[f"codigos_{GABRIEL}"], linha[f"codigos_{BERNARDO}"]) == (
        "efeito_atraso", "efeito_esforco")

    consenso = r.consenso.assign(codigos_final="efeito_atraso;efeito_esforco",
                                 justificativa="o texto cita as duas coisas")
    r2 = _codificado(df, cod_g, cod_b, consenso)
    assert r2.pendencias["consenso"] == 0
    assert r2.finais["origem"].tolist() == ["consenso"]
    assert r2.finais["codigos"].iloc[0] == {"efeito_atraso", "efeito_esforco"}
    assert r2.consenso["justificativa"].tolist() == ["o texto cita as duas coisas"]


def test_consenso_inativo_e_preservado_sem_contar_como_pendente():
    df = validas(resposta(F1="Exemplo."))
    cod_g, cod_b = {"R001_F1": "efeito_atraso"}, {"R001_F1": "efeito_esforco"}
    antigo = _codificado(df, cod_g, cod_b).consenso.assign(
        codigos_final="efeito_atraso", justificativa="decisão conjunta")
    resultado = _codificado(df, cod_g, {}, antigo)
    assert resultado.consenso.iloc[0].justificativa == "decisão conjunta"
    assert resultado.finais.empty
    assert resultado.pendencias["consenso"] == 0


def test_consenso_final_nao_e_reutilizado_com_codigos_alterados():
    df = validas(resposta(F1="Exemplo."))
    cod_g, cod_b = {"R001_F1": "efeito_atraso"}, {"R001_F1": "efeito_esforco"}
    antigo = _codificado(df, cod_g, cod_b).consenso.assign(
        codigos_final="efeito_atraso", justificativa="decisão conjunta")
    with pytest.raises(ErroPreenchimento, match="codificação alterados"):
        _codificado(df, cod_g, {"R001_F1": "efeito_defeito"}, antigo)


@pytest.mark.parametrize("final, justificativa, mensagem", [
    ("efeito_atraso", "", "sem justificativa"),
    ("inventado", "ok", "inventado"),
])
def test_consenso_invalido(final, justificativa, mensagem):
    df = validas(resposta(F1="Exemplo."))
    cod_g, cod_b = {"R001_F1": "efeito_atraso"}, {"R001_F1": "efeito_esforco"}
    consenso = _codificado(df, cod_g, cod_b).consenso.assign(
        codigos_final=final, justificativa=justificativa)
    with pytest.raises(ErroPreenchimento, match=mensagem):
        _codificado(df, cod_g, cod_b, consenso)


# ---------------------------------------------------------------------------
# Concordância, margem de erro e frequências
# ---------------------------------------------------------------------------
def test_kappa_calculado_a_mao():
    # 10 casos: a=[1,1,1,1,1,0,0,0,0,0], b=[1,1,1,1,0,0,0,0,0,1]
    # po = 0,8; pa = pb = 0,5; pe = 0,5; kappa = 0,6
    a = pd.Series([1] * 5 + [0] * 5)
    b = pd.Series([1] * 4 + [0] * 5 + [1])
    assert kappa_cohen(a, b) == pytest.approx(0.6)
    assert math.isnan(kappa_cohen(pd.Series([0, 0]), pd.Series([0, 0])))


@pytest.mark.parametrize("n, esperado", [(60, 12.7), (50, 13.9), (40, 15.5), (20, 21.9),
                                         (15, 25.3)])
def test_margem_pior_caso_bate_com_o_protocolo(n, esperado):
    assert round(100 * margem_erro(0.5, n), 1) == esperado


def test_frequencias_total_e_por_grupo():
    gestor = PAPEIS_GESTAO[0]
    df = validas(
        resposta("2026-11-15 10:00", F2="a"),
        resposta("2026-11-15 11:00", F2="b"),
        resposta("2026-11-15 12:00", F2="c"),
        resposta("2026-11-15 13:00", F2="d", B2=gestor),
        resposta("2026-11-15 14:00", F2="e", B2="CTO"),  # "Outro" ainda sem grupo
    )
    codigos = {"R001_F2": "pressao_prazo", "R002_F2": "pressao_prazo;falta_pessoas",
               "R003_F2": "cultura_equipe", "R004_F2": "pressao_prazo",
               "R005_F2": "pressao_prazo"}
    r = _codificado(df, codigos, codigos)
    f = r.frequencias.set_index(["item", "codigo", "recorte"])
    total = f.loc[("F2", "pressao_prazo", "total")]
    assert (total["n"], total["k"]) == (5, 4)
    assert total["pct"] == pytest.approx(80)
    assert total["margem_pp"] == pytest.approx(100 * 1.96 * math.sqrt(0.8 * 0.2 / 5))
    tecnico = f.loc[("F2", "pressao_prazo", "técnico")]
    assert (tecnico["n"], tecnico["k"]) == (3, 2)
    gestao = f.loc[("F2", "pressao_prazo", "gestão")]
    assert (gestao["n"], gestao["k"], gestao["margem_pp"]) == (1, 1, 0)
    # código sem ocorrência também aparece, com 0%
    assert f.loc[("F2", "risco_mudanca", "total"), "k"] == 0


def test_frequencias_indicam_a_rq_do_protocolo():
    df = validas(resposta(F1="a", F2="b"))
    codigos = {"R001_F1": "efeito_atraso", "R001_F2": "pressao_prazo"}
    rq = _codificado(df, codigos, codigos).frequencias.groupby("item")["rq"].unique()
    assert rq["F1"].tolist() == ["RQ2"] and rq["F2"].tolist() == ["RQ3"]


def test_frequencias_usam_grupo_reclassificado():
    df = validas(resposta(F2="a", B2="CTO"))
    codigos = {"R001_F2": "pressao_prazo"}
    r = _codificado(df, codigos, codigos)
    reclass = pd.DataFrame([{"texto_original": "CTO", "grupo": "gestão",
                             "decidido_por": "g", "justificativa": "decide prioridade"}],
                           columns=COLUNAS_RECLASSIFICACAO)
    r = processar(df, LIVRO, r.revisao, r.planilhas, r.consenso, reclass)
    f = r.frequencias.set_index(["item", "codigo", "recorte"])
    assert f.loc[("F2", "pressao_prazo", "gestão"), "k"] == 1


def test_concordancia_por_codigo():
    df = validas(resposta("2026-11-15 10:00", F1="a"), resposta("2026-11-15 11:00", F1="b"))
    r = _codificado(df, {"R001_F1": "efeito_atraso", "R002_F1": "efeito_atraso"},
                    {"R001_F1": "efeito_atraso", "R002_F1": "efeito_esforco"})
    c = r.concordancia.set_index(["item", "codigo"])
    assert c.loc[("F1", "(conjunto inteiro)"), "concordancia_pct"] == 50
    assert c.loc[("F1", "efeito_atraso"), "concordancia_pct"] == 50
    assert c.loc[("F1", "efeito_defeito"), "concordancia_pct"] == 100


# ---------------------------------------------------------------------------
# Arquivos e privacidade
# ---------------------------------------------------------------------------
def test_saidas_publicas_nao_tem_texto_original(tmp_path):
    original = "O cliente Banco Fulano reclamou com a Ana."
    anonimizado = "O cliente [removido] reclamou com a [removido]."
    df = validas(resposta(F1=original))
    codigos = {"R001_F1": "efeito_defeito"}
    r = _codificado(df, codigos, codigos)
    r = processar(df, LIVRO, _aprovar(r.revisao, R001_F1=anonimizado), r.planilhas)
    dirs = {n: tmp_path / n for n in ("manual", "processed", "outputs")}
    salvar_abertas(r, dirs["manual"], dirs["processed"], dirs["outputs"])

    for pasta in ("processed", "outputs"):
        for arquivo in dirs[pasta].iterdir():
            conteudo = arquivo.read_text(encoding="utf-8-sig")
            assert "Fulano" not in conteudo and "Ana" not in conteudo, arquivo.name
    publicas = pd.read_csv(dirs["processed"] / "respostas_abertas.csv")
    assert publicas["texto"].tolist() == [anonimizado]
    assert pd.read_csv(dirs["processed"] / "codigos_abertas.csv")["codigo"].tolist() == [
        "efeito_defeito"]
    for nome in CODIFICADORES:
        planilha = (dirs["manual"] / csv_codificacao(nome).name).read_text("utf-8-sig")
        assert "Fulano" not in planilha
    pendencias = json.loads((dirs["outputs"] / "pendencias_abertas.json").read_text("utf-8"))
    assert pendencias["resolvidos"] == 1


def test_texto_publico_nao_liga_ao_perfil(tmp_path):
    gestor = PAPEIS_GESTAO[0]
    df = validas(
        resposta("2026-11-15 10:00", F1="b", F2="z"),
        resposta("2026-11-15 11:00", F1="a", B2=gestor),
        resposta("2026-11-15 12:00", F1="c", B2="CTO"),  # "Outro" ainda sem grupo
    )
    codigos = {"R001_F1": "efeito_atraso", "R002_F1": "efeito_esforco;falta_testes"}
    r = _codificado(df, codigos, codigos)
    salvar_abertas(r, tmp_path / "m", tmp_path / "p", tmp_path / "o")

    publicas = pd.read_csv(tmp_path / "p" / "respostas_abertas.csv", keep_default_na=False)
    assert list(publicas.columns) == ["item", "grupo", "codigos", "texto"]
    assert publicas.values.tolist() == [
        ["F1", "", "", "c"],  # sem grupo e sem código resolvido
        ["F1", "gestão", "efeito_esforco;falta_testes", "a"],
        ["F1", "técnico", "efeito_atraso", "b"],
        ["F2", "técnico", "", "z"],
    ]
    # o arquivo que tem resp_id não tem texto
    codigos_publicos = pd.read_csv(tmp_path / "p" / "codigos_abertas.csv")
    assert list(codigos_publicos.columns) == ["resp_id", "item", "codigo"]


def test_ida_e_volta_dos_arquivos_manuais(tmp_path):
    df = validas(resposta(F1='Linha 1.\nLinha 2 com "aspas", vírgula.'))
    r = _codificado(df, {"R001_F1": "efeito_atraso"}, {"R001_F1": "efeito_esforco"})
    salvar_abertas(r, tmp_path, tmp_path / "p", tmp_path / "o")
    revisao, planilhas, consenso = ler_manuais(tmp_path)
    assert list(consenso.columns) == COLUNAS_CONSENSO
    r2 = processar(df, LIVRO, revisao, planilhas, consenso)
    assert r2.pendencias == r.pendencias
    assert r2.textos_aprovados.equals(r.textos_aprovados)


def test_ponta_a_ponta_com_sintetico(tmp_path):
    limpeza = limpar(carregar(sintetico.salvar(tmp_path / "respostas.csv", n=60)))
    r = processar(limpeza.validas, LIVRO, reclassificacao=limpeza.reclassificacao)
    p = r.pendencias
    assert p["textos"] == p["anonimizacao"] > 0
    assert p["resolvidos"] == 0
    assert set(r.revisao["resp_id"]) <= set(limpeza.validas["resp_id"])
    assert (r.frequencias["n"] == 0).all()
