# Procedimento: "Outro", anonimização e codificação das abertas (#5)

Regras em `docs/decisoes-analise.md`, itens 2, 3 e 4. Código em `src/abertas.py`.

Os arquivos marcados com 🔒 guardam texto digitado pelo respondente. Ficam fora do Git (`.gitignore`) e só podem ser compartilhados entre os integrantes por canal privado (nunca por commit, issue ou PR).

| Arquivo | Quem preenche | No Git? |
|---|---|---|
| `data/manual/reclassificacao_outro.csv` 🔒 | Gabriel | não |
| `data/manual/revisao_anonimizacao.csv` 🔒 | Gabriel | não |
| `data/manual/livro_codigos.csv` | a dupla | sim |
| `data/manual/codificacao_gabriel.csv` 🔒 | Gabriel | não |
| `data/manual/codificacao_bernardo.csv` 🔒 | Bernardo | não |
| `data/manual/codificacao_consenso.csv` 🔒 | a dupla, junta | não |
| `data/processed/respostas_abertas.csv` | gerado (só texto aprovado) | sim |
| `data/processed/codigos_abertas.csv` | gerado | sim |

Depois de cada passo, rode de novo:

```
python -m src.abertas
```

O comando refaz a limpeza, acrescenta o que é novo nos arquivos de `data/manual/` sem apagar o que já foi preenchido, recusa valores inválidos com mensagem dizendo a linha e mostra o que falta. **Pronto** quando todas as pendências estão em zero.

Edite os CSVs num editor que preserve UTF-8 e vírgula como separador (VS Code, LibreOffice). O Excel em português costuma salvar com `;` e quebrar o arquivo.

## 1. Papéis digitados em "Outro"

Em `reclassificacao_outro.csv`, para cada `texto_original` preencha:

- `grupo`: `técnico`, `gestão` ou `fora` (critério na tabela do item 2 das decisões; ambíguo vai para `fora`);
- `decidido_por`: seu nome;
- `justificativa`: uma frase. Linha sem autor ou justificativa é recusada.

Olhe **só o texto do cargo**, sem abrir as outras respostas da pessoa.

## 2. Anonimização

Em `revisao_anonimizacao.csv`, uma linha por F1/F2:

1. Leia `texto_original`. A coluna `alertas` aponta e-mails, links, @perfis, números longos e palavras com maiúscula, mas a leitura é sempre do texto inteiro.
2. Em `texto_anonimizado` (já vem com uma cópia do original), troque por `[removido]` nomes de pessoas, empresas, clientes, produtos e sistemas internos, cidades e unidades, e situações específicas a ponto de identificar a empresa. Mantenha tecnologias genéricas. Na dúvida, remova.
3. Preencha `revisado_por` e troque `status` para `aprovado`.

Texto aprovado com e-mail ou link é recusado. Só texto aprovado segue para a codificação e para `data/processed/`.

## 3. Familiarização e livro de códigos

Antes de codificar, os dois leem todos os textos aprovados e ajustam `livro_codigos.csv` juntos: renomear, juntar, separar ou criar códigos. Esse ajuste é a única etapa em que os dois conversam sobre os textos antes do consenso.

Colunas: `codigo` (minúsculas, números e `_`), `itens` (`F1`, `F2` ou `F1;F2`), `nome`, `definicao`, `exemplo` (inventado, nunca copiado das respostas).

## 4. Codificação independente

Cada um abre **só a sua** planilha (`codificacao_<nome>.csv`) e preenche `codigos` com um ou mais códigos do livro, separados por `;`. Todo texto recebe pelo menos um código: use `nao_codificavel` para resposta sem conteúdo e `outro` (com descrição em `observacao`) para tema sem código.

Se aparecer um tema recorrente sem código, avise o outro só com o nome do tema, sem citar a resposta. Os dois acrescentam o código ao livro e revisam o que já codificaram.

## 5. Consenso

Quando os dois terminarem, `codificacao_consenso.csv` lista os textos em que os conjuntos de códigos diferem. Juntos, preencham `codigos_final` e `justificativa`. Textos com os mesmos códigos nas duas planilhas já estão resolvidos.

`outputs/concordancia_codificacao.csv` mostra a concordância antes do consenso (% e kappa por código). Os valores são descritivos e vão para a metodologia do relatório.

## 6. Resultado

- `outputs/frequencia_codigos.csv`: por item (com a RQ correspondente: F1 → RQ2, F2 → RQ3) e código, `n`, `k`, `pct` e `margem_pp` no total, entre técnicos e entre gestores.
- `data/processed/codigos_abertas.csv`: um código por linha (`resp_id`, `item`, `codigo`), para o dashboard.
- `data/processed/respostas_abertas.csv`: textos aprovados com `item`, `grupo` e `codigos`, para os exemplos do dashboard. **Não tem `resp_id`**, para que um relato não possa ser cruzado com o perfil de quem respondeu (porte, tipo de empresa, experiência). Por isso os filtros do dashboard valem para as frequências, mas não para os exemplos.

Antes de qualquer commit, confira com `git status` que nenhum arquivo 🔒 aparece.
